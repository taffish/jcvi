#!/usr/bin/env python3
"""Shared offline validation and immutable, explicit resource installation."""
import argparse
from contextlib import contextmanager, ExitStack
import ctypes
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
import uuid
from urllib.parse import urlsplit

SCHEMA = 'taffish.jcvi.resource.v1'
CATALOG = {
    'ensembl-r116-yeast-fasta': dict(kind='fasta', assembly='R64-1-1', bytes=3784201,
        sha256='a9953096d6a041a01a4cb5352b0232ee9373bf4c050fb23cb7ae673b2e1bb528',
        data_sha256='35cc97fccb91762c7a1f0f71b4adb1037b143d48b63fbd3b3f8bad45e5afa44c',
        url='https://ftp.ensembl.org/pub/release-116/fasta/saccharomyces_cerevisiae/dna/Saccharomyces_cerevisiae.R64-1-1.dna.toplevel.fa.gz'),
    'ensembl-r116-yeast-gff3': dict(kind='gff3', assembly='R64-1-1; annotation 63 in Ensembl release 116', bytes=1091237,
        sha256='717194a9522ae6d4ad97fc499f1ee56120f03877ef23ac8ee153fc51d5d5fbe5',
        data_sha256='3d70320fd69c941aa7b500f6265aef41920794b192c3c980d6460a6b43204792',
        url='https://ftp.ensembl.org/pub/release-116/gff3/saccharomyces_cerevisiae/Saccharomyces_cerevisiae.R64-1-1.63.gff3.gz'),
}
for item in CATALOG.values():
    item.update(license='Ensembl unrestricted project data; third-party source constraints still apply',
        license_url='https://jun2026.archive.ensembl.org/info/about/legal/disclaimer.html',
        attribution='Ensembl and Saccharomyces Genome Database; assembly R64-1-1')
CATALOG['sam-vit-h-4b8939'] = dict(kind='sam-checkpoint', assembly='SAM ViT-H; upstream 4b8939 checkpoint',
    bytes=2564550879,
    sha256='a7bf3b02f3ebf1267aba913ff637d9a2d5c33d3173bb679e46d9f338c26f262e',
    data_sha256='a7bf3b02f3ebf1267aba913ff637d9a2d5c33d3173bb679e46d9f338c26f262e',
    url='https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth',
    license='Apache-2.0 (SAM code and model; not the SA-1B dataset license)',
    license_url='https://github.com/facebookresearch/segment-anything/blob/dca509fe793f601edb92606367a655c15ac00fdf/LICENSE',
    attribution='Meta AI; Kirillov et al., Segment Anything, ICCV 2023')

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()

def inventory(path, kind):
    """Inspect text or a fixed checkpoint ZIP; never unpickle or claim inference."""
    if kind == 'sam-checkpoint':
        with path.open('rb') as stream, zipfile.ZipFile(stream) as archive:
            members = archive.infolist()
            names = [m.filename for m in members]
            if len(names) != len(set(names)) or not any(n.endswith('/data.pkl') for n in names):
                raise ValueError('invalid checkpoint member inventory')
            if any(n.startswith('/') or '..' in n.split('/') for n in names):
                raise ValueError('unsafe checkpoint member path')
            return {m.filename: dict(bytes=m.file_size, crc32=f'{m.CRC:08x}') for m in members}
    records = {}
    current = None
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            line = line.strip()
            if not line: continue
            if kind == 'fasta':
                if line.startswith('>'):
                    current = line[1:].split()[0]
                    if current in records: raise ValueError('duplicate FASTA identifier')
                    records[current] = 0
                else:
                    if current is None or not re.fullmatch('[A-Za-z*.-]+', line): raise ValueError('invalid FASTA')
                    records[current] += len(line)
            elif kind == 'gff3':
                if line == '##FASTA': break
                if line.startswith('#'): continue
                fields = line.split('\t')
                if len(fields) != 9 or int(fields[3]) < 1 or int(fields[4]) < int(fields[3]): raise ValueError('invalid GFF3')
                records[fields[0]] = records.get(fields[0], 0) + 1
            elif kind == 'obo':
                if line == '[Term]': current = True
                elif line.startswith('['): current = False
                elif current and line.startswith('id: '):
                    key = line[4:]
                    if key in records: raise ValueError('duplicate OBO term')
                    records[key] = 1
            else: raise ValueError('unsupported resource kind')
    if not records or any(n <= 0 for n in records.values()): raise ValueError('empty resource inventory')
    return records

class OpenFile:
    """Read only the already-opened regular file, not a mutable pathname."""
    def __init__(self, fd): self.fd = fd; self.initial = os.fstat(fd)
    def open(self, mode='r', encoding=None):
        os.lseek(self.fd, 0, os.SEEK_SET)
        return os.fdopen(os.dup(self.fd), mode, encoding=encoding)
    def read_text(self):
        if os.fstat(self.fd).st_size > 64 * 1024 * 1024:
            raise ValueError('resource metadata is unexpectedly large')
        with self.open(encoding='utf-8') as stream: return stream.read()
    def stat(self): return os.fstat(self.fd)

def same(a, b): return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)

def verify(root, expected_resource=None):
    # Valid root aliases are accepted; member links and changing entries are not.
    try: root = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError('resource root cannot resolve to a directory') from error
    if not root.is_dir(): raise ValueError('resource root must resolve to a directory')
    with ExitStack() as stack:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, fd)
        members = {'resource.data', 'resource.json', 'SHA256SUMS', 'READY'}
        if set(os.listdir(fd)) != members: raise ValueError('missing/extra resource member')
        files = {}
        for name in sorted(members):
            f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            stack.callback(os.close, f)
            if not stat.S_ISREG(os.fstat(f).st_mode): raise ValueError('non-regular resource member')
            files[name] = OpenFile(f)
        receipt, verified_hashes = verify_files(files, expected_resource)
        for attempt in range(2):
            # Fast writes can share coarse filesystem timestamps. Compare the
            # content read by the semantic checks again before trusting stat.
            if any(digest(files[name]) != checksum for name, checksum in verified_hashes.items()):
                raise ValueError('resource content changed during verification')
            if not same(root.stat(), os.fstat(fd)) or set(os.listdir(fd)) != members:
                raise ValueError('resource root changed during verification')
            ctime_changed = False
            for name, f in files.items():
                entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
                after = f.stat()
                if not stat.S_ISREG(entry.st_mode) or not same(entry, after):
                    raise ValueError('resource member changed during verification: '+name)
                before = f.initial
                stable = ('st_size', 'st_mtime_ns', 'st_mode', 'st_uid', 'st_gid', 'st_nlink')
                if any(getattr(before, key) != getattr(after, key) for key in stable):
                    raise ValueError('resource content/permissions changed during verification: '+name)
                ctime_changed |= before.st_ctime_ns != after.st_ctime_ns
            if ctime_changed and attempt == 0:
                # VM shared filesystems may refresh ctime when reads update atime.
                # Recheck the complete content contract, not just timestamps.
                # This also rejects in-place changes with a restored mtime.
                if verify_files(files, expected_resource) != (receipt, verified_hashes):
                    raise ValueError('resource content changed during verification')
                continue
            return receipt

def verify_files(files, expected_resource):
    verified_hashes = {'READY': digest(files['READY']), 'SHA256SUMS': digest(files['SHA256SUMS'])}
    if verified_hashes['SHA256SUMS'] != files['READY'].read_text().strip(): raise ValueError('invalid READY')
    rows = {}
    for line in files['SHA256SUMS'].read_text().splitlines():
        checksum, name = line.split('  ', 1)
        if name not in {'resource.data','resource.json'} or name in rows or not re.fullmatch('[a-f0-9]{64}', checksum):
            raise ValueError('invalid checksum inventory')
        if digest(files[name]) != checksum: raise ValueError('checksum mismatch: '+name)
        rows[name] = checksum
        verified_hashes[name] = checksum
    if set(rows) != {'resource.data','resource.json'}: raise ValueError('incomplete checksum inventory')
    receipt = json.loads(files['resource.json'].read_text())
    identity = receipt['resource']
    if receipt['schema'] != SCHEMA or not isinstance(identity,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',identity):
        raise ValueError('invalid resource identity')
    if expected_resource is not None and identity != expected_resource: raise ValueError('resource identity mismatch')
    if identity not in CATALOG and not re.fullmatch('local-[A-Za-z0-9_.-]+',identity): raise ValueError('unknown resource ID')
    source = receipt['source']
    if identity in CATALOG and source != CATALOG[identity]: raise ValueError('receipt differs from fixed catalog')
    if identity not in CATALOG:
        if source['kind'] not in {'fasta','gff3','obo'}:
            raise ValueError('model imports require a fixed trusted catalog identity')
        for key in ('assembly', 'license'):
            if not isinstance(source.get(key), str) or not source[key].strip():
                raise ValueError('missing source '+key)
        if type(source.get('bytes')) is not int or source['bytes'] < 1:
            raise ValueError('invalid source size')
        if not re.fullmatch('[a-f0-9]{64}', source.get('sha256', '')):
            raise ValueError('invalid source checksum')
        if bool(source.get('origin')) == bool(source.get('url')):
            raise ValueError('source requires exactly one origin or URL')
        if source.get('url'): valid_url(source['url'])
        elif Path(source['origin']).name != source['origin']:
            raise ValueError('invalid source origin')
    if source['data_sha256'] != rows['resource.data'] or receipt['data_bytes'] != files['resource.data'].stat().st_size:
        raise ValueError('invalid payload identity')
    if receipt['inventory'] != inventory(files['resource.data'],source['kind']): raise ValueError('resource inventory mismatch')
    return receipt, verified_hashes

def valid_url(value):
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password:
        raise ValueError('public HTTPS URL required; do not embed credentials')

SIGNALS = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP}

@contextmanager
def blocked_signals():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    try: yield
    finally: signal.pthread_sigmask(signal.SIG_SETMASK, previous)

@contextmanager
def signal_cleanup():
    def interrupted(number, frame):
        try: print('jcvi-resources: interrupted '+signal.Signals(number).name+'; cleaning owned transaction only', file=sys.stderr, flush=True)
        except OSError: pass
        raise SystemExit(128 + number)
    previous = {s: signal.signal(s, interrupted) for s in SIGNALS}
    try: yield
    finally:
        for s, handler in previous.items(): signal.signal(s, handler)

def anchor(fd):
    path = Path('/proc/self/fd') / str(fd)
    if not path.is_dir(): raise ValueError('installation requires Linux /proc/self/fd')
    return path

def create_root(logical):
    # Resolve valid aliases first, then create missing components relative to a
    # pinned ancestor. Never follow a link introduced during mkdir/open.
    for component in (logical, *logical.parents):
        if component.is_symlink() and not component.exists():
            raise ValueError('dangling resource root/parent; no writes performed')
    root = logical.resolve()
    missing = []
    ancestor = root
    while not ancestor.exists():
        missing.append(ancestor.name); ancestor = ancestor.parent
    fd = os.open(ancestor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in reversed(missing):
            try: os.mkdir(name, 0o755, dir_fd=fd)
            except FileExistsError: pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        if logical.resolve(strict=True) != root or not same(root.stat(), os.fstat(fd)):
            raise ValueError('root changed during preparation; no installation performed')
    finally: os.close(fd)
    return root

class OwnedDirectory:
    """Own one newly created flat directory; never sweep old staging trees."""
    def __init__(self, parent, name):
        self.parent, self.name, self.fd = parent, name, None
        self.files = {}
        with blocked_signals():
            os.mkdir(name, 0o700, dir_fd=parent)
            created = os.stat(name, dir_fd=parent, follow_symlinks=False)
            try:
                self.fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                if not same(created, os.fstat(self.fd)): raise ValueError('new directory changed')
            except BaseException:
                if self.fd is not None: os.close(self.fd); self.fd = None
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(current.st_mode) and same(current, created):
                    os.rmdir(name, dir_fd=parent)
                raise
    def write(self, name, data):
        with blocked_signals():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o644, dir_fd=self.fd)
            self.files[name] = os.fstat(fd)
        with os.fdopen(fd, 'wb') as stream: stream.write(data.encode('utf-8'))
    def check(self):
        entry = os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)
        if not stat.S_ISDIR(entry.st_mode) or not same(entry, os.fstat(self.fd)):
            raise ValueError('owned directory identity changed; retained: '+self.name)
    def clean(self):
        if self.fd is None: return
        self.check()
        # Validate the complete deletion set before unlinking anything.
        if set(os.listdir(anchor(self.fd))) != set(self.files):
            raise ValueError('unexpected staged member; retained: '+self.name)
        for name, owned in self.files.items():
            entry = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            if not stat.S_ISREG(entry.st_mode) or not same(entry, owned):
                raise ValueError('staged file changed; retained: '+name)
        for name in self.files: os.unlink(name, dir_fd=self.fd)
        os.rmdir(self.name, dir_fd=self.parent)
    def close(self):
        if self.fd is not None: os.close(self.fd); self.fd = None

def copy_payload(source, stage, compressed, reserve):
    with blocked_signals():
        fd = os.open('resource.data', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o644, dir_fd=stage.fd)
        stage.files['resource.data'] = os.fstat(fd)
    with os.fdopen(fd, 'wb') as out, source.open('rb') as raw:
        stream = gzip.GzipFile(fileobj=raw) if compressed else raw
        try:
            count = 0
            for block in iter(lambda: stream.read(1024*1024), b''):
                count += len(block)
                if shutil.disk_usage(anchor(stage.fd)).free < len(block) + reserve:
                    raise ValueError('insufficient space while decoding resource; no promotion')
                out.write(block)
        finally:
            if compressed: stream.close()

def promote(stage, root_fd, identity, unchanged, owned):
    unchanged(); stage.check()
    rename = getattr(ctypes.CDLL(None, use_errno=True), 'renameat2', None)
    if rename is not None:
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        with blocked_signals():
            if rename(root_fd, os.fsencode(stage.name), root_fd, os.fsencode(identity), 1) == 0:
                owned.remove(stage); stage.close(); return
            code = ctypes.get_errno()
        if code not in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            raise OSError(code, 'destination not replaced: '+os.strerror(code))
    # Host shares may not support RENAME_NOREPLACE. READY commits an exclusive
    # new directory; a reader rejects it until all immutable members are linked.
    with blocked_signals():
        dest = OwnedDirectory(root_fd, identity); owned.append(dest)
    for name in sorted(stage.files, key=lambda n: (n == 'READY', n)):
        unchanged(); dest.check(); stage.check()
        with blocked_signals():
            source = os.stat(name, dir_fd=stage.fd, follow_symlinks=False)
            if not stat.S_ISREG(source.st_mode) or not same(source, stage.files[name]):
                raise ValueError('staged file changed before publication')
            if name == 'READY': os.fchmod(dest.fd, 0o755)
            os.link(name, name, src_dir_fd=stage.fd, dst_dir_fd=dest.fd, follow_symlinks=False)
            dest.files[name] = os.stat(name, dir_fd=dest.fd, follow_symlinks=False)
            if name == 'READY':
                owned.remove(dest); dest.close()

def install(args):
    identity = args.resource
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', identity):
        raise ValueError('choose a safe explicit resource ID')
    source = Path(args.source).resolve(strict=True) if args.source else None
    item = CATALOG.get(identity)
    if item is None:
        if not identity.startswith('local-') or not args.assembly or not args.license_note or not args.kind or not re.fullmatch('[a-f0-9]{64}', args.sha256 or ''):
            raise ValueError('local-* requires --kind, --sha256, --assembly and --license-note')
        if bool(source) == bool(args.url): raise ValueError('choose exactly one --source or --url')
        if args.url:
            valid_url(args.url)
            if not args.bytes or args.bytes < 1: raise ValueError('positive --bytes required')
        item = dict(kind=args.kind, assembly=args.assembly, sha256=args.sha256,
                    bytes=source.stat().st_size if source else args.bytes, license=args.license_note)
        item.update(origin=source.name) if source else item.update(url=args.url)
    elif any((args.url, args.kind, args.sha256, args.assembly, args.license_note, args.bytes)):
        raise ValueError('catalog metadata is immutable; only --source may provide its exact cached bytes')
    if source and not source.is_file(): raise ValueError('source must be a regular file')
    if item['bytes'] < 1: raise ValueError('empty source is not a valid resource')
    logical_root = Path(args.resource_root).absolute()
    root = logical_root.resolve()
    target = root / identity
    required = (3 if item['kind'] == 'sam-checkpoint' else 12) * item['bytes'] + 67108864
    if args.dry_run:
        print(json.dumps(dict(resource=identity, source=item, target=str(target),
                              estimated_free_bytes=required), indent=2)); return
    root = create_root(logical_root)
    with signal_cleanup(), ExitStack() as handles:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        handles.callback(os.close, fd)
        def unchanged():
            current = logical_root.resolve(strict=True)
            if current != root or not same(current.stat(), os.fstat(fd)):
                raise ValueError('resource root/parent changed; transaction retained for inspection')
        unchanged()
        store = anchor(fd)
        for entry in store.iterdir():
            if not entry.name.startswith('.'): verify(entry, entry.name)
        if (store / identity).exists() or (store / identity).is_symlink():
            old = verify(store / identity, identity)
            if any(old['source'].get(k) != v for k, v in item.items()):
                raise ValueError('existing identity differs; choose new ID/root')
            unchanged()
            print('already installed; no writes or download', flush=True)
            return
        owned = []
        active_error = None
        try:
            # Block signals through creation AND ownership registration, including
            # the interval before the lock owner file exists.
            with blocked_signals():
                lock = OwnedDirectory(fd, '.jcvi-install.lock'); owned.append(lock)
            lock.write('owner.json', json.dumps(dict(pid=os.getpid(), uid=os.getuid(), time=time.time())))
            for entry in store.iterdir():
                if not entry.name.startswith('.'):
                    verify(entry, entry.name)
            if target.exists() or target.is_symlink():
                old = verify(store / identity, identity)
                if any(old['source'].get(k) != v for k, v in item.items()):
                    raise ValueError('existing identity differs; choose new ID/root')
                unchanged()
                result = 'already installed; no writes or download'
            else:
                if shutil.disk_usage(store).free < required: raise ValueError('insufficient free space')
                if source is None:
                    unchanged()
                    try: os.mkdir('.downloads', 0o700, dir_fd=fd)
                    except FileExistsError: pass
                    cache_fd = os.open('.downloads', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    handles.callback(os.close, cache_fd)
                    info = os.fstat(cache_fd)
                    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                        raise ValueError('download cache must be private and owned by installer')
                    name = item['sha256'] + '.part'
                    source_fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=cache_fd)
                    handles.callback(os.close, source_fd)
                    info = os.fstat(source_fd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
                        raise ValueError('unsafe partial file; retained')
                    if info.st_size < item['bytes']:
                        print('downloading '+identity+' (resume supported)', flush=True)
                        argv = ['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
                                '--retry', '3', '--retry-all-errors', '--connect-timeout', '30', '--max-time', '1800',
                                '--continue-at', '-', '--output', '/proc/self/fd/'+str(source_fd), item['url']]
                        child = None
                        try:
                            with blocked_signals():
                                child = subprocess.Popen(argv, pass_fds=(source_fd,), start_new_session=True,
                                    preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_UNBLOCK, SIGNALS))
                            code = child.wait()
                            if code: raise subprocess.CalledProcessError(code, argv)
                        finally:
                            # Signal only this newly-created, isolated child group.
                            if child is not None and child.poll() is None:
                                os.killpg(child.pid, signal.SIGTERM)
                                try: child.wait(timeout=5)
                                except subprocess.TimeoutExpired:
                                    os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=5)
                    # Refuse replacement of any cache path before consuming it.
                    if not same(os.stat('.downloads', dir_fd=fd, follow_symlinks=False), os.fstat(cache_fd)) or not same(os.stat(name, dir_fd=cache_fd, follow_symlinks=False), os.fstat(source_fd)):
                        raise ValueError('download cache identity changed; retained')
                else:
                    source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    handles.callback(os.close, source_fd)
                    if not stat.S_ISREG(os.fstat(source_fd).st_mode): raise ValueError('source is not regular')
                prepared = OpenFile(source_fd)
                unchanged()
                if prepared.stat().st_size != item['bytes'] or digest(prepared) != item['sha256']:
                    raise ValueError('source checksum/size mismatch; no promotion; cache retained for diagnosis')
                with blocked_signals():
                    stage = OwnedDirectory(fd, '.'+identity+'.stage-'+uuid.uuid4().hex); owned.append(stage)
                with prepared.open('rb') as probe:
                    compressed = item['kind'] != 'sam-checkpoint' and probe.read(2) == b'\x1f\x8b'
                copy_payload(prepared, stage, compressed, 67108864)
                if prepared.stat().st_size != item['bytes'] or digest(prepared) != item['sha256']:
                    raise ValueError('source changed during installation; no promotion')
                payload = anchor(stage.fd) / 'resource.data'
                actual_sha = digest(payload)
                if item.get('data_sha256', actual_sha) != actual_sha: raise ValueError('decoded payload checksum mismatch')
                item = dict(item, data_sha256=actual_sha)
                receipt = dict(schema=SCHEMA, resource=identity, source=item, data_bytes=payload.stat().st_size,
                    inventory=inventory(payload, item['kind']), created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), uid=os.getuid())
                stage.write('resource.json', json.dumps(receipt, sort_keys=True, indent=2)+'\n')
                stage.write('SHA256SUMS', ''.join(digest(anchor(stage.fd)/n)+'  '+n+'\n' for n in ['resource.data','resource.json']))
                stage.write('READY', digest(anchor(stage.fd)/'SHA256SUMS')+'\n')
                os.fchmod(stage.fd, 0o755)
                verify(anchor(stage.fd), identity)
                unchanged()
                promote(stage, fd, identity, unchanged, owned)
                result = 'installed resource='+identity+' root='+str(target)
        except BaseException as error:
            active_error = error
            raise
        finally:
            cleanup_errors = []
            with blocked_signals():
                for directory in reversed(owned):
                    try:
                        unchanged()
                        directory.clean()
                    except (OSError, ValueError, RuntimeError) as error:
                        cleanup_errors.append(str(error))
                    finally: directory.close()
            if cleanup_errors:
                message = 'cleanup incomplete; retained for inspection: '+'; '.join(cleanup_errors)
                if active_error is None: raise ValueError(message)
                try: print('jcvi-resources: '+message, file=sys.stderr)
                except OSError: pass
        print(result, flush=True)

def main():
    p = argparse.ArgumentParser(description='Explicit immutable FASTA/GFF3/OBO or fixed SAM model. No default selection or analysis-time download.')
    sub = p.add_subparsers(dest='command',required=True)
    sub.add_parser('list',help='fixed catalog; no download')
    v = sub.add_parser('verify',help='offline full inventory/checksum check; no writes')
    v.add_argument('root'); v.add_argument('--expected-resource')
    i = sub.add_parser('install',help='atomic fixed-member download/import into actual writable bind')
    i.add_argument('--resource',required=True); i.add_argument('--resource-root',required=True)
    i.add_argument('--source'); i.add_argument('--url'); i.add_argument('--sha256'); i.add_argument('--bytes',type=int)
    i.add_argument('--kind',choices=['fasta','gff3','obo']); i.add_argument('--assembly'); i.add_argument('--license-note')
    i.add_argument('--dry-run',action='store_true')
    args = p.parse_args(); os.umask(0o022)
    if args.command == 'list': print(json.dumps(CATALOG,indent=2))
    elif args.command == 'verify':
        receipt = verify(Path(args.root),args.expected_resource)
        print('verified resource='+receipt['resource'], flush=True)
    else: install(args)

if __name__ == '__main__':
    try: main()
    except (ValueError,OSError,KeyError,IndexError,TypeError,RuntimeError,zipfile.BadZipFile,subprocess.CalledProcessError) as e:
        print('jcvi-resources: '+str(e),file=sys.stderr); sys.exit(1)

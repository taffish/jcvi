"""Concentrated transaction regressions; no network, no production data."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
from unittest.mock import patch

module = os.environ.get('RESOURCE_MODULE', '/opt/jcvi/share/resource_validation.py')
spec = importlib.util.spec_from_file_location('resource_contract', module)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else ('file', sha(p), p.stat().st_mtime_ns) if p.is_file() else ('dir',)
            for p in root.rglob('*')}
def args(root, source, identity='local-new'):
    return argparse.Namespace(resource=identity, resource_root=str(root), source=str(source),
        url=None, sha256=sha(source), bytes=None, kind='fasta', assembly='synthetic-v1',
        license_note='TAFFISH synthetic fixture; Apache-2.0', dry_run=False)
def failure(call, code=None):
    try: call()
    except (ValueError, OSError, SystemExit) as e:
        if code is not None: assert isinstance(e, SystemExit) and e.code == code, e
    else: raise AssertionError('expected failure')
def resign(root):
    (root/'SHA256SUMS').write_text(''.join(sha(root/n)+'  '+n+'\n' for n in ['resource.data','resource.json']))
    (root/'READY').write_text(sha(root/'SHA256SUMS')+'\n')

cases = ['basic', 'bad-checksum', 'bad-old', 'root-alias', 'dangling', 'store-file',
         'lock-collision', 'old-stage', 'source-link', 'early-int', 'early-term',
         'stage-int', 'stage-term', 'copy-failure', 'parent-replaced', 'stage-replaced',
         'foreign-child', 'target-race', 'fallback', 'fallback-int', 'fallback-term',
         'output-closed', 'source-changed', 'low-space', 'open-lock-failure',
         'compressed-high-ratio', 'read-race', 'ctime-refresh', 'ctime-restored-mtime',
         'permissions-race', 'coarse-clock-write']
for case in cases:
    with tempfile.TemporaryDirectory(prefix='jcvi-safety-') as temporary:
        base = Path(temporary); source = base/'input.fa'; source.write_text('>s1\nACGTNN\n')
        parent = base/'parent'; parent.mkdir(); root = parent/'store'; root.mkdir()
        outside = base/'outside'; outside.mkdir(); (outside/'sentinel').write_text('keep')
        outside_before = snapshot(outside)
        old = args(root, source, 'local-old'); m.install(old)
        old_before = snapshot(root/'local-old'); a = args(root, source)
        mkdir = m.os.mkdir; write = m.OwnedDirectory.write; copy = m.copy_payload
        promote = m.promote; open_fd = m.os.open
        if case == 'basic':
            m.install(a); before = snapshot(root); m.install(a); assert snapshot(root) == before
            assert m.verify(root/'local-new')['resource'] == 'local-new'
            for defect in ('inventory', 'license', 'size', 'member-link', 'extra'):
                damaged = base/defect; shutil.copytree(root/'local-new', damaged)
                if defect == 'member-link':
                    (damaged/'resource.data').unlink(); (damaged/'resource.data').symlink_to(source)
                elif defect == 'extra': (damaged/'foreign').write_text('keep')
                else:
                    data = json.loads((damaged/'resource.json').read_text())
                    if defect == 'inventory': data['inventory'] = {'forged': 1}
                    elif defect == 'license': data['source']['license'] = ''
                    else: data['source']['bytes'] = 0
                    (damaged/'resource.json').write_text(json.dumps(data)); resign(damaged)
                failure(lambda: m.verify(damaged))
        elif case == 'bad-checksum':
            a.sha256 = '0'*64; failure(lambda: m.install(a))
        elif case == 'bad-old':
            (root/'local-old/READY').write_text('bad'); damaged = snapshot(root)
            failure(lambda: m.install(a)); assert snapshot(root) == damaged
        elif case in ('root-alias', 'dangling', 'store-file'):
            alias = base/'alias'
            if case == 'root-alias': alias.symlink_to(root); a.resource_root = str(alias); m.install(a)
            elif case == 'dangling':
                alias.symlink_to(base/'missing'); a.resource_root = str(alias)
                failure(lambda: m.install(a)); assert not (base/'missing').exists()
            else:
                alias.write_text('keep'); a.resource_root = str(alias); failure(lambda: m.install(a))
                assert alias.read_text() == 'keep'
        elif case in ('lock-collision', 'old-stage'):
            existing = root/('.jcvi-install.lock' if case == 'lock-collision' else '.local-new.stage-old')
            existing.mkdir(); (existing/'keep').write_text('recoverable')
            before = snapshot(existing)
            if case == 'lock-collision': failure(lambda: m.install(a))
            else: m.install(a)
            assert snapshot(existing) == before
        elif case == 'source-link':
            link = base/'source-link'; link.symlink_to(source); a.source = str(link); m.install(a)
        elif case in ('early-int', 'early-term', 'stage-int', 'stage-term'):
            sig = signal.SIGINT if case.endswith('int') else signal.SIGTERM
            def interrupt(name, *values, **kw):
                result = mkdir(name, *values, **kw)
                selected = str(name) == '.jcvi-install.lock' if case.startswith('early') else '.stage-' in str(name)
                if selected: os.kill(os.getpid(), sig)
                return result
            with patch.object(m.os, 'mkdir', interrupt): failure(lambda: m.install(a), 128+sig)
        elif case == 'copy-failure':
            def fail_copy(*values): copy(*values); raise OSError('injected I/O failure')
            with patch.object(m, 'copy_payload', fail_copy): failure(lambda: m.install(a))
        elif case in ('parent-replaced', 'stage-replaced', 'foreign-child', 'target-race', 'source-changed'):
            def change(prepared, stage, compressed, limit):
                copy(prepared, stage, compressed, limit)
                if case == 'parent-replaced': parent.rename(base/'original-parent'); parent.symlink_to(outside)
                elif case == 'stage-replaced':
                    (root/stage.name).rename(root/(stage.name+'-saved')); (root/stage.name).symlink_to(outside)
                elif case == 'foreign-child': (m.anchor(stage.fd)/'foreign').write_text('keep')
                elif case == 'target-race': (root/'local-new').mkdir(); (root/'local-new/sentinel').write_text('keep')
                else: source.write_text('>s1\nTTTTTT\n')
            with patch.object(m, 'copy_payload', change): failure(lambda: m.install(a))
            if case == 'parent-replaced': root = base/'original-parent/store'
            if case == 'foreign-child': assert any((p/'foreign').is_file() for p in root.glob('*.stage-*'))
            if case == 'target-race': assert (root/'local-new/sentinel').read_text() == 'keep'
        elif case in ('fallback', 'fallback-int', 'fallback-term'):
            link = m.os.link
            def interrupt_link(src, dst, **kw):
                result = link(src, dst, **kw)
                if case != 'fallback' and src == 'resource.data':
                    os.kill(os.getpid(), signal.SIGINT if case.endswith('int') else signal.SIGTERM)
                return result
            with patch.object(m.ctypes, 'CDLL', return_value=object()), patch.object(m.os, 'link', interrupt_link):
                if case == 'fallback': m.install(a); m.verify(root/'local-new')
                else: failure(lambda: m.install(a), 130 if case.endswith('int') else 143)
        elif case == 'output-closed':
            with patch('builtins.print', side_effect=BrokenPipeError('closed')): failure(lambda: m.install(a))
            m.verify(root/'local-new')
        elif case == 'low-space':
            with patch.object(m.shutil, 'disk_usage', return_value=shutil._ntuple_diskusage(1, 1, 0)):
                failure(lambda: m.install(a))
        elif case == 'open-lock-failure':
            def reject(path, *values, **kw):
                if path == '.jcvi-install.lock': raise OSError('injected directory-open error')
                return open_fd(path, *values, **kw)
            with patch.object(m.os, 'open', reject): failure(lambda: m.install(a))
        elif case == 'compressed-high-ratio':
            compressed=base/'input.fa.gz'
            compressed.write_bytes(gzip.compress(b'>repeat\n'+b'A'*1000000+b'\n'))
            a.source=str(compressed);a.sha256=sha(compressed)
            m.install(a);assert m.verify(root/'local-new')['inventory']=={'repeat':1000000}
        elif case == 'read-race':
            m.install(a);inventory=m.inventory
            def mutate(*values):
                result=inventory(*values)
                (root/'local-new/resource.data').write_text('>s1\nTTTTTT\n')
                return result
            with patch.object(m,'inventory',mutate):failure(lambda:m.verify(root/'local-new'))
        elif case in ('ctime-refresh', 'ctime-restored-mtime', 'permissions-race', 'coarse-clock-write'):
            m.install(a); original = m.verify_files; calls = [0]
            payload = root/'local-new/resource.data'; before_stat = payload.stat()
            def change_metadata(*values):
                result = original(*values); calls[0] += 1
                if calls[0] == 1:
                    if case in ('ctime-restored-mtime', 'coarse-clock-write'):
                        payload.write_text('>s1\nTTTTTT\n')
                        os.utime(payload, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
                    else: os.chmod(payload, 0o644 if case == 'ctime-refresh' else 0o600)
                return result
            with patch.object(m, 'verify_files', change_metadata):
                if case == 'ctime-refresh':
                    assert m.verify(root/'local-new')['resource'] == 'local-new'
                    # A same-mode chmod may not advance a coarse kernel clock.
                    assert calls[0] in (1, 2)
                elif case == 'coarse-clock-write':
                    # Hide all timestamp changes deterministically; content
                    # revalidation must still detect the same-length overwrite.
                    with patch.object(m.OpenFile, 'stat', lambda self: self.initial):
                        failure(lambda:m.verify(root/'local-new'))
                else: failure(lambda:m.verify(root/'local-new'))
        assert snapshot(outside) == outside_before, case
        if case != 'bad-old': assert snapshot(root/'local-old') == old_before, case
        if case not in ('lock-collision', 'parent-replaced'):
            assert not (root/'.jcvi-install.lock').exists(), case
        if case not in ('parent-replaced', 'stage-replaced', 'foreign-child', 'old-stage'):
            assert not list(root.glob('*.stage-*')), case
        # Retry after ordinary interruption/failure; pre-existing recovery trees
        # are intentionally not auto-deleted or reused.
        if case in ('early-int','early-term','stage-int','stage-term','copy-failure',
                    'fallback-int','fallback-term','low-space','open-lock-failure'):
            m.install(a); before = snapshot(root); m.install(a); assert snapshot(root) == before
        print('PASS', case, flush=True)
print('RESOURCE_SAFETY_PASS', len(cases))

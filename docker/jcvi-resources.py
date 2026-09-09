#!/usr/bin/env python3
"""按显式身份原子安装单个参考成员；分析阶段不下载，不替用户选择物种。"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
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
    """检查文本或固定模型 ZIP 成员；不反序列化 pickle，不代替实际模型推理。"""
    if kind == 'sam-checkpoint':
        with zipfile.ZipFile(path) as archive:
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

def verify(root, expected_resource=None):
    # 站点可用根链接公开资源；解析后审计成员，不允许成员链接绕过 inventory。
    try: root = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError('resource root cannot resolve to a directory') from error
    if not root.is_dir(): raise ValueError('resource root must resolve to a directory')
    members = {'resource.data', 'resource.json', 'SHA256SUMS', 'READY'}
    if {p.name for p in root.iterdir()} != members or any(p.is_symlink() or not p.is_file() for p in root.iterdir()):
        raise ValueError('missing/extra resource member or symlink')
    if digest(root/'SHA256SUMS') != (root/'READY').read_text().strip(): raise ValueError('invalid READY')
    rows = {}
    for line in (root/'SHA256SUMS').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        if name not in {'resource.data','resource.json'} or name in rows or not re.fullmatch('[a-f0-9]{64}', checksum):
            raise ValueError('invalid checksum inventory')
        if digest(root/name) != checksum: raise ValueError('checksum mismatch: '+name)
        rows[name] = checksum
    if set(rows) != {'resource.data','resource.json'}: raise ValueError('incomplete checksum inventory')
    receipt = json.loads((root/'resource.json').read_text())
    identity = receipt['resource']
    if receipt['schema'] != SCHEMA or not isinstance(identity,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',identity):
        raise ValueError('invalid resource identity')
    if expected_resource is not None and identity != expected_resource: raise ValueError('resource identity mismatch')
    if identity not in CATALOG and not re.fullmatch('local-[A-Za-z0-9_.-]+',identity): raise ValueError('unknown resource ID')
    source = receipt['source']
    if identity in CATALOG and source != CATALOG[identity]: raise ValueError('receipt differs from fixed catalog')
    if identity not in CATALOG and source['kind'] not in {'fasta','gff3','obo'}:
        raise ValueError('model imports require a fixed trusted catalog identity')
    if source['data_sha256'] != rows['resource.data'] or receipt['data_bytes'] != (root/'resource.data').stat().st_size:
        raise ValueError('invalid payload identity')
    if receipt['inventory'] != inventory(root/'resource.data',source['kind']): raise ValueError('resource inventory mismatch')
    print('verified resource='+identity,flush=True)
    return receipt

def install(args):
    identity = args.resource
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',identity): raise ValueError('choose a safe explicit resource ID')
    source = Path(args.source).resolve() if args.source else None
    item = CATALOG.get(identity)
    if item is None:
        if not identity.startswith('local-') or not args.assembly or not args.license_note or not args.kind or not re.fullmatch('[a-f0-9]{64}',args.sha256 or ''):
            raise ValueError('local-* requires --kind, --sha256, --assembly and --license-note')
        if bool(source) == bool(args.url): raise ValueError('choose exactly one --source or --url')
        if args.url:
            u = urlsplit(args.url)
            if u.scheme != 'https' or not u.hostname or u.username or u.password or not args.bytes or args.bytes < 1:
                raise ValueError('public HTTPS URL and positive --bytes required; do not embed credentials')
        item = dict(kind=args.kind,assembly=args.assembly,sha256=args.sha256,
            bytes=source.stat().st_size if source else args.bytes,license=args.license_note)
        item.update(origin=source.name) if source else item.update(url=args.url)
    elif any((args.url,args.kind,args.sha256,args.assembly,args.license_note,args.bytes)):
        raise ValueError('catalog metadata is immutable; only --source may provide its exact cached bytes')
    root = Path(args.resource_root).resolve()
    target = root/identity
    required = (3 if item['kind']=='sam-checkpoint' else 12)*item['bytes']+67108864
    if args.dry_run:
        print(json.dumps(dict(resource=identity,source=item,target=str(target),estimated_free_bytes=required),indent=2)); return
    if target.exists() or target.is_symlink():
        old = verify(target,identity)
        if any(old['source'].get(k) != v for k,v in item.items()): raise ValueError('existing identity differs; choose new ID/root')
        print('already installed; no writes or download'); return
    root.mkdir(parents=True,exist_ok=True)
    lock = root/('.'+identity+'.lock')
    try: lock.mkdir(mode=0o700)
    except FileExistsError: raise ValueError('lock exists; inspect owner before recovery: '+str(lock)) from None
    stage = None
    try:
        (lock/'owner.json').write_text(json.dumps(dict(uid=os.getuid(),pid=os.getpid(),time=time.time())))
        if shutil.disk_usage(root).free < required: raise ValueError('insufficient free space')
        if source is None:
            cache = root/'.downloads'
            if cache.is_symlink(): raise ValueError('download cache must not be symlink')
            cache.mkdir(mode=0o700,exist_ok=True)
            source = cache/(item['sha256']+'.part')
            if source.is_symlink(): raise ValueError('download member must not be symlink')
            if not source.exists() or source.stat().st_size < item['bytes']:
                print('downloading '+identity+' (resume supported)',flush=True)
                subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https','--retry','3',
                    '--retry-all-errors','--connect-timeout','30','--max-time','1800','--continue-at','-',
                    '--output',str(source),item['url']],check=True)
        if source.stat().st_size != item['bytes'] or digest(source) != item['sha256']:
            raise ValueError('source checksum/size mismatch; no promotion; cache retained for diagnosis')
        stage = Path(tempfile.mkdtemp(prefix='.'+identity+'.stage-',dir=root))
        with source.open('rb') as probe: compressed = item['kind']!='sam-checkpoint' and probe.read(2) == b'\x1f\x8b'
        opener = gzip.open if compressed else open
        with opener(source,'rb') as src, (stage/'resource.data').open('wb') as dst: shutil.copyfileobj(src,dst)
        actual_sha = digest(stage/'resource.data')
        if item.get('data_sha256',actual_sha) != actual_sha: raise ValueError('decoded payload checksum mismatch')
        item = dict(item,data_sha256=actual_sha)
        receipt = dict(schema=SCHEMA,resource=identity,source=item,data_bytes=(stage/'resource.data').stat().st_size,
            inventory=inventory(stage/'resource.data',item['kind']),
            created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),uid=os.getuid())
        (stage/'resource.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
        (stage/'SHA256SUMS').write_text(''.join(digest(stage/n)+'  '+n+'\n' for n in ['resource.data','resource.json']))
        (stage/'READY').write_text(digest(stage/'SHA256SUMS')+'\n')
        for p in stage.iterdir(): p.chmod(0o644)
        stage.chmod(0o755)
        verify(stage,identity)
        if target.exists() or target.is_symlink(): raise ValueError('target appeared; refusing overwrite')
        stage.rename(target); stage = None
        print('installed resource='+identity+' root='+str(target))
    finally:
        if stage is not None: shutil.rmtree(stage)
        (lock/'owner.json').unlink(missing_ok=True); lock.rmdir()

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
    elif args.command == 'verify': verify(Path(args.root),args.expected_resource)
    else: install(args)

if __name__ == '__main__':
    try: main()
    except (ValueError,OSError,KeyError,IndexError,zipfile.BadZipFile,subprocess.CalledProcessError) as e:
        print('jcvi-resources: '+str(e),file=sys.stderr); sys.exit(1)

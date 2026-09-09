"""离线资源回归：全新工作目录，不向镜像顶层伪造安装挂载。"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

helper='/usr/local/bin/jcvi-resources'
def run(*args,ok=True):
    p=subprocess.run([helper,*map(str,args)],capture_output=True,text=True)
    assert (p.returncode==0)==ok,(args,p.returncode,p.stdout,p.stderr)
    return p.stdout
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

run('list')
fixtures={
 'fasta': '>s1\nACGTNN\n>s2\nATGC\n',
 'gff3': '##gff-version 3\nchr1\ttest\tgene\t1\t9\t.\t+\t.\tID=g1\n',
 'obo': 'format-version: 1.2\n\n[Term]\nid: SO:0000704\nname: gene\nnamespace: sequence\n',
}
for kind,data in fixtures.items():
    source=Path('input.'+kind); source.write_text(data)
    args=['install','--resource','local-'+kind,'--resource-root','store','--source',source,
          '--kind',kind,'--sha256',sha(source),'--assembly','synthetic-offline',
          '--license-note','TAFFISH synthetic fixture; Apache-2.0']
    run(*args,'--dry-run')
    if kind=='fasta': assert not Path('store').exists()
    run(*args)
    root=Path('store/local-'+kind)
    before={p.name:(sha(p),p.stat().st_mtime_ns) for p in root.iterdir()}
    run(*args)
    assert before=={p.name:(sha(p),p.stat().st_mtime_ns) for p in root.iterdir()}
    run('verify',root,'--expected-resource','local-'+kind)
    run('verify',root,'--expected-resource','local-wrong',ok=False)
    link=Path('root-link-'+kind); link.symlink_to(root, target_is_directory=True)
    chain=Path('root-chain-'+kind); chain.symlink_to(link, target_is_directory=True)
    for selected in (link,chain):
        run('verify',selected,'--expected-resource','local-'+kind)
        run('verify',selected,'--expected-resource','local-wrong',ok=False)
    dangling=Path('root-dangling-'+kind); dangling.symlink_to('absent-'+kind)
    cycle=Path('root-cycle-'+kind); cycle.symlink_to(cycle.name)
    for selected in (dangling,cycle,source): run('verify',selected,ok=False)
    assert before=={p.name:(sha(p),p.stat().st_mtime_ns) for p in root.iterdir()}
    for defect in ['missing','extra','corrupt','symlink','identity','inventory']:
        damaged=Path('damaged-'+kind+'-'+defect); shutil.copytree(root,damaged)
        if defect=='missing': (damaged/'READY').unlink()
        elif defect=='extra': (damaged/'.unexpected').write_text('x')
        elif defect=='corrupt': (damaged/'resource.data').write_text('broken')
        elif defect=='symlink':
            (damaged/'resource.data').unlink(); (damaged/'resource.data').symlink_to((root/'resource.data').resolve())
        else:
            receipt=json.loads((damaged/'resource.json').read_text())
            receipt['resource' if defect=='identity' else 'inventory']='wrong'
            (damaged/'resource.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
            (damaged/'SHA256SUMS').write_text(''.join(sha(damaged/n)+'  '+n+'\n' for n in ['resource.data','resource.json']))
            (damaged/'READY').write_text(sha(damaged/'SHA256SUMS')+'\n')
        run('verify',damaged,'--expected-resource','local-'+kind,ok=False)
    bad=list(args); bad[bad.index('--resource')+1]='local-bad-'+kind; bad[bad.index('--sha256')+1]='0'*64
    run(*bad,ok=False); assert not Path('store/local-bad-'+kind).exists()
    assert not list(Path('store').glob('*.lock'))

from jcvi.formats.obo import GODag_from_SO,validate_term
try:
    GODag_from_SO()
except FileNotFoundError as error:
    assert 'Implicit ontology downloading is disabled' in str(error)
else:
    raise AssertionError('missing local ontology must fail closed before network')
shutil.copyfile('store/local-obo/resource.data','so.obo')
dag,filename=GODag_from_SO()
assert validate_term('gene',dag)=='gene' and filename=='so.obo'
print('jcvi-resource-atomic-idempotent-identity-inventory-offline-ontology-ok')

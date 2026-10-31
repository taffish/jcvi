"""Independent offline probes; buildtime excludes plots and full workflows."""
from pathlib import Path
import random
import runpy
import subprocess
import sys

def run(*args, expected=(0,)):
    p=subprocess.run(args,capture_output=True,text=True)
    print('$ '+' '.join(args),flush=True)
    print(p.stdout[-8000:]+p.stderr[-8000:],flush=True)
    if p.returncode not in expected:
        print(f'upstream-exit={p.returncode}: {args[0]}',flush=True)
        raise SystemExit(p.returncode if p.returncode>0 else 128-p.returncode)
    return p.stdout+p.stderr

def identity():
    assert run('jcvi','--version').strip()=='jcvi 1.6.8'
    assert 'Run jcvi modules' in run('jcvi','--help')
    import importlib.metadata as md
    import genomepy, mysql.connector, pyBigWig, pybedtools, pysam
    import jcvi, jcvi.assembly.chic, jcvi.formats.cblast
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    installed={canonicalize_name(d.metadata['Name']):d.version for d in md.distributions() if d.metadata['Name']}
    for d in md.distributions():
        for value in d.requires or []:
            r=Requirement(value)
            if r.marker and not r.marker.evaluate({'extra':''}): continue
            assert canonicalize_name(r.name) in installed,(d.name,str(r),'missing')
            assert installed[canonicalize_name(r.name)] in r.specifier,(d.name,str(r),'mismatch')
    assert md.version('jcvi')==jcvi.__version__=='1.6.8'

def modules():
    for name,marker in [('formats.fasta','Remove irregular chars in FASTA seqs'),
        ('formats.bed','Summarize the lengths of the intervals'),
        ('compara.synteny','Get anchor list using single-linkage algorithm')]:
        out=run('jcvi',name,expected=(0,1))
        assert 'Traceback' not in out and marker in out
    # New 1.6.8 selection/bytes paths: deterministic unit probes, no JGI token
    # or network, and no claim of a complete external Gblocks installation.
    from jcvi.apps.fetch import classify_phytozome_file, select_phytozome_files
    def file(name):
        return dict(_id=name, file_name=name, file_status='RESTORED', added_date='2020-01-01', metadata={})
    assert classify_phytozome_file(file('Vv_457_v2.1.gene.gff3.gz')) == 'gff'
    assert classify_phytozome_file(file('Vv_457_v2.1.gene_exons.gff3.gz')) is None
    assert classify_phytozome_file(file('Vv_457_v2.1.cds.fa.gz')) == 'cds'
    assert select_phytozome_files([]) == {}
    from unittest.mock import patch
    # Import-time defaults otherwise prompt for optional external executables.
    # This controlled unit probe exercises decoding, not those executables.
    with patch('jcvi.apps.base.getpath', side_effect=lambda program, **kwargs: program):
        from jcvi.apps.phylo import run_gblocks
    for output in (b'Gblocks alignment: 90 positions (90 %)\n', 'Gblocks alignment: 90 positions (90 %)\n'):
        with patch('jcvi.apps.phylo.GblocksCommandline') as fake:
            fake.return_value.run.return_value = (output, b'')
            assert run_gblocks('synthetic.fa') == 'synthetic.fa-gb'

def fasta():
    Path('input.fa').write_text('>seq2 description\nACGTNN\n>seq1\nAACCGGTT\n')
    run('jcvi','formats.fasta','ids','input.fa','-o','ids.txt')
    assert Path('ids.txt').read_text().splitlines()==['seq2','seq1']
    run('jcvi','formats.fasta','summary','input.fa','-o','summary.txt')
    assert 'Total' in Path('summary.txt').read_text()
    run('jcvi','formats.fasta','sort','input.fa')
    assert Path('input.sorted.fasta').read_text().splitlines()[0]=='>seq1'

def bedtools():
    from pybedtools import BedTool
    Path('a.bed').write_text('chr1\t0\t10\ta\nchr1\t20\t30\tb\n')
    Path('b.bed').write_text('chr1\t5\t25\tregion\n')
    rows=list(BedTool('a.bed').intersect(BedTool('b.bed'),wa=True))
    assert [(x.name,x.start,x.end) for x in rows]==[('a',0,10),('b',20,30)]

def graphics():
    from graphviz import Digraph
    from wand.image import Image
    from pypdf import PdfReader
    Path('numbers.txt').write_text('1\n2\n2\n3\n4\n')
    run('jcvi','graphics.histogram','--bins=4','numbers.txt')
    assert len(PdfReader('numbers.txt.pdf').pages)==1
    graph=Digraph(format='svg'); graph.edge('assembly','annotation')
    assert Path(graph.render(filename='graph',cleanup=True)).stat().st_size>0
    with Image(width=16,height=16,background='white') as img:
        img.format='png'; img.save(filename='wand.png')
    with Image(filename='wand.png') as img: assert (img.width,img.height)==(16,16)
    tests=runpy.run_path('/opt/jcvi/share/testdata/test_chromosome.py')
    count=0
    for name,fn in tests.items():
        if name.startswith('test_'): fn(); count+=1
    assert count==5

def synteny():
    from pypdf import PdfReader
    rng=random.Random(20260908)
    seqs=[''.join(rng.choices('ACGT',k=600)) for _ in range(8)]
    for species in ('a','b'):
        Path(species+'.cds').write_text(''.join(f'>{species}{i}\n{s}\n' for i,s in enumerate(seqs,1)))
        Path(species+'.bed').write_text(''.join(f'chr1\t{i*1000}\t{i*1000+600}\t{species}{i}\n' for i in range(1,9)))
    run('jcvi','compara.catalog','ortholog','a','b','--cpus=1','--notex','--no_strip_names')
    for name in ['a.b.last','a.b.anchors','a.b.lifted.anchors','a.b.pdf']: assert Path(name).stat().st_size>0
    run('jcvi','compara.synteny','mcscan','a.bed','a.b.lifted.anchors','--iter=1','-o','blocks.txt')
    pairs={tuple(line.split()[:2]) for line in Path('a.b.anchors').read_text().splitlines() if line and not line.startswith('#')}
    assert {(f'a{i}',f'b{i}') for i in range(1,9)}<=pairs,pairs
    assert len(PdfReader('a.b.pdf').pages)==1
    assert all(f'a{i}' in Path('blocks.txt').read_text() for i in range(1,9))

def helpers():
    Path('a.fa').write_text('>a\nACGTACGTACGTACGTACGTACGT\n')
    Path('b.fa').write_text('>b\nACGTTCGTACGTACGTACGTACGT\n')
    run('samtools','faidx','a.fa'); assert Path('a.fa.fai').stat().st_size>0
    run('needle','-auto','-asequence','a.fa','-bsequence','b.fa','-outfile','needle.txt')
    assert '# Program: needle' in Path('needle.txt').read_text()
    run('makeblastdb','-in','a.fa','-dbtype','nucl','-out','blastdb')
    run('blastn','-query','a.fa','-db','blastdb','-task','blastn-short','-dust','no','-outfmt','6','-out','hits.txt')
    assert Path('hits.txt').stat().st_size>0
    run('Rscript','-e','stopifnot(requireNamespace("ggplot2",quietly=TRUE))')
    assert 'tesseract ' in run('tesseract','--version')

def resources(): runpy.run_path('/opt/jcvi/share/testdata/resource-regression.py',run_name='__main__')

def sam():
    # Real CPU operators only; a random tiny model is not ViT-H scientific QA.
    import torch, torchvision
    from segment_anything.modeling import ImageEncoderViT, PromptEncoder, MaskDecoder, Sam, TwoWayTransformer
    assert torch.__version__=='2.8.0+cpu' and torchvision.__version__.split('+')[0]=='0.23.0'
    assert not torch.cuda.is_available()
    torch.set_num_threads(1); torch.manual_seed(167)
    model=Sam(image_encoder=ImageEncoderViT(img_size=64,patch_size=16,embed_dim=32,depth=1,
        num_heads=4,out_chans=32,window_size=2,use_rel_pos=True),
        prompt_encoder=PromptEncoder(embed_dim=32,image_embedding_size=(4,4),input_image_size=(64,64),mask_in_chans=8),
        mask_decoder=MaskDecoder(transformer_dim=32,
            transformer=TwoWayTransformer(depth=1,embedding_dim=32,num_heads=4,mlp_dim=64),
            iou_head_hidden_dim=32)).eval()
    with torch.inference_mode():
        result=model([dict(image=torch.zeros((3,64,64)),original_size=(64,64),
            point_coords=torch.tensor([[[32.,32.]]]),point_labels=torch.ones((1,1),dtype=torch.int))],True)[0]
    assert result['masks'].shape==(1,3,64,64) and torch.isfinite(result['iou_predictions']).all()
    boxes=torch.tensor([[0.,0.,10.,10.],[1.,1.,9.,9.]])
    assert torchvision.ops.nms(boxes,torch.tensor([.9,.8]),.5).tolist()==[0]
    print('SAM tiny CPU tensors and torchvision NMS PASS; full ViT-H is separately validated')

modes={f.__name__:f for f in [identity,modules,fasta,bedtools,graphics,synteny,helpers,resources,sam]}
mode=sys.argv[1]
selected=['identity','modules','fasta'] if mode=='buildtime' else list(modes) if mode=='all' else [mode]
for name in selected:
    print('stage='+name,flush=True); modes[name](); print(name+' PASS',flush=True)

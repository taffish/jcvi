#!/bin/sh
set -eu

mode="${1:-all}"

run_identity() {
  jcvi --version 2>&1 | grep -Fx 'jcvi 1.6.6' >/dev/null
  jcvi --help 2>&1 | grep -F 'Run jcvi modules' >/dev/null
  python - <<'PY'
import importlib.metadata as md

import genomepy
import mysql.connector
import pyBigWig
import pybedtools
import pysam
import jcvi
import jcvi.algorithms
import jcvi.annotation
import jcvi.apps
import jcvi.assembly
import jcvi.assembly.chic
import jcvi.compara
import jcvi.formats
import jcvi.formats.cblast
import jcvi.graphics
import jcvi.projects
import jcvi.utils
import jcvi.variation

assert md.version("jcvi") == "1.6.6"
assert jcvi.__version__ == "1.6.6"
print("jcvi-imports-ok")
PY
}

run_fasta() {
  tmp="/tmp/taf-jcvi-fasta-$$"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  cat > "$tmp/input.fa" <<'FASTA'
>seq2 description
ACGTNN
>seq1
AACCGGTT
FASTA
  jcvi formats.fasta ids "$tmp/input.fa" -o "$tmp/ids.txt"
  test "$(sed -n '1p' "$tmp/ids.txt")" = 'seq2'
  test "$(sed -n '2p' "$tmp/ids.txt")" = 'seq1'
  jcvi formats.fasta summary "$tmp/input.fa" -o "$tmp/summary.txt"
  grep -F 'seq1' "$tmp/summary.txt" >/dev/null
  grep -F 'Total' "$tmp/summary.txt" >/dev/null
  jcvi formats.fasta sort "$tmp/input.fa"
  test -s "$tmp/input.sorted.fasta"
  test "$(sed -n '1p' "$tmp/input.sorted.fasta")" = '>seq1'
  rm -rf "$tmp"
}

run_bedtools() {
  tmp="/tmp/taf-jcvi-bedtools-$$"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  cat > "$tmp/a.bed" <<'BED'
chr1	0	10	a
chr1	20	30	b
BED
  cat > "$tmp/b.bed" <<'BED'
chr1	5	25	region
BED
  A="$tmp/a.bed" B="$tmp/b.bed" OUT="$tmp/intersection.bed" python - <<'PY'
import os
from pybedtools import BedTool

result = BedTool(os.environ["A"]).intersect(BedTool(os.environ["B"]), wa=True)
result.saveas(os.environ["OUT"])
PY
  test "$(wc -l < "$tmp/intersection.bed" | tr -d ' ')" = '2'
  grep -F 'chr1' "$tmp/intersection.bed" >/dev/null
  rm -rf "$tmp"
}

run_graphics() {
  tmp="/tmp/taf-jcvi-graphics-$$"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  printf '1\n2\n2\n3\n4\n' > "$tmp/numbers.txt"
  (
    cd "$tmp"
    jcvi graphics.histogram --bins=4 numbers.txt
  )
  test -s "$tmp/numbers.txt.pdf"
  PDF="$tmp/numbers.txt.pdf" SVG="$tmp/graph.svg" PNG="$tmp/wand.png" python - <<'PY'
import os
from graphviz import Digraph
from wand.image import Image

graph = Digraph(format="svg")
graph.edge("assembly", "annotation")
rendered = graph.render(filename=os.environ["SVG"].removesuffix(".svg"), cleanup=True)
assert rendered == os.environ["SVG"]
assert os.path.getsize(rendered) > 0

with Image(width=16, height=16, background="white") as image:
    image.format = "png"
    image.save(filename=os.environ["PNG"])
assert os.path.getsize(os.environ["PNG"]) > 0
assert os.path.getsize(os.environ["PDF"]) > 0
print("jcvi-graphics-ok")
PY
  rm -rf "$tmp"
}

run_helpers() {
  tmp="/tmp/taf-jcvi-helpers-$$"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  cat > "$tmp/a.fa" <<'FASTA'
>a
ACGTACGT
FASTA
  cat > "$tmp/b.fa" <<'FASTA'
>b
ACGTTCGT
FASTA
  samtools faidx "$tmp/a.fa"
  test -s "$tmp/a.fa.fai"
  needle -auto -asequence "$tmp/a.fa" -bsequence "$tmp/b.fa" -outfile "$tmp/needle.txt"
  grep -F '# Program: needle' "$tmp/needle.txt" >/dev/null
  bedtools --version 2>&1 | grep -F 'bedtools v' >/dev/null
  embossversion -full 2>&1 | grep -F 'EMBOSS' >/dev/null
  dot -V 2>&1 | grep -F 'graphviz version' >/dev/null
  tesseract --version 2>&1 | grep -F 'tesseract ' >/dev/null
  Rscript -e 'stopifnot(requireNamespace("ggplot2", quietly=TRUE)); cat("R-ggplot2-ok\n")' | grep -Fx 'R-ggplot2-ok' >/dev/null
  rm -rf "$tmp"
}

case "$mode" in
  identity) run_identity ;;
  fasta) run_fasta ;;
  bedtools) run_bedtools ;;
  graphics) run_graphics ;;
  helpers) run_helpers ;;
  buildtime)
    run_identity
    run_fasta
    ;;
  all)
    run_identity
    run_fasta
    run_bedtools
    run_graphics
    run_helpers
    ;;
  *)
    echo "unknown jcvi smoke mode: $mode" >&2
    exit 2
    ;;
esac

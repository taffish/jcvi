jcvi 1.6.6-r1

Purpose:
  Run the JCVI comparative-genomics toolkit in a reproducible container.
  The default command is jcvi; Python and baseline helper tools are included.

Usage:
  taf-jcvi jcvi MODULE ACTION [OPTIONS] [INPUTS]
  taf-jcvi COMMAND [ARGS]

Common workflows:
  taf-jcvi jcvi formats.fasta summary assembly.fa
  taf-jcvi jcvi formats.fasta ids assembly.fa
  taf-jcvi jcvi formats.gff stats genes.gff3
  taf-jcvi jcvi compara.synteny mcscan sample.bed sample.anchors --iter=1
  taf-jcvi jcvi graphics.synteny blocks simple.bed layout

Discover modules and actions:
  taf-jcvi -- --help
  taf-jcvi jcvi formats.fasta
  taf-jcvi jcvi compara.synteny
  taf-jcvi jcvi graphics.synteny

Command-mode note:
  JCVI module names such as formats.fasta are arguments to jcvi, not programs.
  Use "taf-jcvi jcvi formats.fasta ...".
  Do not use "taf-jcvi formats.fasta ..." or
  "taf-jcvi -- formats.fasta ..." because TAFFISH would try to execute a
  container command named formats.fasta.

Packaged commands:
  jcvi           JCVI module dispatcher, version 1.6.6, and default command
  python         Python 3.12 with the complete declared JCVI dependency graph
  bedtools       Interval operations used by pybedtools and JCVI modules
  Rscript        R plotting runtime with ggplot2
  convert, dot   ImageMagick and Graphviz rendering helpers
  tesseract      OCR helper used by relevant graphics utilities
  EMBOSS         embossversion, needle, and the EMBOSS sequence-analysis suite
  HTS helpers    samtools, bgzip, and tabix

Python API:
  Put Python API code in a mounted script, then run:
  taf-jcvi python analysis.py
  Script files avoid shell interpretation of complex inline python -c code.

Inputs:
  FASTA/FASTQ          Sequences and assemblies
  BED/GFF/VCF          Intervals, annotation, and variants
  anchors/layout       MCscan, synteny, and graphics inputs
  references/metadata  Project resources supplied explicitly by the user

Outputs:
  JCVI actions may write to stdout or create files from an output prefix.
  Naming and overwrite behavior are module-specific; inspect action help.

Databases and network:
  No database, reference genome, or model bundle is embedded.
  Core local-file format, synteny, and plotting paths work offline.
  Download, NCBI, Ensembl, UCSC, cloud, and remote-query actions need network
  access and resources described by upstream.

Platform and resources:
  Native platforms: linux/amd64 and linux/arm64.
  CPU and memory needs follow the selected module and input size.
  Ordinary PDF, PNG, and SVG output uses a headless graphics backend.

Runtime boundary:
  The image contains all JCVI Python modules plus BEDTools, EMBOSS,
  ImageMagick/libmagic, Graphviz, Tesseract, R/ggplot2, Samtools, bgzip, and
  tabix.

  Specialized JCVI wrappers can call optional external software that is not
  JCVI itself. Kent tools, aligners, assemblers, and annotation systems outside
  the runtime list above are not promised. A host PATH command is not visible
  inside the container; check upstream requirements for the selected module.

Detailed documentation:
  https://github.com/tanghaibao/jcvi/wiki
  https://github.com/tanghaibao/jcvi/tree/v1.6.6

Wrapper options:
  taf-jcvi --help       Show this TAFFISH help.
  taf-jcvi --version    Show TAFFISH wrapper version.
  taf-jcvi --compile    Print generated shell code.
  taf-jcvi -- --help    Pass option-leading arguments to default jcvi.

Notes:
  Upstream JCVI is BSD-2-Clause; this TAFFISH packaging is Apache-2.0.
  Smoke covers real FASTA, BEDTools, plotting, Samtools, and EMBOSS paths, not
  production scientific validation or every optional external integration.

# jcvi

`jcvi` packages [JCVI](https://github.com/tanghaibao/jcvi) for TAFFISH.

Package identity:

- name: `jcvi`
- command: `taf-jcvi`
- kind: `tool`
- version: `1.6.6-r1`
- container image: `ghcr.io/taffish/jcvi:1.6.6-r1`
- TAFFISH app license: Apache-2.0
- upstream tag: <https://github.com/tanghaibao/jcvi/tree/v1.6.6>
- upstream runtime identity: `jcvi 1.6.6`

## What This App Packages

This app installs the complete JCVI 1.6.6 Python distribution from its
checksum-pinned PyPI source archive. JCVI provides command-line modules for
genome assembly and annotation, comparative genomics and synteny, common
genomics file formats, variation analysis, and publication-oriented graphics.

The image also contains the declared Python dependency graph and a practical
runtime baseline used directly by JCVI modules: BEDTools, EMBOSS, ImageMagick,
libmagic, Graphviz, Tesseract, R with ggplot2, Samtools, bgzip, and tabix.

## Scope

This app supports:

- every Python module shipped in the JCVI 1.6.6 distribution, including
  `assembly`, `annotation`, `compara`, `formats`, `graphics`, `projects`,
  `utils`, and `variation`
- FASTA, BED, GFF, VCF, anchor, layout, and related format operations
- MCscan/synteny preparation and visualization when the requested operation
  uses the packaged runtime
- Python API use through the packaged `python` interpreter
- headless PDF, PNG, and SVG generation through the packaged graphics stack

This app does not:

- bundle reference genomes or a JCVI database; core local-file operations do
  not require one
- promise every optional external program wrapped by a specialized JCVI
  module, such as the full Kent tools, BLAST+, LAST, BWA, Bowtie2, minimap2,
  MUMmer, GMAP/BLAT, CD-HIT, MUSCLE, RAxML, MAKER, PASA, or AUGUSTUS stacks
- make network-backed download, cloud, browser, or remote-query modules
  offline; those operations still require the resource and network access
  documented by upstream

## Container Contents

- `jcvi`: the upstream module dispatcher and default command
- `python`: the isolated Python 3.12 runtime containing JCVI and its declared
  Python dependencies
- `bedtools`: interval operations used by `pybedtools` and JCVI format modules
- `embossversion`, `needle`, and the EMBOSS suite: sequence-analysis helpers
- `convert`, `identify`, and libmagic: ImageMagick and file-type support
- `dot`: Graphviz rendering
- `tesseract`: OCR support used by relevant graphics utilities
- `Rscript` with `ggplot2`: R-backed plotting used by graphics modules
- `samtools`, `bgzip`, and `tabix`: indexed sequence and variant helpers

Resolved Python and Debian package inventories are retained in the image at
`/opt/jcvi/share/doc/jcvi/pip-freeze.txt` and
`/opt/jcvi/share/doc/jcvi/system-packages.tsv`.

## Usage

Show upstream help and version:

```sh
taf-jcvi -- --help
taf-jcvi -- --version
```

Summarize a FASTA file:

```sh
taf-jcvi jcvi formats.fasta summary assembly.fa
```

Inspect module-specific actions before running them:

```sh
taf-jcvi jcvi formats.gff
taf-jcvi jcvi compara.synteny
taf-jcvi jcvi graphics.synteny
```

Run common local-file operations:

```sh
taf-jcvi jcvi formats.fasta ids assembly.fa
taf-jcvi jcvi formats.gff stats genes.gff3
taf-jcvi jcvi compara.synteny mcscan sample.bed sample.anchors --iter=1
taf-jcvi jcvi graphics.synteny blocks simple.bed layout
```

Use the packaged Python API:

```python
# analysis.py
import jcvi

print(jcvi.__version__)
```

```sh
taf-jcvi python analysis.py
```

JCVI has many modules and action-specific arguments. Consult the
[upstream wiki](https://github.com/tanghaibao/jcvi/wiki) and inspect the module
or action help for the exact input contract used by a particular workflow.

## Command Mode

TAFFISH tool apps support automatic command mode. `jcvi` module names such as
`formats.fasta` are arguments to the `jcvi` dispatcher, not executables inside
the container. Therefore, prefer:

```sh
taf-jcvi jcvi formats.fasta summary assembly.fa
```

For option-leading default-command arguments, use the wrapper separator:

```sh
taf-jcvi -- --help
```

The `--` separator is useful for option-leading default-command arguments such
as `--help` and `--version`; it does not turn a following non-option module name
into a `jcvi` argument. Do not use bare `taf-jcvi formats.fasta ...` or
`taf-jcvi -- formats.fasta ...`; automatic command mode would try to execute a
program named `formats.fasta`.

Use `taf-jcvi python ...`, `taf-jcvi bedtools ...`, or another packaged command
when intentionally invoking that executable directly.

For Python API work, pass a mounted script file as shown above. This avoids
shell interpretation of punctuation inside a complex inline `python -c`
argument.

## Inputs

| Input | Meaning | Notes |
| --- | --- | --- |
| FASTA/FASTQ | sequences and assemblies | Exact validation depends on the selected action. |
| BED/GFF/VCF | intervals, annotation, and variants | Coordinate conventions remain those documented by JCVI. |
| anchors/layout/config files | comparative-genomics and graphics inputs | Required columns and names are action-specific. |
| project-specific resources | references, alignments, and metadata | Supply these explicitly; no reference bundle is embedded. |

## Output Notes

JCVI modules follow their upstream output naming and overwrite behavior. Some
actions write to standard output, while others create files beside the chosen
prefix or input. Run the relevant module/action help first and use explicit
output prefixes where available. Files written under the current mounted work
directory remain available on the host after the container exits.

## Resources, Databases, and Platform

- Native image platforms: `linux/amd64` and `linux/arm64`.
- No database or reference genome is embedded or downloaded automatically.
- Core format, synteny, and local plotting paths are offline-capable.
- Memory and CPU requirements depend on input size and module; large genome
  alignments and MCscan analyses should be sized for the source datasets.
- Modules that explicitly retrieve NCBI, Ensembl, UCSC, cloud, or other remote
  resources require network access and remain subject to those services.
- Matplotlib and related tools use a headless backend and writable temporary
  cache directories, so no display server is required for normal file output.

## Boundaries

JCVI is both a toolkit and an integration layer. Shipping the JCVI source does
not make every external aligner, assembler, annotation system, or Kent utility
that one specialized module can call part of JCVI itself. This image includes
the upstream Python dependency graph and the documented baseline above, while
keeping large, unrelated, or workflow-specific programs outside the app.

Because commands run inside the container, a tool present only on the host
`PATH` is not a hidden fallback. If a selected module reports a missing
executable, check upstream documentation and use a TAFFISH app or a purpose-built
revision that explicitly contains that backend. Such optional backend paths
are not covered by this app's smoke contract.

For cross-platform parity, the image omits the optional LDAP/SASL authentication
plugin bundled inside `mysql-connector-python`: its upstream arm64 wheel links
to the obsolete `libcrypto.so.10`. Regular `mysql.connector`, `genomepy`, and
JCVI imports remain packaged and tested; this corporate database authentication
plugin is not used by the declared local JCVI workflows.

## Troubleshooting

- `formats.fasta: command not found`: use
  `taf-jcvi jcvi formats.fasta ...`, not bare `taf-jcvi formats.fasta ...`.
- A module reports a missing aligner or annotation program: that operation uses
  an optional external backend outside this image's declared runtime baseline.
- A network/query action fails offline: provide network access or download the
  required resource separately and switch to the module's local-file mode.
- A plotting action needs a special font, TeX installation, or external viewer:
  those presentation extras are not part of the tested headless PDF/PNG/SVG
  path; use an explicit project image if the upstream action requires them.

## Testing

The independent-container smoke tests cover:

- wrapper metadata, command availability, upstream version, top-level help,
  representative module/action discovery, and compiled-extension imports
- real FASTA `ids`, `summary`, and `sort` operations with output assertions
- a real `pybedtools` interval intersection
- headless R/ggplot2 PDF, Graphviz SVG, and Wand/ImageMagick PNG generation
- real Samtools indexing and EMBOSS Needle output, plus bgzip/tabix, Tesseract,
  and helper identity checks
- offline execution for every runtime smoke path

The Dockerfile uses an architecture-safe build-time subset; the complete
graphics and helper smoke runs after image construction. These checks validate
packaging and representative functionality, not scientific correctness on a
production dataset or every optional JCVI integration.

## License and Citation

TAFFISH app packaging: Apache-2.0.

Upstream JCVI is distributed under BSD-2-Clause. The source archive, upstream
license, citation metadata, checksums, and resolved dependency inventories are
retained under `/opt/jcvi/share/`.

Please cite JCVI according to the upstream citation metadata, including:

> Tang H, Krishnakumar V, Li J, et al. JCVI: A versatile toolkit for comparative
> genomics analysis. *iMeta*. 2024. <https://doi.org/10.1002/imt2.211>

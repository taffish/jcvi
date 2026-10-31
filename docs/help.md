jcvi 1.6.8-r1

Purpose:
  Prepare genome files, find collinear genes and create headless genomics plots.

Usage:
  taf-jcvi -- --help
  taf-jcvi -- --version
  taf-jcvi jcvi formats.fasta summary assembly.fa
  Use "jcvi" before module names; bare "formats.fasta" is not an executable.

Common tasks:
  taf-jcvi jcvi formats.fasta ids assembly.fa -o ids.txt
  taf-jcvi jcvi formats.gff summary genes.gff3
  taf-jcvi jcvi compara.catalog ortholog species_a species_b --cpus=4 --notex
  taf-jcvi jcvi compara.synteny mcscan species_a.bed species_a.species_b.anchors --iter=1 -o blocks.txt
  taf-jcvi jcvi graphics.synteny blocks simple.bed layout --notex

Required inputs:
  FASTA sequences; BED/GFF annotation; action-specific anchors/layout files.
  "ortholog a b" needs a.cds, b.cds, a.bed and b.bed in the work directory.
  BED IDs must match CDS IDs. Match assembly, chromosome names and coordinates.
  Use a new writable work directory; JCVI may create indexes beside inputs.
  Avoid spaces/shell metacharacters in JCVI workflow paths (upstream shell calls).

Common options:
  --cpus=N       Limit threads where the action supports it.
  -o FILE        Explicit output for actions that support it; inspect action help.
  --notex        Use native text rendering in supported plotting actions.

Key outputs:
  FASTA summaries/IDs; .last alignments, .anchors and .lifted.anchors; plot PDF.
  Names depend on the action; existing files may be reused or overwritten.

Backend-specific use (CPU CLI, static PDF/PNG/SVG; no GPU/display/port required):
  Docker:    TAFFISH_CONTAINER_BACKEND=docker taf-jcvi jcvi formats.fasta summary assembly.fa
  Podman:    TAFFISH_CONTAINER_BACKEND=podman taf-jcvi jcvi formats.fasta summary assembly.fa
  Apptainer: TAFFISH_CONTAINER_BACKEND=apptainer taf-jcvi jcvi formats.fasta summary assembly.fa
  Apptainer requires native Linux; macOS users can use Docker/Podman Linux VMs.

Optional resource installation (choose ONE reference or model; no default):
  taf-jcvi jcvi-resources list
  base="${TAFFISH_USER_HOME:-$HOME/.local/share/taffish}/resources/jcvi"
  mkdir -p "$base"
  Docker:    TAFFISH_CONTAINER_BACKEND=docker TAFFISH_JCVI_RESOURCE_INSTALL_ROOT="$base" taf-jcvi jcvi-resources install --resource ensembl-r116-yeast-fasta --resource-root /resource-install
  Podman:    TAFFISH_CONTAINER_BACKEND=podman TAFFISH_JCVI_RESOURCE_INSTALL_ROOT="$base" taf-jcvi jcvi-resources install --resource ensembl-r116-yeast-fasta --resource-root /resource-install
  Apptainer: TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_JCVI_RESOURCE_INSTALL_ROOT="$base" taf-jcvi jcvi-resources install --resource ensembl-r116-yeast-fasta --resource-root /resource-install
  Run only your backend's line; add --dry-run to preview source/space.
  This example is yeast R64-1-1, NOT a universal reference. GFF is a separate member.
  For SAM, replace the example ID with sam-vit-h-4b8939 (2.6 GB; allow 8 GB free).
  Local FASTA/GFF3/OBO or another pinned HTTPS member: jcvi-resources install --help

Reuse personal or administrator-installed resources (all three backends):
  export TAFFISH_JCVI_RESOURCE_ID=ensembl-r116-yeast-fasta
  taf-jcvi jcvi-resources verify /jcvi-resource
  taf-jcvi cp /jcvi-resource/resource.data reference.fa
  taf-jcvi jcvi formats.fasta summary reference.fa
  Copy into your work directory when an action needs writable sidecar indexes.
  Discovery: personal resources, /usr/local/share/taffish/resources/jcvi/ID,
  then /opt/taffish/resources/jcvi/ID; selected member is mounted read-only.
  Override: TAFFISH_JCVI_RESOURCE_PATH=/safe/path/to/ID
  Disable discovery: TAFFISH_JCVI_RESOURCE_AUTO_MOUNT=0
  Root symlinks resolve physically; member symlinks, wrong IDs or corrupt units fail.
  Auto-mount needs host Python 3; without it use verified manual binds (README).

Optional SAM seed segmentation (install sam-vit-h-4b8939 above first):
  export TAFFISH_JCVI_RESOURCE_ID=sam-vit-h-4b8939
  Docker:    TAFFISH_CONTAINER_BACKEND=docker taf-jcvi jcvi graphics.grabseeds seeds seeds.jpg --filter=sam --sam-checkpoint=/jcvi-resource/resource.data --notex --outdir=results -o seeds.tsv
  Podman:    TAFFISH_CONTAINER_BACKEND=podman taf-jcvi jcvi graphics.grabseeds seeds seeds.jpg --filter=sam --sam-checkpoint=/jcvi-resource/resource.data --notex --outdir=results -o seeds.tsv
  Apptainer: TAFFISH_CONTAINER_BACKEND=apptainer taf-jcvi jcvi graphics.grabseeds seeds seeds.jpg --filter=sam --sam-checkpoint=/jcvi-resource/resource.data --notex --outdir=results -o seeds.tsv
  CPU only; allow 12 GB available RAM and minutes/image. Classic canny needs no model.
  Inspect masks/counts before use; SAM must not be combined with --edges/--watershed.

Immediate notes:
  Before --verifySO, select a prepared SO OBO member and copy resource.data to
  so.obo in a NEW work directory. GO consumers similarly need go-basic.obo.
  Missing resources fail closed; interruption retains partials and old recovery trees.
  Phytozome requires your JGI token; fetch actions need network/rights (see upstream help).
  Missing optional aligner: use a dedicated tool/workflow image; host PATH is not a fallback.
  Read-only error: use writable output/scratch or an actual install bind; never chmod SIF.

More help:
  taf-jcvi jcvi compara.catalog ortholog --help
  taf-jcvi jcvi-resources install --help
  https://github.com/taffish/jcvi

Wrapper options:
  taf-jcvi --help       This task-oriented help.
  taf-jcvi --version    Wrapper identity.
  taf-jcvi -- --help    Upstream help.

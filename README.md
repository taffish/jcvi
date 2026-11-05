# jcvi

`jcvi` packages [JCVI](https://github.com/tanghaibao/jcvi) for TAFFISH.

Package identity:

- name / command / kind: `jcvi` / `taf-jcvi` / `tool`
- version: `1.6.9-r1`; image: `ghcr.io/taffish/jcvi:1.6.9-r1`
- packaging license: Apache-2.0; actual upstream LICENSE: BSD-2-Clause
- upstream: [v1.6.9](https://github.com/tanghaibao/jcvi/tree/v1.6.9),
  commit `687c5d3e62f9a60f040cf4a80b08d60dee5be6fd`

## What This App Packages

The complete JCVI Python distribution is compiled from the checksum-pinned
1.6.9 PyPI source archive, including its Cython extensions. This release updates
LAST query batching and streams BLAST filtering and anchor liftover. It also fixes heatmap legends, gene labels on rotated tracks, reversed karyotype spacing and TeX fallback. The package preserves the upstream analysis algorithms. A narrow ontology I/O guard
rejects implicit GO/SO downloads when the explicitly prepared local OBO is missing.

The wrapper retains the upstream dispatcher and automatic executable mode.
Its only initialization is backend-specific user identity and optional
verified resource mounts. The separate resource installer supplies immutable
identities, checksums, atomic promotion and administrator-once sharing missing
from the upstream download helpers.

## Scope

This app supports:

- local FASTA/BED/GFF preparation and the packaged JCVI Python API;
- default LAST-based MCscan ortholog, anchor, liftover and local synteny paths;
- headless PDF/PNG/SVG graphics, including the 1.6.7 chromosome clipping fixes;
- Grabseeds classic filters and optional SAM ViT-H CPU segmentation;
- explicitly selected reusable FASTA/GFF3/OBO members and a fixed SAM checkpoint.

This app does not:

- promise every external program invoked by a specialized JCVI module;
- include a production reference, trained model or complete database family;
- provide an interactive desktop, GPU service or hosted web application;
- repair legacy external web services or supply account credentials.

## Container Contents

- JCVI and its declared Python dependency graph in Python 3.12;
- LAST and BLAST+ for core sequence alignment;
- BEDTools, EMBOSS, Samtools, bgzip/tabix for interval/sequence operations;
- ImageMagick/Wand, libmagic, Graphviz, Tesseract and R/ggplot2 for graphics;
- Segment Anything at commit `dca509fe793f601edb92606367a655c15ac00fdf`,
  PyTorch 2.8.0 CPU and torchvision 0.23.0 (official architecture-specific wheels);
- `jcvi-resources`: explicit, verified single-member installation.

The base image is digest-pinned. Runtime versions are constrained in
`docker/constraints.txt`; actual per-architecture pip install reports (URLs and
artifact hashes), freezes, Debian inventories, source archive, LICENSE and
CITATION remain under `/opt/jcvi/share/`. Debian packages and isolated
build-backend tooling are resolved during build; this is not a claim of
bit-for-bit reproducible image rebuilds. Pinned files can also disappear from
upstream hosting. Biopython is fixed at 1.85 because JCVI still imports
`Bio.Emboss.Applications` and `Bio.Phylo.Applications`, absent in 1.88;
no upstream analysis code is changed.
The image supplies `LOGNAME=taffish` and `USER=taffish` as display-name defaults
for arbitrary numeric UIDs without a passwd entry. They do not change UID/GID
or permissions and are not a real contact address or account credential.

Build caches, Python test suites, static archives and PyTorch C++ headers/CMake/
protoc are excluded. SAM uses eager CPU inference; this is not a C++ extension
development or `torch.compile` environment. Runtime libraries, `torch_shm_manager`,
licenses and EMBOSS reference/index data are retained.

## Installation and Usage

Install TAFFISH and a working Docker, Podman or native Linux Apptainer backend.
After this release is published and available in the Hub Index:

```sh
taf install jcvi 1.6.9-r1
taf-jcvi-v1.6.9-r1 --version
```

The examples below use the installed `taf-jcvi` default alias; use the versioned
command when multiple releases coexist.

```sh
taf-jcvi -- --help
taf-jcvi -- --version
taf-jcvi jcvi formats.fasta summary assembly.fa
taf-jcvi jcvi formats.gff summary genes.gff3
taf-jcvi jcvi compara.catalog ortholog species_a species_b --cpus=4 --notex
taf-jcvi jcvi compara.synteny mcscan species_a.bed species_a.species_b.anchors --iter=1 -o blocks.txt
taf-jcvi jcvi graphics.synteny blocks merged.bed blocks.layout --notex
taf-jcvi python analysis.py
```

Ortholog requires matching `species_a.cds` / `.bed` and `species_b.cds` / `.bed`.
Gene IDs, assembly and coordinates must match. See the
[official MCscan tutorial](https://github.com/tanghaibao/jcvi/wiki/MCscan-(Python-version))
for action-specific contracts.

For a local synteny plot, `--genelabels=GENE_ID` draws that gene at size 6 by default; `--genelabelsize=0` hides it. The default label angle is 25 degrees. Setting `--genelabelrotation=0` places text on the track, where it can overlap a neighbouring gene; use the default angle or a larger figure for dense tracks. Landscape heatmap percentages are scaled per track, not across tracks.

## Backend Usage and Capability Matrix

| Capability | Docker | Podman | Apptainer |
| --- | --- | --- | --- |
| CPU CLI / headless plots | Linux container | rootless Linux container | native Linux, read-only SIF |
| Prepared reference reuse | read-only volume | read-only volume | read-only bind |
| Explicit installer | actual writable volume, invoking UID | keep-id writable volume | ordinary-user writable bind |
| Grabseeds SAM CPU | external read-only checkpoint | external read-only checkpoint | external read-only checkpoint |
| GUI / GPU / service | N/A: not a JCVI interface | same | same |

Select one `TAFFISH_CONTAINER_BACKEND` value: `docker`, `podman` or `apptainer`.
Native images target Linux amd64 and arm64. macOS uses Docker/Podman Linux VMs;
Apptainer is a Linux route. No device/display/port arguments are required.
Testing below owns validation status; support does not mean every cross-product
of architecture and backend was separately tested.

## Command Mode

Use `taf-jcvi jcvi formats.fasta ...`: the module is an argument to JCVI, not an
executable. Bare `taf-jcvi formats.fasta` and `taf-jcvi -- formats.fasta` select
a nonexistent executable. The separator is for option-leading default-command
arguments such as `-- --help`. `taf-jcvi python script.py` and other packaged
commands retain automatic executable mode.

## Inputs

| Input | Meaning | Notes |
| --- | --- | --- |
| FASTA/CDS/peptide | genome or gene sequences | Match nucleotide/protein mode. |
| BED/GFF3 | positions / annotation | Match IDs, assembly and coordinates. |
| anchors / blocks / layout | comparative-genomics and plot inputs | Formats are action-specific. |
| OBO / references | optional reusable input | Explicit snapshot and license; never infer species. |

## Output Notes

Run in a new writable directory. Actions may create indexes beside inputs,
reuse existing products or overwrite named outputs. Copy references from
read-only storage into work when sidecar writes are needed. Avoid whitespace
and shell metacharacters in JCVI workflow paths: upstream integration helpers
construct shell commands. Matplotlib uses Agg and its ordinary user cache or
writable temporary fallback; caches are not persistent reference data.

## Resources, Databases, and Platform

Core genomics and classic Grabseeds need no trained model. Optional Grabseeds
`--filter sam` needs the official ViT-H checkpoint. The smallest reusable resource
is one assembly FASTA, matching GFF3 annotation, GO/SO OBO snapshot or fixed model.
Project-specific alignments/layouts remain explicit inputs. Three independent catalog
members are available; none is downloaded by default:

| ID | Fixed source | Download bytes | Installed payload |
| --- | --- | --- | --- |
| ensembl-r116-yeast-fasta | R64-1-1, release-116 FASTA | 3784201 | decoded FASTA |
| ensembl-r116-yeast-gff3 | annotation 63 under release-116 | 1091237 | decoded GFF3 |
| sam-vit-h-4b8939 | official SAM ViT-H checkpoint | 2564550879 | unchanged PyTorch checkpoint |

`jcvi-resources list` shows full URLs, source/decoded SHA256 and attribution.
Checksums are maintainer observations of fixed official files, not upstream
cryptographic signatures. This yeast example is not a universal reference.

### Personal installation and read-only reuse

```sh
base="${TAFFISH_USER_HOME:-$HOME/.local/share/taffish}/resources/jcvi"
mkdir -p "$base"
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_JCVI_RESOURCE_INSTALL_ROOT="$base" \
  taf-jcvi jcvi-resources install --resource ensembl-r116-yeast-fasta --resource-root /resource-install
export TAFFISH_JCVI_RESOURCE_ID=ensembl-r116-yeast-fasta
taf-jcvi jcvi-resources verify /jcvi-resource
taf-jcvi cp /jcvi-resource/resource.data reference.fa
taf-jcvi jcvi formats.fasta summary reference.fa
```

For Podman or Apptainer replace the backend value; help provides all three full
invocations. Installation needs network unless `--source` supplies exact cached
bytes. Verification and local analysis are offline. `--dry-run` previews the
source, target and conservative space estimate.

Discovery for the selected ID: personal root above, then
`/usr/local/share/taffish/resources/jcvi/ID`, then `/opt/taffish/resources/jcvi/ID`.
`TAFFISH_SYSTEM_HOME` can relocate the first site prefix from `/usr/local/share/taffish`.
`TAFFISH_JCVI_RESOURCE_PATH` overrides with one prepared unit; an ID also set
must agree. `TAFFISH_JCVI_RESOURCE_AUTO_MOUNT=0` disables discovery.
Invalid personal units fail closed rather than falling back to another site
copy. Automatic verification requires host Python 3 (standard library only);
the frozen host module and container installer use the same complete contract.
Without host Python, disable discovery and use the verified manual-bind path below.
Mount paths cannot contain colon or comma (backend syntax); valid root aliases
resolve physically. Ordinary spaces are supported for resource mounts, but JCVI
workflow shell calls still have the separate path restriction above.

### Administrator-once installation

An authorized administrator prepares the site parent once and invokes the same
wrapper with `TAFFISH_JCVI_RESOURCE_INSTALL_ROOT=/usr/local/share/taffish/resources/jcvi`.
The helper never calls sudo, escalates or changes an existing parent's owner.
Docker/Podman rootless stores and Apptainer availability follow site policy.
Final units are 0755 with 0644 files; parents must permit user traversal.
Ordinary users select the same ID without INSTALL_ROOT and receive read-only
mounts. They need not download again or change shared permissions.
Restricted resources require a licensed group and controlled store instead of
world-readable publication; follow their actual sharing terms.

### Grabseeds SAM: install once, reuse without downloads

Choose `sam-vit-h-4b8939` instead of the yeast ID in the personal or administrator
installation command. This downloads about 2.6 GB; allow about 8 GB free during
installation (cache plus atomic staging). No weights are embedded in the image.
An administrator can install the same fixed unit at the site root once for all
ordinary users. Select it with the same resource variables on all three backends:

```sh
export TAFFISH_JCVI_RESOURCE_ID=sam-vit-h-4b8939
taf-jcvi jcvi-resources verify /jcvi-resource
taf-jcvi jcvi graphics.grabseeds seeds seeds.jpg --filter=sam --sam-checkpoint=/jcvi-resource/resource.data --notex --outdir=results -o seeds.tsv
```

The upstream JCVI path hardcodes ViT-H and runs on CPU; no CUDA/GPU flags are
needed or offered. Allow at least 12 GB available RAM and several minutes per
image; input complexity and CPU affect cost. Use a fresh writable work directory
and output directory. Inspect seed counts, masks and calibration before scientific
use. Classic `--filter=canny` needs no checkpoint and is the lower-cost alternative.
Do not combine SAM with `--edges`/`--watershed`: these are classic-filter options.
Do not replace the file with another SAM variant or an untrusted pickle model.
The helper accepts only the fixed official checkpoint bytes for model installation;
it inventories ZIP members without unpickling. Weight loading happens only when
the user explicitly invokes SAM. SHA256:
`a7bf3b02f3ebf1267aba913ff637d9a2d5c33d3173bb679e46d9f338c26f262e`.

### Other fixed members and authorized imports

Use a fresh `local-*` ID, exact SHA256, type, snapshot and license note:

```sh
TAFFISH_JCVI_RESOURCE_INSTALL_ROOT="$base" taf-jcvi jcvi-resources install \
  --resource local-my-so-snapshot --resource-root /resource-install \
  --source so.obo --kind obo --sha256 SHA256_OF_AUTHORIZED_FILE \
  --assembly SNAPSHOT_ID --license-note '"Authorized use and sharing terms"'
```

For a public fixed HTTPS member, replace `--source` with `--url URL --bytes N`;
retain the kind, checksum, snapshot and license. Do not embed credentials or
bypass authentication. Obtain Phytozome/account-controlled inputs through the
official authorized route, then import only when storage/sharing is permitted.
GO/SO licenses are independent of JCVI; record the snapshot's terms (see
[GO citation policy](https://geneontology.org/docs/go-citation-policy/)).
[Ensembl terms](https://jun2026.archive.ensembl.org/info/about/legal/disclaimer.html)
allow unrestricted project data but retain third-party constraints.

The installer writes and validates a complete installed-member inventory and
READY marker for each selected unit, including a root with only one chosen member.
Each unit contains only `resource.data` (decoded text or unchanged model), `resource.json`
(source/identity/logical inventory), `SHA256SUMS` and `READY`. Verification
resolves root symlinks to physical directories before validation and read-only
binding; dangling or cyclic roots are rejected. Wrong identity, missing/extra
members, member symlinks, corruption or inventory mismatch remain errors.
Existing valid units are idempotent; changed data need a new ID.
Verification independently rechecks every member's contents after the semantic
inventory read; timestamps are not used as proof that the bytes stayed unchanged.
Read-only VM file sharing may refresh `ctime`; that alone triggers one additional
full validation. Changed contents, identity, modification time or permissions
still fail, including equal-size writes within one filesystem clock tick.
A private `.jcvi-install.lock` serializes installations in one store. New-member
installation validates all existing members; an unrelated broken member is not
silently accepted. No `--force` overwrite or automatic cache deletion is offered:
changed data need a new ID/root. Managed-resource discovery never downloads;
preparing one of these members requires an explicit helper installation.

INT/TERM clean only files and directories owned by this transaction, including
interruption before lock metadata is written. Existing staging/recovery directories
and partial downloads are retained. Parent/member replacement or unexpected files
fail closed with diagnostics; cleanup never follows their links. A valid completed
member is reusable without writes or network. On supported filesystems publication
uses no-replace rename; elsewhere an exclusively created directory becomes readable
only when READY is committed last. Readers reject any incomplete unit.

Interrupted HTTPS downloads resume from the checksum-named `.downloads/*.part`;
a zero-byte partial restarts normally, while oversized or checksum-invalid cache
fails without promotion. Inspect the specific cache or stale lock and its owner
before manual recovery; do not remove a live lock or sweep old staging trees.
Gzip is decoded during staging with ongoing free-space checks. Allow room for both
compressed and decoded data; permissions/disk exhaustion fail without replacing old data.

GO/SO default-URL consumers require a verified OBO unit copied as `so.obo` or
`go-basic.obo` into a fresh work directory before use. The upstream downloader
uses that local filename. A narrowly scoped packaging guard rejects missing
local files before any network request, replacing upstream's implicit default-URL
download. It does not rewrite ontology parsing/terms or substitute another snapshot.
Use the explicit resource helper to obtain a fixed OBO before analysis.

### Manual bind fallback

Disable discovery, then bind one prepared read-only unit (replace the safe
absolute `/srv/jcvi/ID` path):

```sh
TAFFISH_CONTAINER_BACKEND=docker TAFFISH_JCVI_RESOURCE_AUTO_MOUNT=0 TAFFISH_DOCKER_RUN_ARGS='--volume=/srv/jcvi/ID:/jcvi-resource:ro' taf-jcvi jcvi-resources verify /jcvi-resource
TAFFISH_CONTAINER_BACKEND=podman TAFFISH_JCVI_RESOURCE_AUTO_MOUNT=0 TAFFISH_PODMAN_RUN_ARGS='--volume=/srv/jcvi/ID:/jcvi-resource:ro' taf-jcvi jcvi-resources verify /jcvi-resource
TAFFISH_CONTAINER_BACKEND=apptainer TAFFISH_JCVI_RESOURCE_AUTO_MOUNT=0 TAFFISH_APPTAINER_RUN_ARGS='--bind=/srv/jcvi/ID:/jcvi-resource:ro' taf-jcvi jcvi-resources verify /jcvi-resource
```

These are site/storage overrides, not mandatory per-run app flags.

## Phytozome / JGI access

JCVI 1.6.9 uses the official JGI Data Portal REST API. Downloads require your
own authorized JGI session token and may be subject to organism-specific data-use
conditions. The app does not supply, persist or log credentials, accept terms for
you, or guarantee hosted-service availability. Inspect
`taf-jcvi jcvi apps.fetch phytozome --help` and follow JGI's current sign-in flow.
No authenticated JGI download is part of the packaging acceptance tests.
After authorized retrieval, import only snapshots whose license permits your
intended local/site sharing; do not put tokens in URLs, manifests or shell history.

## Boundaries

SAM is included as the CPU library used by JCVI, not as the separate SAM React
demo, ONNX deployment or hosted service. No GPU capability is claimed. JCVI's
default Grabseeds method remains classic `canny`; SAM requires explicit selection.

All shipped modules remain present, but presence is not complete functional
coverage. Specialized Kent/BLAT, BWA/Bowtie2, minimap2, MUMmer, GMAP, CD-HIT,
MUSCLE, Gblocks, RAxML, MAKER, PASA and AUGUSTUS integrations are not bundled or fully tested.
The earlier Gblocks bytes/text decoding change is checked with controlled output;
this is not an execution of an external Gblocks installation. Debian main for the
selected base does not provide that optional executable; no non-free binary or
new external phylogeny stack has been added.
Use separate tools/workflow images; host PATH is not a fallback. Default MCscan
LAST is included; optional DIAMOND is not.

Official JCVI extras, entry points and wiki companions were audited: MCscan,
ALLMAPS and GRABSEEDS are CLI/static graphics. ETE4's optional visualization
interface is not called as a JCVI service; wga2ribbon exports files for the
separate Ribbon viewer. There is no JCVI GUI/noVNC/GPU interface to expose.
Legacy `utils.taxonomy` remote iTOL helpers reference obsolete Python-2 web
clients/endpoints; retained source is not a supported browser service.
Likewise optional `formats.gff gb` (BCBio), STR (`pyfasta`/legacy `vcf`) and
read phasing (`vcf`) are not part of the declared local FASTA/BED/MCscan contract.

The optional mysql-connector LDAP/SASL plugin is omitted on both platforms for
parity: the pinned 8.4.0 arm64 wheel depends on obsolete libcrypto.so.10.
Standard mysql.connector/genomepy imports remain tested; corporate LDAP/SASL
authentication is outside the declared local workflows.

## Troubleshooting

- Module name is reported missing: put the `jcvi` executable first.
- Read-only index/cache error: choose writable work/scratch; never chmod a SIF.
- Reference rejected: verify identity, inventory and permissions; never rename
  a catalog unit to impersonate another assembly.
- Missing TeX/aligner/cloud credential: use the documented headless `--notex`
  path or a separately provisioned integration.

## Testing

Native engine-reported sizes before registry compression are 2,354,386,483 bytes (amd64) and 2,219,147,002 bytes (arm64). On amd64, `/opt/jcvi` accounts for about 1.2 GiB including the eager CPU SAM runtime. The optional 2,564,550,879-byte model is external. The native Linux SIF is converted from the tested amd64 image archive.

Smoke covers identity/dependency closure, module help, FASTA/BED, LAST → MCscan
→ PDF, five upstream clipping regressions, R/Graphviz/Wand, Samtools/EMBOSS/
BLAST+, immutable resource regressions and a tiny random-weight SAM CPU component
test including torchvision NMS. Full official ViT-H inference and actual model
binds are separate wrapper tests; tiny random tensors are not evidence of trained
model accuracy. Dockerfile uses only the light
identity/FASTA subset. Full exact commands require fresh offline containers,
read-only proxies and a same-OCI native Linux SIF; actual wrapper binds are
verified separately. These are packaging checks, not scientific qualification
on production datasets.

Synthetic SAM objects are not biological ground truth: upstream mask deduplication
retained the inner highlight regions in this fixture. Inspect masks/calibration
for real data; a successful run does not establish seed-outline or model accuracy.

## License and Citation

TAFFISH packaging and original helpers: Apache-2.0. Actual upstream 1.6.9 LICENSE
is BSD-2-Clause; upstream pyproject metadata says BSD-3-Clause. The actual text
is preserved in [the source-tree notice](docker/licenses/jcvi-BSD-2-Clause.txt)
alongside the unmodified upstream graphics test, and in the image; the metadata
discrepancy is recorded, not silently replaced. Dependencies
retain their own notices. Cite [Tang et al., JCVI, iMeta 2024](https://doi.org/10.1002/imt2.211);
the original checksum-pinned CITATION.cff is included. Its version field still says 1.6.8 at this upstream tag; package identity is determined by the pinned source and installed version.

SAM code and model are Apache-2.0, not subject to the separate SA-1B dataset
license. The pinned SAM LICENSE and README are preserved under `/opt/jcvi/share/`.
For SAM use, also cite [Kirillov et al., Segment Anything, ICCV 2023](https://arxiv.org/abs/2304.02643).

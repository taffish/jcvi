#!/bin/bash
set -euo pipefail
case "${TARGETARCH:?missing TARGETARCH}" in
  amd64)
    torch_file=torch-2.8.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl
    torch_sha=cb9a8ba8137ab24e36bf1742cb79a1294bd374db570f09fc15a5e1318160db4e
    vision_file=torchvision-0.23.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl
    vision_sha=ae459d4509d3b837b978dc6c66106601f916b6d2cda75c137e3f5f48324ce1da;;
  arm64)
    torch_file=torch-2.8.0+cpu-cp312-cp312-manylinux_2_28_aarch64.whl
    torch_sha=610f600c102386e581327d5efc18c0d6edecb9820b4140d26163354a99cd800d
    vision_file=torchvision-0.23.0-cp312-cp312-manylinux_2_28_aarch64.whl
    vision_sha=6dd7c4d329a0e03157803031bc856220c6155ef08c26d4f5bbac938acecf0948;;
  *) echo 'unsupported SAM CPU architecture' >&2; exit 2;;
esac
tmp=$(mktemp -d /tmp/jcvi-sam-build.XXXXXXXX)
trap 'rm -rf -- "$tmp"' EXIT
cd "$tmp"
# Resume large, checksum-pinned wheels after transient transport failures.
# HTTP/1.1 avoids intermediary HTTP/2 stream resets without weakening HTTPS.
curl --http1.1 --fail --location --retry 5 --retry-all-errors --continue-at - --connect-timeout 30 --max-time 900 "https://download-r2.pytorch.org/whl/cpu/${torch_file/+/%2B}" -o "$torch_file"
printf '%s  %s\n' "$torch_sha" "$torch_file" | sha256sum -c -
curl --http1.1 --fail --location --retry 5 --retry-all-errors --continue-at - --connect-timeout 30 --max-time 900 "https://download-r2.pytorch.org/whl/cpu/${vision_file/+/%2B}" -o "$vision_file"
printf '%s  %s\n' "$vision_sha" "$vision_file" | sha256sum -c -
sam_commit=dca509fe793f601edb92606367a655c15ac00fdf
sam_sha=b693c2358e9e1c63589a322b1baa6a6dc384df0013ff455d933d9a8e23549dab
curl --fail --location --retry 5 --retry-all-errors "https://codeload.github.com/facebookresearch/segment-anything/tar.gz/$sam_commit" -o sam.tar.gz
printf '%s  sam.tar.gz\n' "$sam_sha" | sha256sum -c -
python -m pip install --report /opt/jcvi/share/doc/jcvi/sam-install-report.json "$torch_file" "$vision_file" ./sam.tar.gz
tar -xzf sam.tar.gz
mkdir -p /opt/jcvi/share/licenses/segment-anything
cp "segment-anything-$sam_commit/LICENSE" /opt/jcvi/share/licenses/segment-anything/LICENSE
cp "segment-anything-$sam_commit/README.md" /opt/jcvi/share/doc/jcvi/SAM-README.md
printf 'sam_commit=%s\nsam_source_sha256=%s\ntorch_wheel=%s\ntorch_sha256=%s\ntorchvision_wheel=%s\ntorchvision_sha256=%s\nsam_device=cpu\n' \
  "$sam_commit" "$sam_sha" "$torch_file" "$torch_sha" "$vision_file" "$vision_sha" >> /opt/jcvi/share/doc/jcvi/source.txt
python -c 'import torch,torchvision,segment_anything; assert torch.__version__=="2.8.0+cpu"; assert torchvision.__version__.split("+")[0]=="0.23.0"; assert not torch.cuda.is_available(); print("SAM CPU imports PASS")'

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS builder

ARG JCVI_VERSION=1.6.8
ARG JCVI_COMMIT=c7d2de6f4b5e3269fb922dc1ee16191408cf381a
ARG JCVI_SDIST_URL=https://files.pythonhosted.org/packages/2c/e1/5c497c50c2e4f704529edec667f2e0f55592b6be779de50c329be1a7115e/jcvi-1.6.8.tar.gz
ARG JCVI_SDIST_SHA256=90abb6d2da918ba11eaaa08629fabb504ffa0830ad08769303cba4df82d861df
ARG JCVI_CITATION_URL=https://raw.githubusercontent.com/tanghaibao/jcvi/v1.6.8/CITATION.cff
ARG JCVI_CITATION_SHA256=a85d2fe0e9b523a72a5e5b7b86649ec8fa9310afd69ee22e2616e28d364767eb

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONNOUSERSITE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/opt/jcvi/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=5 update \
       && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
            build-essential \
            ca-certificates \
            curl \
            libcurl4-openssl-dev \
            zlib1g-dev \
            pkg-config; then \
        break; \
      fi; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb

WORKDIR /tmp/build
# Reproducibility boundary: fixed source checksums and pinned Python constraints
# identify the inputs, but PyPI availability/build dependencies and Debian APT
# indexes can drift. A base digest does not snapshot either package repository.
COPY docker/constraints.txt /opt/jcvi/constraints.txt
ENV PIP_CONSTRAINT=/opt/jcvi/constraints.txt

RUN --mount=type=cache,target=/root/.cache/pip set -eux; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL "${JCVI_SDIST_URL}" -o jcvi.tar.gz; \
    echo "${JCVI_SDIST_SHA256}  jcvi.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/jcvi-src; \
    tar -xzf jcvi.tar.gz -C /tmp/jcvi-src --strip-components=1; \
    python -m venv --copies /opt/jcvi/venv; \
    /opt/jcvi/venv/bin/python -m pip install --root-user-action=ignore --report /tmp/jcvi-install-report.json ./jcvi.tar.gz; \
    /opt/jcvi/venv/bin/python -c 'import importlib.metadata as md; assert md.version("jcvi") == "1.6.8"'; \
    mkdir -p \
        /opt/jcvi/share/doc/jcvi \
        /opt/jcvi/share/licenses/jcvi \
        /opt/jcvi/share/sources \
        /opt/jcvi/share/testdata; \
    cp /tmp/jcvi-install-report.json /opt/jcvi/share/doc/jcvi/install-report.json; \
    cp /tmp/jcvi-src/README.md /opt/jcvi/share/doc/jcvi/README.md; \
    cp /tmp/jcvi-src/pyproject.toml /opt/jcvi/share/doc/jcvi/pyproject.toml; \
    cp /tmp/jcvi-src/LICENSE /opt/jcvi/share/licenses/jcvi/LICENSE; \
    cp jcvi.tar.gz "/opt/jcvi/share/sources/jcvi-${JCVI_VERSION}.tar.gz"; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL "${JCVI_CITATION_URL}" -o /opt/jcvi/share/doc/jcvi/CITATION.cff; \
    echo "${JCVI_CITATION_SHA256}  /opt/jcvi/share/doc/jcvi/CITATION.cff" | sha256sum -c -; \
    { \
      printf 'upstream_name=JCVI\n'; \
      printf 'upstream_repo=https://github.com/tanghaibao/jcvi\n'; \
      printf 'upstream_tag=v%s\n' "${JCVI_VERSION}"; \
      printf 'upstream_commit=%s\n' "${JCVI_COMMIT}"; \
      printf 'runtime_source=pypi::jcvi==%s\n' "${JCVI_VERSION}"; \
      printf 'sdist_url=%s\n' "${JCVI_SDIST_URL}"; \
      printf 'sdist_sha256=%s\n' "${JCVI_SDIST_SHA256}"; \
      printf 'citation_url=%s\n' "${JCVI_CITATION_URL}"; \
      printf 'citation_sha256=%s\n' "${JCVI_CITATION_SHA256}"; \
    } > /opt/jcvi/share/doc/jcvi/source.txt

ARG TARGETARCH
COPY docker/install-sam.sh /opt/jcvi/share/doc/jcvi/install-sam.sh
RUN --mount=type=cache,target=/root/.cache/pip TARGETARCH="${TARGETARCH}" bash /opt/jcvi/share/doc/jcvi/install-sam.sh

RUN /opt/jcvi/venv/bin/python <<'PY' > /opt/jcvi/share/doc/jcvi/pip-freeze.txt
import importlib.metadata as md

rows = []
for dist in md.distributions():
    name = dist.metadata.get("Name")
    if name:
        rows.append((name.lower(), f"{name}=={dist.version}"))
for _, row in sorted(rows):
    print(row)
PY

COPY docker/jcvi-smoke.sh /opt/jcvi/share/testdata/jcvi-smoke.sh
COPY docker/smoke.py docker/resource-regression.py docker/test-resource-safety.py docker/test_chromosome.py docker/TESTDATA.md /opt/jcvi/share/testdata/
COPY docker/licenses/jcvi-BSD-2-Clause.txt /opt/jcvi/share/testdata/licenses/jcvi-BSD-2-Clause.txt

RUN set -eux; \
    cmp /opt/jcvi/share/testdata/licenses/jcvi-BSD-2-Clause.txt /opt/jcvi/share/licenses/jcvi/LICENSE; \
    chmod 0755 /opt/jcvi/share/testdata/jcvi-smoke.sh; \
    site_packages="$(/opt/jcvi/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"; \
    test -f "$site_packages/mysql/vendor/plugin/authentication_kerberos_client.so"; \
    rm -f \
        "$site_packages/mysql/vendor/plugin/authentication_ldap_sasl_client.so" \
        "$site_packages/mysql/vendor/private/libsasl2.so.3" \
        "$site_packages/mysql/vendor/private/libsasl2.so.3.0.0"; \
    rm -rf "$site_packages/mysql/vendor/private/sasl2"; \
    test ! -e "$site_packages/mysql/vendor/plugin/authentication_ldap_sasl_client.so"; \
    { \
      printf 'mysql_connector_ldap_sasl_plugin_bundled=false\n'; \
      printf 'mysql_connector_ldap_sasl_reason=removed on both platforms for parity because the upstream arm64 wheel requires obsolete libcrypto.so.10; not used by JCVI or genomepy core\n'; \
    } >> /opt/jcvi/share/doc/jcvi/source.txt; \
    rm -rf "$site_packages/goatools/test_data"; \
    find "$site_packages" -depth -type d \( -name test -o -name tests \) -exec rm -rf '{}' +; \
    find "$site_packages" -type f -name '*.a' -delete; \
    rm -rf "$site_packages/torch/include" "$site_packages/torch/share/cmake"; \
    rm -f "$site_packages/torch/bin/protoc" "$site_packages/torch/bin/protoc-3.13.0.0"; \
    printf 'sam_runtime=eager_cpu; torch C++ headers, CMake and protoc are excluded; torch_shm_manager retained\n' >> /opt/jcvi/share/doc/jcvi/source.txt; \
    rm -rf "$site_packages/pip" "$site_packages"/pip-*.dist-info; \
    rm -f /opt/jcvi/venv/bin/pip /opt/jcvi/venv/bin/pip3 /opt/jcvi/venv/bin/pip3.12; \
    find /opt/jcvi/venv -type d -name '__pycache__' -prune -exec rm -rf '{}' +; \
    find /opt/jcvi/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete; \
    rm -rf /root/.cache /tmp/build /tmp/jcvi-src

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONNOUSERSITE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg
ENV PATH=/opt/jcvi/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

RUN set -eux; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=5 update \
       && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
            bash \
            bedtools \
            bzip2 \
            ca-certificates \
            coreutils \
            curl \
            emboss \
            file \
            findutils \
            fonts-dejavu-core \
            gawk \
            ghostscript \
            git \
            graphviz \
            grep \
            gzip \
            imagemagick \
            last-align \
            ncbi-blast+ \
            libgomp1 \
            libmagic1 \
            procps \
            r-base-core \
            r-cran-ggplot2 \
            samtools \
            sed \
            tabix \
            tesseract-ocr \
            unzip \
            wget \
            xz-utils \
            zip; then \
        break; \
      fi; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*.deb

COPY --from=builder /opt/jcvi /opt/jcvi
COPY --chmod=0755 docker/jcvi-resources.py /usr/local/bin/jcvi-resources
COPY src/resource_validation.py /opt/jcvi/share/resource_validation.py
COPY docker/apply-ontology-guard.py /opt/jcvi/share/doc/jcvi/apply-ontology-guard.py

RUN set -eux; \
    python /opt/jcvi/share/doc/jcvi/apply-ontology-guard.py; \
    printf 'ontology_implicit_download=false\nontology_guard=apply-ontology-guard.py\n' >> /opt/jcvi/share/doc/jcvi/source.txt; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /opt/jcvi/share/doc/jcvi/system-packages.tsv; \
    # Check exit status and output independently; no drawing or full SAM here. \
    /opt/jcvi/share/testdata/jcvi-smoke.sh buildtime; \
    python -c 'import torch, torchvision, segment_anything; assert torch.__version__ == "2.8.0+cpu"; assert torchvision.__version__.split("+")[0] == "0.23.0"'; \
    # import torch preloads its own libraries (arm64 also uses torch.libs); static audit only. \
    find /opt/jcvi/venv -type f -name '*.so' -print0 | xargs -0 -r env LD_LIBRARY_PATH=/opt/jcvi/venv/lib/python3.12/site-packages/torch/lib:/opt/jcvi/venv/lib/python3.12/site-packages/torch.libs ldd > /tmp/jcvi-ldd.txt 2>&1 || true; \
    if grep -F 'not found' /tmp/jcvi-ldd.txt; then exit 1; fi; \
    rm -rf /root/.cache /tmp/jcvi-* /tmp/matplotlib /tmp/xdg-cache

WORKDIR /work

# JCVI/getpass needs a display username even for arbitrary container UIDs.
# This does not change the process UID, grant permissions or supply credentials.
ENV LOGNAME=taffish USER=taffish
ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=jcvi

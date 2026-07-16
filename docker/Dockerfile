FROM python:3.12-slim-bookworm AS builder

ARG JCVI_VERSION=1.6.6
ARG JCVI_COMMIT=846be3c9996873ea9b13cfbe2d6998d87739eac2
ARG JCVI_SDIST_URL=https://files.pythonhosted.org/packages/f2/a2/030e2c1993a8729f152e2ae7d0ecbfe381c9e8cade9c9f7620d1c7e4481b/jcvi-1.6.6.tar.gz
ARG JCVI_SDIST_SHA256=81f17efbb02b38209bff6f340345078b8c52adde544b6bb044d169e7c19e3e1f
ARG JCVI_CITATION_URL=https://raw.githubusercontent.com/tanghaibao/jcvi/v1.6.6/CITATION.cff
ARG JCVI_CITATION_SHA256=6b92d2e94bc39437c525ccae965d0e494140dab3653ce601e87f208b5bc3552b

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

RUN --mount=type=cache,target=/root/.cache/pip set -eux; \
    curl --retry 5 --retry-delay 2 --retry-all-errors -fsSL "${JCVI_SDIST_URL}" -o jcvi.tar.gz; \
    echo "${JCVI_SDIST_SHA256}  jcvi.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/jcvi-src; \
    tar -xzf jcvi.tar.gz -C /tmp/jcvi-src --strip-components=1; \
    python -m venv --copies /opt/jcvi/venv; \
    /opt/jcvi/venv/bin/python -m pip install --root-user-action=ignore ./jcvi.tar.gz; \
    /opt/jcvi/venv/bin/python -c 'import importlib.metadata as md; assert md.version("jcvi") == "1.6.6"'; \
    mkdir -p \
        /opt/jcvi/share/doc/jcvi \
        /opt/jcvi/share/licenses/jcvi \
        /opt/jcvi/share/sources \
        /opt/jcvi/share/testdata; \
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

RUN set -eux; \
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
    rm -rf "$site_packages/pip" "$site_packages"/pip-*.dist-info; \
    rm -f /opt/jcvi/venv/bin/pip /opt/jcvi/venv/bin/pip3 /opt/jcvi/venv/bin/pip3.12; \
    find /opt/jcvi/venv -type d -name '__pycache__' -prune -exec rm -rf '{}' +; \
    find /opt/jcvi/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete; \
    rm -rf /root/.cache /tmp/build /tmp/jcvi-src

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONNOUSERSITE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV XDG_CACHE_HOME=/tmp/xdg-cache
ENV PATH=/opt/jcvi/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin

RUN set -eux; \
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

RUN set -eux; \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /opt/jcvi/share/doc/jcvi/system-packages.tsv; \
    jcvi --version 2>&1 | grep -Fx 'jcvi 1.6.6' >/dev/null; \
    jcvi --help 2>&1 | grep -F 'Run jcvi modules' >/dev/null; \
    jcvi formats.fasta 2>&1 | grep -F 'Remove irregular chars in FASTA seqs' >/dev/null; \
    jcvi compara.synteny 2>&1 | grep -F 'Get anchor list using single-linkage algorithm' >/dev/null; \
    python -c 'import importlib.metadata as md; import genomepy; import mysql.connector; import pyBigWig; import pybedtools; import pysam; import jcvi; import jcvi.algorithms; import jcvi.annotation; import jcvi.apps; import jcvi.assembly; import jcvi.compara; import jcvi.formats; import jcvi.graphics; import jcvi.projects; import jcvi.utils; import jcvi.variation; import jcvi.assembly.chic; import jcvi.formats.cblast; assert md.version("jcvi") == "1.6.6"; print(jcvi.__version__)' | grep -Fx '1.6.6' >/dev/null; \
    /opt/jcvi/share/testdata/jcvi-smoke.sh buildtime; \
    find /opt/jcvi/venv -type f -name '*.so' -print0 | xargs -0 -r ldd > /tmp/jcvi-ldd.txt 2>&1 || true; \
    if grep -F 'not found' /tmp/jcvi-ldd.txt; then exit 1; fi; \
    rm -rf /root/.cache /tmp/jcvi-* /tmp/matplotlib /tmp/xdg-cache

WORKDIR /root

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=jcvi

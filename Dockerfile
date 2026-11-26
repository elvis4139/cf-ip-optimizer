# syntax=docker/dockerfile:1
FROM debian:bookworm-slim AS cfst-fetch
ARG CFST_VERSION=2.3.5
ARG CFST_ARCHIVE_SHA256=c4c8fc76b4e1bf2bdb5ced8b765956d82dda7bc4eb59df5c04053f0f7db98d90
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl tar && rm -rf /var/lib/apt/lists/*
RUN set -eux; archive="/tmp/cfst_linux_amd64.tar.gz"; url="https://github.com/XIU2/CloudflareSpeedTest/releases/download/v${CFST_VERSION}/cfst_linux_amd64.tar.gz"; curl --fail --show-error --location --retry 3 --output "$archive" "$url"; echo "${CFST_ARCHIVE_SHA256}  $archive" | sha256sum --check --strict; mkdir -p /tmp/cfst-extract; tar -xzf "$archive" -C /tmp/cfst-extract; test -x /tmp/cfst-extract/cfst

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --uid 1000 --gid 100 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app && install -d -o 1000 -g 100 /input /output /work /config
COPY --from=cfst-fetch /tmp/cfst-extract/cfst /usr/local/bin/cfst
COPY app.py /opt/cf-ip-optimizer/app.py
WORKDIR /opt/cf-ip-optimizer
USER 1000:100
ENTRYPOINT ["python","-m","app"]
CMD ["--help"]

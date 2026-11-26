# CF IP Optimizer

QNAP Docker project for measuring Cloudflare IPv4 candidates with **CFST v2.3.5** and, in later stages, validating and formatting EdgeTunnel subscription output.

Project documentation is kept separately in [docs/](docs/).

## Current implementation stage

**Stage 1 — Docker/CFST runtime foundation**

- Pinned official CFST release: v2.3.5.
- Downloads the prebuilt Linux amd64 archive; no Go compiler or NAS-side build toolchain is required.
- Verifies the release archive SHA-256 during image build.
- Targets the QNAP TS-453Dmini (Intel J4125 / linux/amd64).
- Runs as UID 1000 / GID 100, with a read-only root filesystem, dropped Linux capabilities, and no-new-privileges.
- Uses a dedicated Docker bridge network.
- Clears HTTP(S)/ALL proxy environment variables for the CFST process and sets NO_PROXY=*.
- Manual invocation only: no scheduler, subscription publication, or automatic overwrite is enabled.

The project-level production parameters are intentionally not filled in yet. Probe counts, timeouts, download settings, packet-loss threshold, retest policy, result grouping, and output counts remain pending confirmation in the project review document.

## Directory layout

```text
.
├── Dockerfile
├── compose.yaml
├── README.md
├── docs/                  # Requirements, decisions, test reports
└── data/
    ├── input/             # Put the IPv4 candidate list here (not committed)
    └── output/            # CFST output files (not committed)
```

## QNAP deployment path

The intended NAS project directory is:

```text
/share/Container/cf-ip-optimizer
```

Clone/copy this repository into that directory. No NAS changes are performed by GitHub commits.

## Build the image

From the project directory:

```bash
docker compose --profile manual build cfst
```

The build downloads the official CFST v2.3.5 Linux amd64 release and checks its SHA-256 before copying the binary into the runtime image.

## Verify CFST only

```bash
docker compose --profile manual run --rm cfst -h
```

This prints the CFST help and does not start a measurement.

## Input and output mounts

- Place the candidate IPv4 list at `data/input/ip.txt`.
- CFST sees it as `/input/ip.txt`.
- Output directory `data/output/` is mounted at `/output`.
- The input mount is read-only; output is writable.
- Do not commit candidate lists, measurement CSVs, or generated subscription files.

A measurement command must be assembled only after checking the actual v2.3.5 help output and confirming the project's pending parameters. Do not infer production flags from older repository code.

## Network behavior

The Compose service uses a dedicated bridge network and explicitly clears proxy environment variables inside the CFST process. This does not prove that the host/router has no transparent proxy or traffic interception. Validate the actual egress path during the authorized NAS test stage.

The project does not modify Mihomo, Docker daemon proxy configuration, AdGuard Home, router settings, or NAS network settings.

## Security and operational boundaries

- No privileged mode, host networking, published ports, or extra capabilities.
- Root filesystem is read-only; only the mounted output directory and tmpfs work areas are writable.
- The service is behind the `manual` Compose profile and is not started by a normal `docker compose up`.
- No cron/scheduler, notification, GitHub publishing, or EdgeTunnel overwrite is implemented in this stage.
- Never replace a previously valid subscription with an incomplete or failed run.

## Version provenance

CFST: [XIU2/CloudflareSpeedTest v2.3.5](https://github.com/XIU2/CloudflareSpeedTest/releases/tag/v2.3.5)

The archive SHA-256 is pinned in the Dockerfile and checked during build. See the project review under [docs/](docs/) for measurement findings and unresolved production decisions.

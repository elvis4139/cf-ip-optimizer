# Stage 2 — Python orchestration and two-pass selection

CFST v2.3.5 remains the only measurement engine. Current configurable defaults:

1. First pass measures the source IPv4 list. Python filters strictly to records with loss_ratio == 0.0 and valid download speed + latency, sorts by raw speed descending (then latency, loss, numeric IPv4), and keeps the fastest 80.
2. From those 80, the fastest 50 are written to a dedicated candidate file and passed to CFST for the second measurement.
3. Second-pass results are filtered again to exactly 0.0 loss. Missing rows or missing loss are not treated as zero. Final nodes are ranked by second-pass measurements; maximum possible output is 50.
4. Each run retains both CSVs, logs, candidate list, SHA-256 hashes, and normalized JSON.

The selection values are in [selection] in config.example.toml and can be changed without editing Python. The code currently enforces max_loss_ratio=0.0 as the approved policy.

## CFST arguments

Set exact v2.3.5 arguments in [stage1].args and [stage2].args after checking the binary help output and confirming the actual CSV/input-list contract. Use {input}, {csv}, and {run_dir}. Stage 2 {input} resolves to the generated fastest-50 candidate file. Empty args intentionally prevent accidental unconfigured execution.

## Subscription

Output format: IP:PORT#COUNTRY-xx.xxMB/s-yyms-City(optional). Country/city metadata is not inferred from CFST Colo. Publication remains disabled until trusted enrichment and output destination are configured.

No schedule, GitHub publishing, EdgeTunnel overwrite, notification, or NAS deployment is enabled.

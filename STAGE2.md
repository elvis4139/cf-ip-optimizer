# Stage 2 — Python orchestration and two-pass selection

CFST v2.3.5 remains the sole measurement engine. The agreed configurable defaults are:

- First pass: select the fastest 80 records meeting 0% packet loss and having speed/latency values.
- Second pass: rerun CFST against those first-pass candidates, then retain up to the fastest 50 records meeting 0% loss again.
- Loss is a CFST ratio: exactly 0.0 means 0%. Missing loss is not treated as zero.
- Both stage CSVs, logs, candidate list, hashes, and normalized JSON are retained per run.
- Second-pass output is constrained to IPs selected in pass one.
- Sort by raw speed descending, latency ascending, loss ascending, numeric IPv4; only format speed/latency at subscription rendering.
- Subscription format: IP:PORT#COUNTRY-xx.xxMB/s-yyms-City(optional). Country is never guessed from a CFST Colo/region token.
- Output remains disabled by default until trusted country/city enrichment and publication path are configured.

## Configuration

Edit config.example.toml and mount a runtime config as /config/config.toml. Set exact CFST v2.3.5 arguments in [stage1].args and [stage2].args after checking the binary's help. Arguments are passed without shell interpretation. Use {input}, {csv}, {run_dir}; stage 2 {input} points to the automatically generated first-pass candidate list. The input list format and flags must be confirmed with CFST help before enabling a live run.

No cron schedule, GitHub publishing, EdgeTunnel overwrite, notification, or NAS deployment is enabled by this stage.

# Selection policy — confirmed 2026-11-26

The first implementation uses configurable values, with the following approved defaults:

| Setting | Default | Meaning |
|---|---:|---|
| `first_top_n` | 80 | After first-pass measurement, retain the fastest 80 nodes that have complete speed/latency data and exactly 0% packet loss. |
| `second_top_n` | 50 | From those 80, take the fastest 50 and run the second CFST measurement against this candidate list. |
| `max_loss_ratio` | 0.0 | Strict gate in both passes. CFST's ratio value 0.0 means 0%; missing loss data is not accepted as zero. |

## Processing rules

1. First pass ranks using unrounded download speed descending, latency ascending, loss ascending, then numeric IPv4.
2. Only first-pass records with loss exactly 0.0 and non-missing speed/latency are eligible for the top 80.
3. The second pass measures only the first-pass top 50 (not all 80).
4. Second-pass records are checked against the exact candidate IP set. Unexpected IPs fail the run.
5. The final list consists only of second-pass records that again have exactly 0.0 loss and complete speed/latency. Its maximum size is 50; fewer may be returned if some candidates fail or are omitted.
6. Missing rows and missing loss values are unknown/unqualified, not inferred as 100% or 0% loss.
7. Both rounds' CSV, logs, candidate file and normalized JSON are retained per run.

The values can be changed in `config.toml` without editing Python. `max_loss_ratio` is currently enforced at 0.0 because zero loss is a confirmed admission condition.

## Not yet enabled

The exact CFST v2.3.5 command-line flags/input-file contract still needs to be filled into `[stage1].args` and `[stage2].args` after checking the installed binary's own help output. Output publication remains disabled until country/city enrichment is sourced from a trusted mapping and the final output destination is configured.

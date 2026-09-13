# RESIDUAL controller evaluation

Scripted simulation. No live LLM performance or billing claim.

| Mode | Passed | Remote calls | Remote request bytes | Reported input tokens | Usage complete |
| --- | ---: | ---: | ---: | ---: | --- |
| local_only | 2/8 | 0 | 0 | 0 | True |
| full_cloud | 8/8 | 24 | 1,044,858 | 0 | False |
| cascade | 8/8 | 6 | 262,188 | 0 | False |
| residual_fixed | 8/8 | 12 | 37,368 | 0 | False |
| residual | 8/8 | 12 | 37,368 | 0 | False |
| no_pull | 2/8 | 24 | 68,448 | 0 | False |

- Synthetic workloads; task success means declared checks passed.
- Scripted providers measure controller behavior, not LLM accuracy or real token savings.
- Request bytes include protocol framing; provider-reported tokens are recorded separately.
- Local hardware/energy and engineering costs are not measured.
- All modes share checks and limits; caches are disabled; no hidden gold is sent to models.

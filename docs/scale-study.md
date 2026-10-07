# Context size crossover

Scripted controller simulation; framed request bytes, not measured LLM tokens or cost.

| Background lines | Cascade bytes | Fixed-window bytes | Adaptive residual bytes | Reduction vs cascade | Passed, cascade / adaptive |
| ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 27,392 | 35,460 | 18,372 | 32.9% | 8/8; 8/8 |
| 32 | 53,502 | 37,336 | 27,962 | 47.7% | 8/8; 8/8 |
| 256 | 262,188 | 37,368 | 37,368 | 85.7% | 8/8; 8/8 |
| 1024 | 977,622 | 37,404 | 37,404 | 96.2% | 8/8; 8/8 |

The fixed-window policy loses to the cascade on tiny inputs. Adaptive residual sends the small relevant artifact in one capsule.
All other limits and checks are unchanged; each mode starts without a cache.

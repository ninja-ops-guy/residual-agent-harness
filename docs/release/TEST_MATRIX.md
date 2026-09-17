# Demo / Provider Test Matrix

| Test | Generated artifact | Published origin | Real external SDK | Auth | Inference | Physical device |
|---|---:|---:|---:|---:|---:|---:|
| publication/unit contracts | yes | no | no | no | no | no |
| browser_smoke desktop | yes/production variant | yes when post-deploy | no (fixture) | fixture | fixture failure path | no |
| browser_smoke narrow Chromium | yes/production variant | yes when post-deploy | no (fixture) | fixture | fixture failure path | no |
| provider_sdk_smoke | no | yes | **yes** | **no** | **no** | no |
| retained real-account provider acceptance | yes/public as recorded | yes | yes | yes | yes | device as recorded |
| physical iOS/WebKit acceptance | no | yes | as exercised | as exercised | as exercised | **yes** |

Agents must consult this matrix before using one test as evidence for another column.

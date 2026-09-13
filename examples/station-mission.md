# Night Shift recovery specification

This training mission uses scripted file proposals and real Git/check execution. No LLM is called.

```json
{
  "schema_version": 1,
  "name": "Night Shift / Station Recovery",
  "goal": "Restore the station health check, cap retry delays, and prepare the next shift handoff.",
  "tasks": [
    {
      "id": "OPS-101",
      "title": "Restore the health beacon",
      "instruction": "Implement status(services): ready for a nonempty mapping whose values are all truthy, otherwise degraded.",
      "files": [
        "station/health.py"
      ],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {
          "kind": "python_compile",
          "path": "station/health.py"
        },
        {
          "kind": "command",
          "argv": [
            "{python}",
            "-c",
            "from station.health import status; assert status({'db':True}) == 'ready'; assert status({}) == 'degraded'; assert status({'db':False}) == 'degraded'"
          ]
        }
      ]
    },
    {
      "id": "OPS-102",
      "title": "Stabilize the retry circuit",
      "instruction": "Implement delay(attempt) as exponential backoff starting at 1 second with a 60-second cap. Reject negative and non-integer attempts.",
      "files": [
        "station/retry.py"
      ],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {
          "kind": "python_compile",
          "path": "station/retry.py"
        },
        {
          "kind": "command",
          "argv": [
            "{python}",
            "-c",
            "from station.retry import delay; assert [delay(i) for i in (0,1,6,999)] == [1,2,60,60]\ntry: delay(-1)\nexcept ValueError: pass\nelse: raise AssertionError('negative attempt accepted')"
          ]
        }
      ]
    },
    {
      "id": "OPS-103",
      "title": "Write the shift handoff",
      "instruction": "Document the health states and retry behavior for the next shift.",
      "files": [
        "HANDOFF.md"
      ],
      "context": [
        "station/health.py",
        "station/retry.py"
      ],
      "depends_on": [
        "OPS-101",
        "OPS-102"
      ],
      "route": "local",
      "checks": [
        {
          "kind": "contains",
          "path": "HANDOFF.md",
          "text": "degraded"
        },
        {
          "kind": "contains",
          "path": "HANDOFF.md",
          "text": "60"
        }
      ]
    }
  ]
}
```

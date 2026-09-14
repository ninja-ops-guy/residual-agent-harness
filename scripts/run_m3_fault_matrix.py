from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.factory.reliability_m3 import aggregate_m3_faults


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = aggregate_m3_faults()
    (output / 'm3-fault-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    with (output / 'm3-fault-trials.jsonl').open('w') as stream:
        for trial in report['trials']:
            stream.write(json.dumps(trial, sort_keys=True) + '\n')
    print(json.dumps({'faults': report['faults'], 'contained': report['contained'], 'fcr': report['fcr']}, sort_keys=True))
    return 0 if report['fcr'] == 1.0 else 1


if __name__ == '__main__':
    raise SystemExit(main())

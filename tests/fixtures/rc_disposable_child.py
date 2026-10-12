"""Disposable stdlib child: stdout JSON only, no sockets, descendants or services."""
import argparse
import json
import os
from pathlib import Path
import time


def emit(value):
    print(json.dumps(value,sort_keys=True,separators=(',',':')),flush=True)


def main():
    parser = argparse.ArgumentParser()
    for key in ('role','mode','token','config'): parser.add_argument('--'+key,required=True)
    parser.add_argument('--lifetime',required=True,type=float)
    args = parser.parse_args()
    stop = time.monotonic()+args.lifetime
    emit({'event':'hello','role':args.role,'pid':os.getpid(),
          'token':'wrong-generation' if args.mode == 'wrong_identity' else args.token})
    if args.mode == 'exit': return
    sent = False
    while time.monotonic() < stop:
        if args.role == 'driver' and not sent and args.mode != 'never':
            try:
                data = json.loads(Path(args.config).read_bytes())
            except (FileNotFoundError,json.JSONDecodeError):
                data = None
            if data is not None:
                for task in data['tasks']:
                    if args.mode == 'never_second' and task['sequence'] == 1: continue
                    outcome = {k:task[k] for k in ('task_id','attempt_id','nonce','sequence')}
                    outcome.update(result_id='child-result-'+str(task['sequence']),status='succeeded',
                                   payload={'fixture_operation':'completed'},target=data['target'],driver=data['driver'])
                    if args.mode == 'stale': outcome['attempt_id'] = 'stale-attempt'
                    emit({'event':'outcome','value':outcome})
                sent = True
        time.sleep(0.01)


if __name__ == '__main__': main()

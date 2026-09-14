from __future__ import annotations
import json,time
from ..core import digest
def structured_event(kind,payload): return json.dumps({"timestamp_ns":time.time_ns(),"run_id":payload.get("run_id"),"goal_id":payload.get("goal_id"),"event_kind":kind,"payload_hash":digest(payload)},sort_keys=True,separators=(",",":"))

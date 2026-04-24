import json
import time


def handler(event, context):
    payload = {
        "message": "schedule_stub_tick",
        "time": int(time.time()),
        "event_preview": str(event)[:500],
    }
    print(json.dumps(payload))
    return {"ok": True}

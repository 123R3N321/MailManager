import json


def handler(event, context):
    for record in event.get("Records", []):
        print("ingest_message", json.dumps({"body": record.get("body"), "messageId": record.get("messageId")}))
    return {}


#CRUD API for the website target list.
# here each function handles one API Gateway route.

import json
import os
import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TARGETS_TABLE_NAME"])


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def create_target(event, context):
    """POST /targets — body: {"name": "...", "url": "..."}"""
    body = json.loads(event.get("body") or "{}")
    name = body.get("name")
    url = body.get("url")

    if not name or not url:
        return _response(400, {"error": "name and url are required"})

    table.put_item(Item={"name": name, "url": url})
    return _response(201, {"name": name, "url": url})


def list_targets(event, context):
    """GET /targets"""
    result = table.scan()
    return _response(200, result.get("Items", []))


def update_target(event, context):
    """PUT /targets/{name} — body: {"url": "..."}"""
    name = event["pathParameters"]["name"]
    body = json.loads(event.get("body") or "{}")
    url = body.get("url")

    if not url:
        return _response(400, {"error": "url is required"})

    table.update_item(
        Key={"name": name},
        UpdateExpression="SET #u = :url",
        ExpressionAttributeNames={"#u": "url"},
        ExpressionAttributeValues={":url": url},
    )
    return _response(200, {"name": name, "url": url})


def delete_target(event, context):
    """DELETE /targets/{name}"""
    name = event["pathParameters"]["name"]
    table.delete_item(Key={"name": name})
    return _response(204, {})
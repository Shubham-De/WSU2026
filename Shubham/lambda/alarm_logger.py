import json
import os

import boto3   


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, context):
    # SNS 
    for record in event["Records"]:


        # The alarm details from text into a dictionary
        message = json.loads(record["Sns"]["Message"])


        # Save one row 
        table.put_item(Item={
            "alarm_name": message["AlarmName"],
            "timestamp": message["StateChangeTime"],
            "new_state": message["NewStateValue"],     # 
            "old_state": message["OldStateValue"],
            "reason": message["NewStateReason"],
        })

    return "saved"


import json
import time
import boto3
import pytest

lambda_client = boto3.client("lambda", region_name="us-east-1")
cloudwatch_client = boto3.client("cloudwatch", region_name="us-east-1")


def _find_function_name(contains: str) -> str:

    #Find the real, deployed Lambda whose name contains the given text
    
    paginator = lambda_client.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page["Functions"]:
            if contains in fn["FunctionName"]:
                return fn["FunctionName"]
    pytest.skip(f"No deployed function found containing '{contains}' — is Beta deployed?")


def test_deployed_webmonitor_lambda_runs_successfully():

    #Invoke the real Beta WebMonitor lambda and check it returns valid results."""

    function_name = _find_function_name("Beta-ShubhamStack-WebMonitor")

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({}),
    )

    assert response["StatusCode"] == 200
    payload = json.loads(response["Payload"].read())
    assert isinstance(payload, list)
    assert len(payload) > 0
    assert "website" in payload[0]
    assert "is_up" in payload[0]


def test_webmonitor_metrics_appear_in_cloudwatch():

    
    #After running, availability metrics for WesternSydney should exist in Cloudwatch
    end = time.time()
    start = end - 3600  # look at the last hour

    response = cloudwatch_client.get_metric_statistics(
        Namespace="WebHealth",
        MetricName="Availability",
        Dimensions=[{"Name": "Website", "Value": "WesternSydney"}],
        StartTime=start,
        EndTime=end,
        Period=300,
        Statistics=["Average"],
    )

    assert len(response["Datapoints"]) > 0
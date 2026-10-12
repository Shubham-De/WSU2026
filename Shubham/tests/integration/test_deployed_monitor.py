

import json
import time
import boto3
import pytest
import urllib.request
import urllib.error

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




def _find_api_url():
    """Find the real, deployed TargetsApi endpoint URL."""
    apigw_client = boto3.client("apigateway", region_name="us-east-1")
    apis = apigw_client.get_rest_apis()["items"]
    for api in apis:
        if "WebHealth-Targets-Beta" in api["name"]:
            return f"https://{api['id']}.execute-api.us-east-1.amazonaws.com/prod/targets"
    pytest.skip("TargetsApi not found — is Beta deployed?")


def test_crud_api_create_and_read_target():
    """POST a target to the real API, then GET it back."""
    api_url = _find_api_url()

    # Create
    payload = json.dumps({"name": "IntegrationTestSite", "url": "https://example.com"}).encode()
    req = urllib.request.Request(api_url, data=payload, method="POST",
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 201

    # Read
    with urllib.request.urlopen(api_url, timeout=10) as resp:
        body = json.loads(resp.read())
        names = [item["name"] for item in body]
        assert "IntegrationTestSite" in names
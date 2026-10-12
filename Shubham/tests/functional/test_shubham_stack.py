
#Functional tests — check that ShubhamStack synthesizes the resources
#we expect, with the settings we expect, without deploying anything.

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

from shubham.shubham_stack import ShubhamStack


def _synthesized_template():

    #Build the stack and return its CloudFormation template for inspection.
    app = cdk.App()
    stack = ShubhamStack(app, "TestShubhamStack")
    return Template.from_stack(stack)


def test_seven_lambda_functions_are_created():

    #HelloLambda, WebMonitor, AlarmLogger, and 4 CRUD functions = 7 Lambda functions.
    template = _synthesized_template()
    template.resource_count_is("AWS::Lambda::Function", 7)


def test_lambdas_use_python312_runtime():
    template = _synthesized_template()
    template.has_resource_properties("AWS::Lambda::Function", {
        "Runtime": "python3.12",
    })


def test_monitor_schedule_runs_every_5_minutes():
    template = _synthesized_template()
    template.has_resource_properties("AWS::Events::Rule", {
        "ScheduleExpression": "rate(5 minutes)",
    })


def test_availability_alarm_has_correct_threshold():

    # availability alarms should trigger below 1 
    
    template = _synthesized_template()
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "Threshold": 1,
        "ComparisonOperator": "LessThanThreshold",

    })




def test_latency_alarm_has_correct_threshold():
    #Latency alarms should trigger above 3000ms.

    template = _synthesized_template()
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "Threshold": 3000,
        "ComparisonOperator": "GreaterThanThreshold",
    })


def test_dynamodb_table_has_correct_keys():
    template = _synthesized_template()
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": Match.array_with([
            {"AttributeName": "alarm_name", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ]),
    })


def test_sns_topic_is_created():
    template = _synthesized_template()
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_dashboard_is_created():
    template = _synthesized_template()
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)




def test_targets_table_has_name_as_partition_key():
    """The TargetsTable used by the CRUD API should be keyed by 'name'."""
    template = _synthesized_template()
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": Match.array_with([
            {"AttributeName": "name", "KeyType": "HASH"},
        ]),
    })


def test_targets_api_gateway_is_created():
    """The CRUD API Gateway should exist with GET, POST, PUT, DELETE methods."""
    template = _synthesized_template()
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
    template.resource_count_is("AWS::ApiGateway::Method", 4)
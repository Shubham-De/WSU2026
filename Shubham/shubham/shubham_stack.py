import json
import os

from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    Duration,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    RemovalPolicy,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
)
from constructs import Construct

alert_email = "bhattaraishubham817@gmail.com"

class ShubhamStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #read the wesite list
        json_path = os.path.join(os.path.dirname(__file__), "..", "lambda", "websites.json")
        with open(json_path) as f:
            websites = json.load(f)

        _lambda.Function(
            self, "HelloLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="hello.handler",
            code=_lambda.Code.from_asset("lambda"),
        )

        monitor = _lambda.Function(
            self, "WebMonitor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="monitor.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),            # 60 bcz more website more time
        )

        monitor.add_to_role_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
        ))

        #monitor every 5 mins
        rule = events.Rule(
            self, "MonitorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )
        rule.add_target(targets.LambdaFunction(monitor))

        topic = sns.Topic(self, "AlarmTopic", display_name="WebHealth Alarms")
        topic.add_subscription(subs.EmailSubscription(alert_email))

        table = dynamodb.Table(
            self, "AlarmLogTable",
            partition_key=dynamodb.Attribute(
                name="alarm_name", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # CRUD API for the website target list

        targets_table = dynamodb.Table(
            self, "TargetsTable",
            partition_key=dynamodb.Attribute(
                name="name", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        create_target_fn = _lambda.Function(
            self, "CreateTargetFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="targets_api.create_target",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TARGETS_TABLE_NAME": targets_table.table_name},
        )

        list_targets_fn = _lambda.Function(
            self, "ListTargetsFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="targets_api.list_targets",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TARGETS_TABLE_NAME": targets_table.table_name},
        )

        update_target_fn = _lambda.Function(
            self, "UpdateTargetFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="targets_api.update_target",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TARGETS_TABLE_NAME": targets_table.table_name},
        )

        delete_target_fn = _lambda.Function(
            self, "DeleteTargetFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="targets_api.delete_target",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TARGETS_TABLE_NAME": targets_table.table_name},
        )

        for fn in (create_target_fn, list_targets_fn, update_target_fn, delete_target_fn):
            targets_table.grant_read_write_data(fn)

        # API Gateway - wires HTTP routes to the 4 Lambdas above
        api = apigateway.RestApi(
            self, "TargetsApi",
            rest_api_name=f"WebHealth-Targets-{Stack.of(self).stack_name}",
        )

        targets_resource = api.root.add_resource("targets")
        targets_resource.add_method("GET", apigateway.LambdaIntegration(list_targets_fn))
        targets_resource.add_method("POST", apigateway.LambdaIntegration(create_target_fn))

        target_by_name = targets_resource.add_resource("{name}")
        target_by_name.add_method("PUT", apigateway.LambdaIntegration(update_target_fn))
        target_by_name.add_method("DELETE", apigateway.LambdaIntegration(delete_target_fn))

        # saving alarm messages into the table (logger lambda)
        logger = _lambda.Function(
            self, "AlarmLogger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="alarm_logger.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TABLE_NAME": table.table_name},
        )

        table.grant_write_data(logger)
        topic.add_subscription(subs.LambdaSubscription(logger))

        # points at one metric for one website
        def site_metric(metric_name, site_name):
            return cloudwatch.Metric(
                namespace="WebHealth",
                metric_name=metric_name,
                dimensions_map={"Website": site_name},
                statistic="Average",
                period=Duration.minutes(5),
            )

        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboardV2", dashboard_name=f"WebHealth-{Stack.of(self).stack_name}"
        )
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Availability (1 = up, 0 = down)",
                left=[site_metric("Availability", s["name"]) for s in websites],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Latency (ms)",
                left=[site_metric("Latency", s["name"]) for s in websites],
                width=12,
            ),
        )

        # Operational health alarms for the WebMonitor Lambda itself
        webmonitor_duration_alarm = cloudwatch.Alarm(
            self, "WebMonitorDurationAlarm",
            alarm_description="WebMonitor is taking too long to run",
            metric=monitor.metric_duration(statistic="Average", period=Duration.minutes(5)),
            threshold=50000,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        webmonitor_errors_alarm = cloudwatch.Alarm(
            self, "WebMonitorErrorsAlarm",
            alarm_description="WebMonitor is throwing errors",
            metric=monitor.metric_errors(statistic="Sum", period=Duration.minutes(5)),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        webmonitor_throttles_alarm = cloudwatch.Alarm(
            self, "WebMonitorThrottlesAlarm",
            alarm_description="WebMonitor is being throttled",
            metric=monitor.metric_throttles(statistic="Sum", period=Duration.minutes(5)),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        webmonitor_invocations_alarm = cloudwatch.Alarm(
            self, "WebMonitorNoInvocationsAlarm",
            alarm_description="WebMonitor has not run recently — schedule may be broken",
            metric=monitor.metric_invocations(statistic="Sum", period=Duration.minutes(10)),
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
        )

        for alarm in (webmonitor_duration_alarm, webmonitor_errors_alarm,
                      webmonitor_throttles_alarm, webmonitor_invocations_alarm):
            alarm.add_alarm_action(cw_actions.SnsAction(topic))
            alarm.add_ok_action(cw_actions.SnsAction(topic))



        # Two alarms for every website
        for site in websites:
            name = site["name"]

            down_alarm = cloudwatch.Alarm(
                self, f"{name}AvailabilityAlarm",
                alarm_description=f"{name} is down",
                metric=site_metric("Availability", name),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
                evaluation_periods=1,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )

            slow_alarm = cloudwatch.Alarm(
                self, f"{name}LatencyAlarm",
                alarm_description=f"{name} is slow",
                metric=site_metric("Latency", name),
                threshold=3000,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                evaluation_periods=2,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )

            for alarm in (down_alarm, slow_alarm):
                alarm.add_alarm_action(cw_actions.SnsAction(topic))
                alarm.add_ok_action(cw_actions.SnsAction(topic))
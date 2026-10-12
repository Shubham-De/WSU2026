import json
import os

from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
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
    aws_codedeploy as codedeploy,

)
from constructs import Construct

alert_email = "bhattaraishubham817@gmail.com"

class ShubhamStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "ShubhamQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )

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
            current_version_options=_lambda.VersionOptions(removal_policy=RemovalPolicy.RETAIN,),
        )

        monitor.add_to_role_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
        ))

        # A new immutable version is published every deploy
        monitor_version = monitor.current_version

        # The alias is the stable name EventBridge actually calls — it points
        # at whichever version is currently "live"

        monitor_alias = _lambda.Alias(
            self, "WebMonitorLiveAlias",
            alias_name="live",
            version=monitor_version,
        )


        

        #monitor every 5 mins
        rule = events.Rule(
            self, "MonitorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )

        #rule.add_target(targets.LambdaFunction(monitor))
        rule.add_target(targets.LambdaFunction(monitor_alias))

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
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,   # pay only for what you use
            removal_policy=RemovalPolicy.DESTROY,                # cdk destroy also deletes the table
        )



        # saving alarm messages into the table (logger lambda)
        logger = _lambda.Function(
            self, "AlarmLogger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="alarm_logger.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={"TABLE_NAME": table.table_name},   # tells the code which table to use
        )

        table.grant_write_data(logger)                       #  allow writing to the table
        topic.add_subscription(subs.LambdaSubscription(logger))     # the logger also listens to the group chat

        
        # points at one metric for one website
        def site_metric(metric_name, site_name):
            return cloudwatch.Metric(
                namespace="WebHealth",
                metric_name=metric_name,
                dimensions_map={"Website": site_name},
                statistic="Average",
                period=Duration.minutes(5),
            )

        # dashboard  two graphs side by side
        
        """
        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboard", dashboard_name="WebHealth"
        )  
        """

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


        # CodeDeploy deployment group  shifts traffic to the new version, watches these alarms, and rolls back automatically if any trip
        deployment_group = codedeploy.LambdaDeploymentGroup(
            self, "WebMonitorDeploymentGroup",
            alias=monitor_alias,
            deployment_config=codedeploy.LambdaDeploymentConfig.ALL_AT_ONCE,
            alarms=[
                webmonitor_duration_alarm,
                webmonitor_errors_alarm,
                webmonitor_throttles_alarm,
            ],
        )



        
        # Two alarms for every website
        for site in websites:
            name = site["name"]

            # Alarm 1 when the site is down
            down_alarm = cloudwatch.Alarm(
                self, f"{name}AvailabilityAlarm",
                alarm_description=f"{name} is down",
                metric=site_metric("Availability", name),
                threshold=1,
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
                evaluation_periods=1,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )

            # Alarm 2 when the site is slow over 3000 ms && twice in a row
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
                alarm.add_alarm_action(cw_actions.SnsAction(topic))   # alarm
                alarm.add_ok_action(cw_actions.SnsAction(topic))      #ok
            




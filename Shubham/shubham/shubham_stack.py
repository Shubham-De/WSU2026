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
        dashboard = cloudwatch.Dashboard(
            self, "WebHealthDashboard", dashboard_name="WebHealth"
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
            




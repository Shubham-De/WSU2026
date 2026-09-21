from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_lambda as _lambda,
    Duration
)
from constructs import Construct

class ShubhamStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "ShubhamQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )


        _lambda.Function(
            self, "HelloLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="hello.handler",
            code=_lambda.Code.from_asset("lambda"),
        )

        _lambda.Function(
            self, "WebMonitor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="monitor.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(15),            # allow up to 15s to run
        )

from aws_cdk import Stage
from constructs import Construct

from shubham.shubham_stack import ShubhamStack


class WebHealthStage(Stage):
    """
    One full deployable copy of the WebHealth app.
    The pipeline creates this twice: once for Beta, once for Prod.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ShubhamStack(self, "ShubhamStack")
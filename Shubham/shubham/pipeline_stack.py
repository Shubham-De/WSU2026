from aws_cdk import (
    Stack,
    SecretValue,
    pipelines,
)
from constructs import Construct

from shubham.app_stage import WebHealthStage


class PipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = pipelines.CodePipeline(
            self, "Pipeline",
            pipeline_name="WebHealthPipeline",
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.git_hub(
                    "Shubham-De/WSU2026",
                    "main",
                    authentication=SecretValue.secrets_manager("github-token"),
                ),
                commands=[
                    "cd Shubham",
                    "python -m pip install --upgrade pip",
                    "python -m pip install -r requirements.txt",
                    "npx cdk synth",
                ],
                primary_output_directory="Shubham/cdk.out",
            ),
        )

        #beta stage
        pipeline.add_stage(WebHealthStage(self, "Beta"))

        integration_test_step = pipelines.ShellStep(
            "IntegrationTests",
            commands=[
                "cd Shubham",
                "python -m pip install --upgrade pip",
                "python -m pip install -r requirements.txt",
                "python -m pip install -r requirements-dev.txt",
                "python -m pip install boto3",
                "python -m pytest tests/integration -v",
            ],
        )


        pipeline.add_stage(
            WebHealthStage(self, "Prod"),
            pre=[pipelines.ManualApprovalStep("PromoteToProd")],
        )
""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import aws_cdk as cdk

from aws_cdk import (
    aws_s3 as _s3,
    aws_iam as _iam,
    aws_sqs as _sqs,
    aws_ssm as _ssm
)
from constructs import Construct
from components.fine_tuner import FineTuner
from components.tuning_workflow import Orchestration
from components.fmops_pipeline import Pipeline

class TuningStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, *, pipeline_name: str, model_parameter: str, **kwargs) -> None:

        super().__init__(scope, id, **kwargs)

        # Load pipeline variables form toolchain context
        context = self.node.try_get_context("toolchain-context")

        # Define the S3 Bucket for tuning data, and store the name for use outside of the stack
        tuning_bucket = _s3.Bucket(
            self,
            "TuningDataBucket",
            bucket_name=f"{self.stack_name.lower()}-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True
        )
        cdk.CfnOutput(self, "TuningDataBucketName", value=tuning_bucket.bucket_name)

        # Create the Bedrock Service Role to manage the fine-tuning process, and access tuning data
        # in the `tuning_bucket` 
        bedrock_role = _iam.Role(
            self,
            "BedrockServiceRole",
            assumed_by=_iam.ServicePrincipal(
                service="bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": cdk.Aws.ACCOUNT_ID
                    },
                    "ArnEquals": {
                        "aws:SourceArn": f"arn:{cdk.Aws.PARTITION}:bedrock:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:model-customization-job/*"
                    }
                }
            ),
            inline_policies={
                "BedrockS3Policy": _iam.PolicyDocument(
                    statements=[
                        _iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket"
                            ],
                            effect=_iam.Effect.ALLOW,
                            resources=[
                                f"arn:{cdk.Aws.PARTITION}:s3:::{tuning_bucket.bucket_name}",
                                f"arn:{cdk.Aws.PARTITION}:s3:::{tuning_bucket.bucket_name}/*"
                            ],
                            conditions={
                                "StringEquals": {
                                    "aws:PrincipalAccount": cdk.Aws.ACCOUNT_ID
                                }
                            }
                        )
                    ]
                )
            }
        )

        # Create an SQS queue to integrate the fine-tuning workflow with the FMOps pipeline
        callback_queue = _sqs.Queue(
            self,
            "CallbackQueue",
            visibility_timeout=cdk.Duration.seconds(120)
        )

        # Add the fine-tuner component
        fine_tuner = FineTuner(self, "FineTuner")

        # Add the Bedrock service role to the fine-tuner handler environment
        fine_tuner.fine_tuner_handler.add_environment(key="BEDROCK_ROLE", value=bedrock_role.role_arn)

        # Add the fine-tuning orchestration component
        tuning_workflow = Orchestration(
            self,
            "TuningWorkflow",
            tuner=fine_tuner.fine_tuner_handler,
            sqs_queue=callback_queue
        )

        # Create the FMOps pipeline component
        fmops_pipeline = Pipeline(
            self,
            "FMOpsPipeline",
            data_bucket=tuning_bucket,
            sqs_queue=callback_queue
        )

        # Initialize the S3 notification function to start the FMOps pipeline with the context input parameters
        fmops_pipeline.pipeline_notification.add_environment(key="BASE_MODEL", value="amazon.titan-text-express-v1")
        fmops_pipeline.pipeline_notification.add_environment(key="EPOCHS", value=context.get("tuning-epoch-count"))
        fmops_pipeline.pipeline_notification.add_environment(key="BATCHES", value=context.get("tuning-batch-size"))
        fmops_pipeline.pipeline_notification.add_environment(key="LEARNING_RATE", value=context.get("tuning-learning-rate"))
        fmops_pipeline.pipeline_notification.add_environment(key="WARMUP_STEPS", value=context.get("tuning-warmup-steps"))

        # Initialize the model approval event handler to start the CI/CD process for a fine-tuned model, with permissions
        # to update the model SSM parameter, and start a CodePipeline execution
        fmops_pipeline.approval_function.add_environment(key="PIPELINE_NAME", value=pipeline_name)
        fmops_pipeline.approval_function.add_environment(key="MODEL_PARAMETER", value=model_parameter)
        fmops_pipeline.approval_function.add_to_role_policy(
            statement=_iam.PolicyStatement(
                sid="ModelParameterAccess",
                actions=["ssm:PutParameter"],
                effect=_iam.Effect.ALLOW,
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:ssm:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:parameter/{model_parameter}"
                ]
            )
        )
        fmops_pipeline.approval_function.add_to_role_policy(
            statement=_iam.PolicyStatement(
                sid="CodePipelineAccess",
                actions=["codepipeline:StartPipelineExecution"],
                effect=_iam.Effect.ALLOW,
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:codepipeline:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:{pipeline_name}"
                ]
            )
        )

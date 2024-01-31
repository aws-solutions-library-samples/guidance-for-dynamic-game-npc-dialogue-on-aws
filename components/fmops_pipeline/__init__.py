""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import pathlib
import boto3
import constants
import aws_cdk as cdk

from aws_cdk import (
    aws_sagemaker as _sagemaker,
    aws_iam as _iam,
    aws_s3 as _s3,
    aws_lambda as _lambda,
    aws_s3_notifications as _notification,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_sqs as _sqs
)
from components.fmops_pipeline.pipeline import get_sagemaker_pipeline
from botocore.exceptions import ClientError
from constructs import Construct

class Pipeline(Construct):

    def __init__(self, scope: Construct, id: str, data_bucket: _s3.Bucket, sqs_queue: _sqs.Queue) -> None:
        super().__init__(scope, id)

        # Register the SageMaker Execution Role for the Domain as a CDK object
        sagemaker_role = _iam.Role.from_role_arn(
            self,
            "ExecutionRole",
            role_arn=self._get_execution_role(domain_id=constants.SAGEMAKER_DOMAIN_ID)
        )

        # Add Bedrock permissions to the Execution role
        sagemaker_role.attach_inline_policy(
            policy=_iam.Policy(
                self,
                "BedrockAccessPolicy",
                document=_iam.PolicyDocument(
                    assign_sids=True,
                    statements=[
                        _iam.PolicyStatement(
                            actions=["bedrock:*"],
                            effect=_iam.Effect.ALLOW,
                            resources=["*"]
                        )
                    ]
                )
            )
        )

        # Give Data Bucket access to the execution role
        data_bucket.grant_read_write(sagemaker_role)

        # Give SQS access to the execution role
        sqs_queue.grant_send_messages(sagemaker_role)

        # Get the SageMaker Pipeline definition
        sagemaker_pipeline = get_sagemaker_pipeline(
            role=sagemaker_role.role_arn,
            model_package_group_name=f"{constants.WORKLOAD_NAME}-PackageGroup",
            queue_url=sqs_queue.queue_url
        )

        # Define the SageMaker Pipeline L1 construct
        fmops_workflow = _sagemaker.CfnPipeline(
            self,
            "FMOpsWorkflow",
            pipeline_name=f"{constants.WORKLOAD_NAME}-FMOpsPipeline",
            role_arn=sagemaker_role.role_arn,
            pipeline_description=f"SageMaker FMOps Pipeline for {constants.WORKLOAD_NAME}",
            pipeline_definition={
                "PipelineDefinitionBody": sagemaker_pipeline.definition()
            }
        )
        cdk.CfnOutput(self, "PipelineNameOutput", value=fmops_workflow.ref)

        # Define the notification handler to start an execution of the SageMaker Pipeline
        self.pipeline_notification = _lambda.Function(
            self,
            "TuningNotification",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(
                path=str(pathlib.Path(__file__).parent.joinpath("notification").resolve()),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(60),
            environment={
                "PIPELINE_NAME": fmops_workflow.ref
            }
        )
        self.pipeline_notification.add_to_role_policy(
            _iam.PolicyStatement(
                sid="PipelineExecutionPolicy",
                actions=["sagemaker:StartPipelineExecution"],
                effect=_iam.Effect.ALLOW,
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:pipeline/{fmops_workflow.ref}"
                ]
            )
        )

        # Bind the S3 notification to the Bucket to start the FMOps process
        notification = _notification.LambdaDestination(self.pipeline_notification)
        notification.bind(self, bucket=data_bucket)
        data_bucket.add_object_created_notification(
            notification,
            _s3.NotificationKeyFilter(
                suffix="raw-data/data.jsonl" # NOTE: Hard-coded to avoid multiple notifications when data is preprocessed
            )
        )

        # Create the Model Approval Function
        self.approval_function = _lambda.Function(
            self,
            "ApprovalFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(
                path=str(pathlib.Path(__file__).parent.joinpath("event").resolve()),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(60)
        )
        self.approval_function.add_to_role_policy(
            statement=_iam.PolicyStatement(
                sid="BedrockAccess",
                actions=[
                    "bedrock:ListCustomModels",
                    "bedrock:ListProvisionedModelThroughputs"
                ],
                effect=_iam.Effect.ALLOW,
                resources=["*"]
            )
        )

        # Create the EventBridge rule to start the CI/CD/CT Pipeline execution upon model approval
        _events.Rule(
            self,
            "ModelRegistryRule",
            rule_name=f"{constants.WORKLOAD_NAME.lower()}-ModelPackage-Change",
            description="Rule to trigger a deployment when SageMaker Model registry is updated with a new model package.",
            event_pattern=_events.EventPattern(
                detail_type=["SageMaker Model Package State Change"],
                source=["aws.sagemaker"],
                detail={
                    "ModelPackageGroupName": [
                        f"{constants.WORKLOAD_NAME}-PackageGroup"
                    ],
                    "ModelApprovalStatus": [
                        "Approved"
                    ]
                }
            ),
            targets=[
                _targets.LambdaFunction(self.approval_function)
            ]
        )


    @staticmethod
    def _get_execution_role(domain_id: str) -> str:
        client = boto3.client("sagemaker")
        try:
            domain = client.describe_domain(
                DomainId=domain_id
            )
            return domain["DefaultUserSettings"]["ExecutionRole"]
        
        except ClientError as e:
            message = e.response["Error"]["Message"]
            raise Exception(message)

""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import aws_cdk as cdk

from aws_cdk import (
    aws_iam as _iam,
    aws_sqs as _sqs,
    aws_lambda as _lambda,
    aws_stepfunctions_tasks as _tasks,
    aws_stepfunctions as _sfn,
    aws_lambda_event_sources as _event_source
)
from constructs import Construct

class Orchestration(Construct):

    def __init__(self, scope: Construct, id: str, tuner: _lambda.Function, sqs_queue: _sqs.Queue) -> None:
        super().__init__(scope, id)

        # Create the IAM role for the fine-tuning state machine
        orchestration_role = _iam.Role(
            self,
            "WorkflowRole",
            assumed_by=_iam.CompositePrincipal(
                _iam.ServicePrincipal("states.amazonaws.com"),
                _iam.ServicePrincipal("lambda.amazonaws.com")
            ),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AWSStepFunctionsFullAccess")
            ]
        )

        # Create a Step function state machine to handle the fine-tuning workflow and then
        # work backwards. The failure step sends a failure message back to the SageMaker
        # FMOps Pipeline
        failure_step = _tasks.LambdaInvoke(
            self,
            "Tuning Failed",
            lambda_function=tuner,
            payload=_sfn.TaskInput.from_json_path_at("$.Payload")
        )

        # Create the success step. This task tests the custom tuned model, and sends 
        # a success message back to the SageMaker FMOps Pipeline
        success_step = _tasks.LambdaInvoke(
            self,
            "Tuning Complete",
            lambda_function=tuner,
            payload=_sfn.TaskInput.from_json_path_at("$.Payload")
        )

        # Create status handling branch, based on the output on the output
        # of the `status_step`
        status_choice = _sfn.Choice(self, "Review Status")
        status_choice.when(
            condition=_sfn.Condition.string_equals(
                variable="$.Payload.status",
                value="Completed"
            ),
            next=success_step
        )
        status_choice.when(
            condition=_sfn.Condition.string_equals(
                variable="$.Payload.status",
                value="Failed"
            ),
            next=failure_step
        )

        # Create a status check task. This tasks checks the status on the fine-tuning
        # process, and returns the current status
        status_step = _tasks.LambdaInvoke(
            self,
            "Get Tuning Status",
            lambda_function=tuner,
            payload=_sfn.TaskInput.from_json_path_at("$.Payload")
        )
        status_step.next(status_choice)

        # Add a `Wait` step before checking the status
        wait_step = _sfn.Wait(self, "Wait", time=_sfn.WaitTime.duration(cdk.Duration.minutes(10)))
        wait_step.next(status_step)
        status_choice.otherwise(wait_step)

        # Create the `Start` task. This task starts the fine-tuning model customization job.
        start_step = _tasks.LambdaInvoke(
            self,
            "Start Fine-tuning",
            lambda_function=tuner
        )

        # Create the state machine to orchestrate the fine-tuning process
        tuning_workflow = _sfn.StateMachine(
            self,
            "TuningWorkflow",
            definition_body=_sfn.DefinitionBody.from_chainable(start_step.next(wait_step)),
            role=orchestration_role
        )

        # Create the IAM Role for the Lambda function that starts the fine-tuning workflow
        callback_role = _iam.Role(
            self,
            "CallbackRole",
            assumed_by=_iam.CompositePrincipal(
                _iam.ServicePrincipal("sagemaker.amazonaws.com"),
                _iam.ServicePrincipal("lambda.amazonaws.com"),
                _iam.ServicePrincipal("states.amazonaws.com")
            ),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess")
            ],
            inline_policies={
                "StepFunctionsAccess": _iam.PolicyDocument(
                    statements=[
                        _iam.PolicyStatement(
                            actions=[
                                "states:StartExecution"
                            ],
                            effect=_iam.Effect.ALLOW,
                            resources=[
                                f"arn:{cdk.Aws.PARTITION}:states:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:stateMachine:{tuning_workflow.state_machine_name}"
                            ]
                        )
                    ]
                ),
                "SageMakerAccess": _iam.PolicyDocument(
                    statements=[
                        _iam.PolicyStatement(
                            actions=[
                                "sagemaker:SendPipelineExecutionStepFailure"
                            ],
                            effect=_iam.Effect.ALLOW,
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Create the Lambda function to start the fine-tuning workflow
        callback_handler = _lambda.Function(
            self,
            "CallbackHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(
                path="components/tuning_workflow/runtime",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="index.lambda_handler",
            role=callback_role,
            timeout=cdk.Duration.seconds(60),
            environment={
                "STATE_MACHINE_ARN": tuning_workflow.state_machine_arn
            }
        )

        # Create an event mapping between the `callback_handler` and `callback_queue`
        callback_handler.add_event_source(_event_source.SqsEventSource(sqs_queue))

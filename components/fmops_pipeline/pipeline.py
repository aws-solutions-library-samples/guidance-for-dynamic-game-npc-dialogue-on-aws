""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import boto3
import json
import constants

from sagemaker import Model
from sagemaker.workflow.callback_step import CallbackStep, CallbackOutput, CallbackOutputTypeEnum
from sagemaker.xgboost import XGBoostProcessor
from sagemaker.processing import ProcessingOutput, ProcessingInput
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterString
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.functions import Join
from sagemaker.workflow.steps import ProcessingStep
from sagemaker.workflow.execution_variables import ExecutionVariables
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.workflow.model_step import ModelStep

def get_pipeline_session(region: str) -> None:
    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")
    return PipelineSession(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client
    )


def get_sagemaker_pipeline(role: str, model_package_group_name: str, queue_url: str) -> None:
    # SageMaker session variables
    if role is None:
        raise Exception("Execution Role is Required")
    pipeline_session = get_pipeline_session(region=constants.REGION)

    # Pipeline variables
    base_model = ParameterString(name="BaseModel", default_value="amazon.titan-text-express-v1")
    data_bucket = ParameterString(name="DataBucket", default_value=pipeline_session.default_bucket())
    data_prefix = ParameterString(name="DataPrefix", default_value="/data.jsonl")
    epochs = ParameterString(name="Epochs", default_value="1")
    batch_size = ParameterString(name="BatchSize", default_value="1")
    learning_rate = ParameterString(name="LearningRate", default_value="0.005")
    warmup_steps = ParameterString(name="WarmupSteps", default_value="0")

    # Data preprocessing step
    preprocessor = XGBoostProcessor(
        role=role,
        framework_version="1.7-1",
        instance_count=1,
        instance_type="ml.m5.xlarge",
        sagemaker_session=pipeline_session,
        base_job_name=f"{constants.WORKLOAD_NAME}/preprocessing",
    )
    preprocessing_step = ProcessingStep(
        name="DataPreprocessing",
        step_args=preprocessor.run(
            inputs=[
                ProcessingInput(
                    input_name="data",
                    source=Join(
                        on="/",
                        values=[
                            "s3:/",
                            data_bucket,
                            data_prefix
                        ]
                    ),
                    destination="/opt/ml/processing/input"
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="train",
                    source="/opt/ml/processing/output/train",
                    destination=Join(
                        on="/",
                        values=[
                            "s3:/",
                            data_bucket,
                            ExecutionVariables.PIPELINE_EXECUTION_ID,
                            "data/train"
                        ]
                    )
                ),
                ProcessingOutput(
                    output_name="validation",
                    source="/opt/ml/processing/output/validation",
                    destination=Join(
                        on="/",
                        values=[
                            "s3:/",
                            data_bucket,
                            ExecutionVariables.PIPELINE_EXECUTION_ID,
                            "data/validation"
                        ]
                    )
                ),
                ProcessingOutput(
                    output_name="test",
                    source="/opt/ml/processing/output/test",
                    destination=Join(
                        on="/",
                        values=[
                            "s3:/",
                            data_bucket,
                            ExecutionVariables.PIPELINE_EXECUTION_ID,
                            "data/test"
                        ]
                    )
                )
            ],
            code="preprocessing.py",
            source_dir=os.path.join(os.path.dirname(__file__), "scripts")
        )
    )

    # Bedrock custom model fine-tuning, as a callback step
    callback_step = CallbackStep(
        name="FineTuning",
        sqs_queue_url=queue_url,
        inputs={
            "JOB_PREFIX": constants.WORKLOAD_NAME,
            "DATA_BUCKET": data_bucket,
            "EXECUTION_ID": ExecutionVariables.PIPELINE_EXECUTION_ID,
            "BASE_MODEL": base_model,
            "TRAIN_DATA": preprocessing_step.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri,
            "VALIDATION_DATA": preprocessing_step.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri,
            "EPOCHS": epochs,
            "BATCH_SIZE": batch_size,
            "LEARNING_RATE": learning_rate,
            "WARMUP_STEPS": warmup_steps
        },
        outputs=[
            CallbackOutput(output_name="OUTPUT_MODEL_NAME", output_type=CallbackOutputTypeEnum.String),
            CallbackOutput(output_name="OUTPUT_MODEL_ARN", output_type=CallbackOutputTypeEnum.String),
            CallbackOutput(output_name="JOB_NAME", output_type=CallbackOutputTypeEnum.String),
            CallbackOutput(output_name="JOB_ARN", output_type=CallbackOutputTypeEnum.String),
            CallbackOutput(output_name="BASE_MODEL_ARN", output_type=CallbackOutputTypeEnum.String),
            CallbackOutput(output_name="OUTPUT_DATA", output_type=CallbackOutputTypeEnum.String)
        ]
    )

    # Fine-tuned model evaluation
    evaluation_processor = XGBoostProcessor(
        framework_version="1.7-1",
        role=role,
        instance_count=1,
        instance_type="ml.m5.xlarge",
        base_job_name=f"{constants.WORKLOAD_NAME}/evaluation",
        sagemaker_session=pipeline_session,
        env={
            "JOB_ARN": callback_step.properties.Outputs["JOB_ARN"]
        }
    )
    evaluation_step = ProcessingStep(
        name="ModelEvaluation",
        step_args=evaluation_processor.run(
            inputs=[
                ProcessingInput(
                    source=callback_step.properties.Outputs["OUTPUT_DATA"],
                    destination="/opt/ml/processing/input/data/"
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="evaluation",
                    source="/opt/ml/processing/output/data",
                    destination=Join(
                        on="/",
                        values=[
                            "s3:/",
                            data_bucket,
                            ExecutionVariables.PIPELINE_EXECUTION_ID,
                            "evaluation"
                        ]
                    )
                )
            ],
            code="evaluation.py",
            source_dir=os.path.join(os.path.dirname(__file__), "scripts")
        )
    )

    # Create a placeholder model, representing the fine-tuned custom model
    model = Model(
        name="BedrockCustomModel",
        role=role,
        image_uri=evaluation_processor.image_uri,
        sagemaker_session=pipeline_session
    )

    # Register the placeholder model in the SageMaker Model registry
    register_model_step = ModelStep(
        name="Register",
        step_args=model.register(
            content_types=["text/csv"],
            response_types=["text/csv"],
            approval_status="PendingManualApproval",
            model_metrics=ModelMetrics(
                model_statistics=MetricsSource(
                    s3_uri=Join(
                        on="/",
                        values=[
                            evaluation_step.arguments["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"],
                            "evaluation_report.json"
                        ]
                    ),
                    content_type="application/json"
                )
            ),
            model_package_group_name=model_package_group_name,
            customer_metadata_properties={
                "ModelName": callback_step.properties.Outputs["OUTPUT_MODEL_NAME"],
                "ModelArn": callback_step.properties.Outputs["OUTPUT_MODEL_ARN"],
                "JobName": callback_step.properties.Outputs["JOB_NAME"],
                "JobArn": callback_step.properties.Outputs["JOB_ARN"],
                "BaseModelArn": callback_step.properties.Outputs["BASE_MODEL_ARN"],
                "OutputData": callback_step.properties.Outputs["OUTPUT_DATA"]
            }
        ),
        depends_on=[evaluation_step]
    )

    # Define the pipeline
    pipeline = Pipeline(
        name=f"{constants.WORKLOAD_NAME}-FMOpsPipeline",
        parameters=[
            base_model,
            data_bucket,
            data_prefix,
            epochs,
            batch_size,
            learning_rate,
            warmup_steps
        ],
        steps=[
            preprocessing_step,
            callback_step,
            evaluation_step,
            register_model_step
        ],
        sagemaker_session=pipeline_session
    )

    # Local Debug
    # with open("definition.json", "w") as f:
    #     json.dump(json.loads(pipeline.definition()), f, indent=4)

    return pipeline
    

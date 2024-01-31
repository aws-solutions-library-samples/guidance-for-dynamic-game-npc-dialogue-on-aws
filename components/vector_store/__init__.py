""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import json
import pathlib
import constants
import aws_cdk as cdk

from aws_cdk import (
    aws_opensearchservice as _opensearch,
    aws_iam as _iam,
    aws_ec2 as _ec2,
    aws_secretsmanager as _secrets,
    aws_s3 as _s3,
    aws_s3_deployment as _deployment,
    aws_lambda as _lambda,
    aws_ecr_assets as _ecr_asset,
    aws_s3_notifications as _notification
)
from constructs import Construct

class VectorStore(Construct):

    def __init__(self, scope: Construct, id: str, data_bucket: _s3.Bucket) -> None:
        super().__init__(scope, id)

        # Load pipeline variables form toolchain context
        context = self.node.try_get_context("toolchain-context")

        # Create an OpenSearch Master User Secret
        self.opensearch_secret = _secrets.Secret(
            self,
            "OpenSearchMasterUserSecret",
            generate_secret_string=_secrets.SecretStringGenerator(
                secret_string_template=json.dumps({"USERNAME": "admin"}),
                generate_string_key="PASSWORD",
                password_length=8
            )
        )

        # Create the OpenSearch Domain
        self.search_domain = _opensearch.Domain(
            self,
            "OpenSearchDomain",
            version=_opensearch.EngineVersion.OPENSEARCH_2_9,
            ebs=_opensearch.EbsOptions(
                volume_size=20,
                volume_type=_ec2.EbsDeviceVolumeType.GP3
            ),
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest=_opensearch.EncryptionAtRestOptions(
                enabled=True
            ),
            logging=_opensearch.LoggingOptions(
                app_log_enabled=True,
                slow_index_log_enabled=True,
                slow_search_log_enabled=True
            ),
            fine_grained_access_control=_opensearch.AdvancedSecurityOptions(
                master_user_name=self.opensearch_secret.secret_value_from_json("USERNAME").unsafe_unwrap(),
                master_user_password=self.opensearch_secret.secret_value_from_json("PASSWORD")
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            capacity=_opensearch.CapacityConfig(
                data_node_instance_type="r6g.large.search",
                data_nodes=3,
                master_node_instance_type="r6g.large.search",
                master_nodes=3
            ),
            zone_awareness=_opensearch.ZoneAwarenessConfig(
                availability_zone_count=3
            )
        )
        self.search_domain.add_access_policies(
            _iam.PolicyStatement(
                principals=[
                    _iam.AnyPrincipal()
                ],
                actions=[
                    "es:*"
                ],
                effect=_iam.Effect.ALLOW,
                resources=[
                    self.search_domain.domain_arn,
                    f"{self.search_domain.domain_arn}/*"
                ]
            )
        )

        # Create the database hydration SageMaker Processing Job docker image
        processing_image = _ecr_asset.DockerImageAsset(
            self,
            "ProcessingImage",
            directory=str(pathlib.Path(__file__).parent.joinpath("image").resolve()),
        )
        
        # Create the SageMaker role for the database hydration processing job,
        # with access to the image and S3
        processing_role = _iam.Role(
            self,
            "ProcessingJobRole",
            assumed_by=_iam.CompositePrincipal(
                _iam.ServicePrincipal("sagemaker.amazonaws.com")
            ),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
            ],
            inline_policies={
                "BedrockAccess": _iam.PolicyDocument(
                    statements=[
                        _iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel"
                            ],
                            effect=_iam.Effect.ALLOW,
                            resources=[
                                f"arn:aws:bedrock:{cdk.Aws.REGION}::foundation-model/{context.get('bedrock-text-model-id')}",
                                f"arn:aws:bedrock:{cdk.Aws.REGION}::foundation-model/{context.get('bedrock-embedding-model-id')}"
                            ]
                        )
                    ]
                )
            }
        )
        data_bucket.grant_read_write(processing_role)
        processing_image.repository.grant_pull(processing_role)
        self.opensearch_secret.grant_read(processing_role)

        # Create a Lambda function to start the SageMaker Processing Job from S3 notification
        self.notification_function = _lambda.Function(
            self,
            "NotificationFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(
                path="components/vector_store/runtime",
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
                "JOB_NAME": f"{constants.WORKLOAD_NAME}-RAG-Ingest",
                "IMAGE_URI": processing_image.image_uri,
                "ROLE": processing_role.role_arn,
                "SCRIPT_URI": f"s3://{data_bucket.bucket_name}/scripts/data_ingest.py",
                "TEXT_MODEL_ID": context.get("bedrock-text-model-id"),
                "EMBEDDING_MODEL_ID": context.get("bedrock-embedding-model-id"),
                "OPENSEARCH_ENDPOINT": self.search_domain.domain_endpoint,
                "OPENSEARCH_SECRET": self.opensearch_secret.secret_name,
                "OPENSEARCH_INDEX": context.get("embedding-index-name")
            }
        )
        self.notification_function.add_to_role_policy(
            _iam.PolicyStatement(
                sid="StartJobPermission",
                actions=[
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:AddTags",
                    "iam:PassRole"
                ],
                effect=_iam.Effect.ALLOW,
                resources=["*"]
            )
        )

        # Deploy data ingest script to S3
        _deployment.BucketDeployment(
            self,
            "ScriptsDeployment",
            sources=[
                _deployment.Source.asset(
                    path=str(pathlib.Path(__file__).parent.joinpath("scripts").resolve())
                )
            ],
            destination_bucket=data_bucket,
            destination_key_prefix="scripts",
            retain_on_delete=False
        )

        # Add the S3 trigger to start the processing job
        notification = _notification.LambdaDestination(self.notification_function)
        notification.bind(self, bucket=data_bucket)
        data_bucket.add_object_created_notification(
            notification,
            _s3.NotificationKeyFilter(
                suffix=".txt"
            )
        )

    @property
    def endpoint_name(self) -> str:
        return self.search_domain.domain_endpoint

# Guidance for Dynamic Non-Player Character (NPC) Dialogue on AWS

## Table of Content

1. [Overview](#overview)
    - [Architecture](#architecture)
    - [Cost](#cost)
2. [Prerequisites](#prerequisites)
    - [Operating System](#operating-system)
    - [Third-party tools](#third-party-tools)
    - [AWS account requirements](#aws-account-requirements)
    - [aws cdk bootstrap](#aws-cdk-bootstrap)
    - [Supported Regions](#supported-regions)
3. [Deployment Steps](#deployment-steps)
4. [Deployment Validation](#deployment-validation)
5. [Running the Guidance](#running-the-guidance)
    - [Quality Assurance](#quality-assurance)
    - [Hydrating the vector store](#hydrating-the-vector-store)
    - [Unreal Engine sample project](#unreal-engine-sample-project)
6. [Next Steps](#next-steps)
7. [Cleanup](#cleanup)

## Overview

Typical player interactions with NPCs are static, and require large teams of script writers to create static dialog content for each character, in each game, and each game version to ensure consistency with game lore. This Guidance helps game developers automate the process of creating a non-player character (NPC) for their games and associated infrastructure. It uses Unreal Engine, along with foundation models (FMs), for instance, the large language models (LLMs) Claude Haiku 4.5, to improve NPC conversational skills. The solution integrates Amazon Polly to convert NPC responses into speech with viseme data for realistic lip-sync animation in MetaHuman characters. This leads to dynamic responses from the NPC that are unique to each player, adding to scripted dialogue. By using the Large Language Model Ops (LLMOps) methodology, this Guidance accelerates prototyping, and delivery time by continually integrating, and deploying the generative AI application, along with fine-tuning the LLMs. All while helping to ensure that the NPC has full access to a secure knowledge base of game lore, using retrieval-augmented generation (RAG).

___If you're looking for quick and easy step by step guide to get started, check out the Workshop -  [Operationalize Generative AI Applications using LLMOps](https://catalog.us-east-1.prod.workshops.aws/workshops/90992473-01e8-42d6-834f-9baf866a9057/en-US).___

### Architecture

![Architecture](assets/images/architecture.png)

### Cost

_You are responsible for the cost of the AWS services used while running this Guidance. As of April 2026, the cost for running this Guidance with the default settings in the `us-east-1` (N. Virginia) AWS Region is approximately $372 per month for processing 100 requests._

For example, the following table shows a break-down of approximate costs _(per month)_ to process 100 requests, using an **Amazon OpenSearch Service** vector database for RAG:

|     **Service**    | **Cost (per month)** |
|:------------------:|:--------------------:|
| OpenSearch Service | $369.00              |
| SageMaker          | $1.43                |
| S3                 | $0.67                |
| CodeBuild          | $0.34                |
| Secrets Manager    | $0.20                |
| Bedrock            | $0.26                |
|      **Total**     | **$371.90**          |


## Prerequisites

### Operating System, Tools, and Configuration

These deployment instructions are optimized to best work on a **Amazon Linux 2023** based development environment. Deployment using another OS may require additional steps, and configured Python libraries (see [Third-party tools](#third-party-tools)). The instructions also use the [GitHub fork feature](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) that will connect to [AWS CodePipeline](https://aws.amazon.com/codepipeline/). Once the project is deployed, you may use any code editor and Git client to make and push changes to your fork. When developing this project, we used [Visual Studio Code](https://code.visualstudio.com/) and its [Git integration](https://code.visualstudio.com/docs/sourcecontrol/overview).

The Unreal Engine sample project has been tested using a **Windows 2022 Datacenter (g5.4xlarge)** EC2 instance. See the [Stream a remote environment with NICE DCV over QUIC UDP for a 4K monitor at 60 FPS](https://aws.amazon.com/blogs/gametech/stream-remote-environment-nice-dcv-quic-udp-4k-monitor-60-fps/) blog post, for more information on setting up a similar environment.

>__NOTE:__ A Github [dev container](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers) configuration has been provided should you wish to use [GitHub codespaces](https://docs.github.com/en/codespaces), or [Visual Studio Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) as your development environment.

### Third-party tools

Before deploying the guidance code, ensure that the following required tools have been installed:

- AWS Cloud Development Kit (CDK) >= 2.178.2
- Python >= 3.8
- NodeJS >= 18

>__NOTE:__ The Guidance has been tested using AWS CDK version 2.178.2. If you wish to update the CDK application to later version, make sure to update the `requirements.txt`, and `cdk.json` files, in the root of the repository, with the updated version of the AWS CDK.

- Unreal Engine 5.4 (compatible with 5.5 and 5.6).
- Microsoft Visual Studio 2022 for Unreal Engine 5 C++ development.

>__NOTE:__ If you need help with these setup steps, refer to the Unreal Engine 5 documentation, especially "Setting Up Visual Studio for Unreal Engine". The sample was tested with Visual Studio 2022 with Unreal Engine 5.4 and 5.6.

### AWS account requirements

This deployment requires that you have an existing [Amazon SageMaker Domain](https://docs.aws.amazon.com/sagemaker/latest/dg/sm-domain.html) in your AWS account. A SageMaker Domain is required in order to provide access to monitor, and track the following SageMaker resources:

- SageMaker Pipelines
- SageMaker Model Registry

>__NOTE:__ See the [Quick onboard to Amazon SageMaker Domain](https://docs.aws.amazon.com/sagemaker/latest/dg/onboard-quick-start.html) section of the __Amazon SageMaker Developer Guide__ for more information on how to configure an __Amazon SageMaker Domain__ in your AWS account. 

- Bedrock Model Access
    - Anthropic Claude Haiku 4.5
    - Amazon Titan Text Embeddings V2

>__NOTE:__ Bedrock foundation models are now automatically enabled when first invoked. For Anthropic Claude models, some first-time users may need to submit use case details before accessing the model. See the [Model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) section of the __Amazon Bedrock User Guide__ for more information.

### aws cdk bootstrap

This Guidance uses AWS CDK. If you are using `aws-cdk` for the first time, please see the [Bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html) section of the __AWS Cloud Development Kit (AWS CDK) v2__ developer guide, to provision the required resources, before you can deploy AWS CDK apps into an AWS environment.

>__NOTE:__ Since the guidance leveraged CDK PIpelines, it is recommended that you re-bootstrap the CDK, even if you have already bootstrapped the CDK.

### Supported Regions

All features for this guidance are only available in the _US East (N. Virginia)_ and _US West (Oregon)_ AWS regions.

## Deployment Steps

1. Make a fork of this project in GitHub. Select **Fork** and follow the instructions to create a fork in your own GitHub account.
2. Connect GitHub to the AWS Developer Tools in the AWS Console. Though this could be done in the CDK scripts, you would still need to verify the connection in the AWS Console, so it's easier to make the connection there:
    - a. Open the AWS Management Console, and switch to the region where you will deploy the project 
    - b. Navigate to the CodePipeline service
    - c. In the left navigation pane, choose "Settings" and then "Connections"
    - d. Select "Create Connection"
    - e. Choose "GitHub" as the provider
    - f. Name the connection "DynamicNPC"
    - g. Select "Connect to GitHub"
    - h. Authorize AWS Connector for GitHub (you may need to log in to GitHub if you aren't already)
    - i. Leave the defaults, and select "Connect"
    - j. Keep a note of the Arn for the connection
>__NOTE:__ Verify the configuration in GitHub to ensure that the AWS Connector for GitHub [has access to the repository](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-create-github.html).
3. Clone the repository. Note that you will need to [provide a personal access token, or authenticate in some other way](https://docs.github.com/get-started/getting-started-with-git/about-remote-repositories#cloning-with-https-urls):
    ```bash
    git clone https://github.com/[your GitHub user name]/guidance-for-dynamic-game-npc-dialogue-on-aws dynamic-npc
    ```
4. Change to the repository root folder:
    ```bash
    cd dynamic-npc
    ```
5. Initialize the Python virtual environment:
    ```bash
    python3 -m venv .venv
    ```
6. Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```
7. Install the necessary python libraries in the virtual environment:
    ```bash
    python3 -m pip install -r requirements.txt
    ```
8. Type `nano constants.py` to open the `constants.py` file for editing. The following settings can be adjusted to suite your use case:
    - `WORKLOAD_NAME`
        - ___Description:___ The name of the workload that matches your use case. This will be used as a prefix for an component deployed in your AWS account.
        - ___Type:___ String
        - ___Default:___ `"Ada"`
    - `REGION`
        - ___Description:___ The name of the AWS region into which you want to deploy the use case.
        - ___Type:___ String
        - ___Example:___ `"us-east-1"`
    - `GITHUB_REPO_NAME`
        - ___Description:___ The name of your forked GitHub repo, including your username in the format `github_username/repo_name`.
        - ___Type:___ String
        - ___Example:___ `"my-github-username/guidance-for-dynamic-game-npc-dialogue-on-aws"`
    - `CODESTAR_CONNECTION_ARN`
        - ___Description:___ The Arn for the CodeStar Connection you noted above
        - ___Type:___ String
        - ___Example:___ `"arn:aws:codeconnections:us-east-1:555555555555:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"`
    - `SM_DOMAIN_ID`
        - ___Description:___ The ID for your prerequisite __Amazon SageMaker Domain__ in your configured AWS region. You can view the ID for your domain in the [AWS Console](https://console.aws.amazon.com/sagemaker/), or by running the ```aws sagemaker list-domains --query "Domains[*].DomainId" --output text``` command.
        - ___Type:___ String
        - ___Example:___ `"d-abcdef12gh3i"`
    - `QA_ENV_NAME`
        - ___Description:___ The name of the "Quality Assurance" stage of the LLMOps pipeline.
        - ___Type:___ String
        - ___Default:___ `"QA"`
    - `PROD_ENV_NAME`
        - ___Description:___ The name of the "Production" stage of the LLMOps pipeline.
        - ___Type:___ String
        - ___Default:___ `"PROD"`
9. Save the `constants.py` file after updating your use case settings.
10. Verify that the CDK deployment correctly synthesizes the CloudFormation template:
    ```bash
    cdk synth
    ```
11. Deploy the guidance:
    ```bash
    cdk deploy --require-approval never
    ```

## Deployment Validation

To verify a successful deployment of this guidance, open [CloudFormation](https://console.aws.amazon.com/cloudformation/home) console, and verify the status of the stack infrastructure stack is `CREATE_COMPLETE`. For example, if your `WORKLOAD_NAME` parameter is `Ada`, CloudFormation will reflect that the `Ada-Toolchain` stack has a `CREATE_COMPLETE` status.

>__NOTE:__ If upgrading from a previous version of this guidance, the OpenSearch cluster configuration has changed (removed dedicated master nodes). You will need to delete the existing QA/PROD stacks before redeploying. See the [Cleanup](#cleanup) section for instructions.

## Running the Guidance

### Quality Assurance

Once the deployment has been validated, you can deploy the infrastructure into the QA stage, as part of an LLMOps pipeline, using the following steps:

1. Once the toolchain stack has been deployed, add the source code to trigger a CI/CD/CT pipeline execution:
    ```bash
    git add -A
    
    git commit -m "Initial commit"
    
    git push --set-upstream origin main
    ```
    >__NOTE:__ Specifies that you want to push to the `main` branch.
4. Open the [CodePipeline](https://console.aws.amazon.com/codesuite/codepipeline/pipelines) console, and click on the LLMOps pipeline for the workload. For example, if your `WORKLOAD_NAME` parameter is `Ada`, CodePipeline will reflect that the `Ada-Pipeline`  is `In progress`.

<p align="center">
    <img src="assets/images/qa_stage.png" alt="QA Stage" style="width: 43em;" />
</p>

Once the `QA` stage of the pipeline is complete, and the `SystemTest` stage action is successful, indicating the backend infrastructure is deployed, you can hydrate the vector store.

### Hydrating the vector store

>__NOTE:__ This guidance uses 3 data nodes without dedicated master nodes, following AWS best practices for clusters with fewer than 10 nodes. Master election is handled automatically by the data nodes. For production deployments with 10+ nodes or heavy write workloads, consider adding dedicated master nodes.

The following steps will demonstrate how to hydrate the **Amazon OpenSearch Service** vector database for RAG:

1. Download a copy of [Treasure Island by Robert Louis Stevenson](https://www.gutenberg.org/ebooks/120.txt.utf-8) to test vector store hydration and RAG.
2. Using the AWS Console, navigate to Amazon S3 service, and select the bucket with the following format, `<WORKLOAD NAME>-qa-<REGION>-<ACCOUNT NUMBER>`. For example,  `ada-qa-us-east-1-123456789`.
3. Upload the Treasure Island File, by clicking on the upload button, and selecting the file `pg120.txt` file. This will trigger the **AWS Lambda** function that starts a an **Amazon SageMaker Processing Job** to hydrate the **Amazon OpenSearch Service** database.
3. Open the [SageMaker](https://console.aws.amazon.com/sagemaker) console. Using the navigation panel on the left-hand side, expand the `Processing` option, and then select `Processing jobs`. You'll see a processing job has been started, for example `Ada-RAG-Ingest-01-21-20-13-20`. This jobs executes the process of chunking the ebook data, converting it to embeddings, and hydrating the database. 
4. Click on the running processing job to view its configuration. Under the `Monitoring`, click the `View logs` link to see see the processing logs for your job in **Amazon CloudWatch**. After roughly 5 minutes, the log stream becomes available, and after clicking on the log stream, you will see that each line of the log output represents the successful processing of a chunk of the text inserted into the vector store. For example:

<p align="center">
    <img src="assets/images/sagemaker_job_log.png" alt="SageMaker Log" style="width: 33em;" />
</p>

>__NOTE:__ The [Treasure Island by Robert Louis Stevenson](https://www.gutenberg.org/ebooks/120.txt.utf-8) is available for reuse under the terms of the Project Gutenberg License, included with the ebook or online at www.gutenberg.org.

### Unreal Engine sample project

An Unreal Engine sample project, [AmazonPollyMetaHuman](https://artifacts.kits.eventoutfitters.aws.dev/industries/games/AmazonPollyMetaHuman.zip), has been provided for download. This sample [MetaHuman digital character](https://www.unrealengine.com/en-US/digital-humans) can be used to showcase dynamic NPC dialog. Use the following steps to integrate the sample MetaHuman with the deployed guidance infrastructure:

1. Using the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home), click the deployed `QA` stack. For example, if your `WORKLOAD_NAME` parameter is `Ada`, CloudFormation will reflect that `Ada-QA` as the deployed `QA` stack.
2. Select the `Outputs` tab, and capture the values for `TextApiEndpointUrl`, and `RagApiEndpointUrl`.
3. Download the [AmazonPollyMetaHuman](https://artifacts.kits.eventoutfitters.aws.dev/industries/games/AmazonPollyMetaHuman.zip) zipped Unreal Engine project.
4. Extract the `AmazonPollyMetaHuman` project folder.
5. Right-click on the `AmazonPollyMetaHuman.uproject` file and select `Generate Visual Studio project files`.
6. Open the `AmazonPollyMetaHuman.sln` file in Microsoft Visual Studio 2022.
7. In Visual Studio, navigate to `Source/AmazonPollyMetaHuman/Private/SpeechComponent.cpp` and open it for editing.
8. Locate the `CallAPI` function and update the placeholder URLs with your API endpoints from CloudFormation:
    ```cpp
    void USpeechComponent::CallAPI(const FString Text, const FString Uri)
    {
        FString ComboBoxUri = "";
        FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
        UE_LOG(LogPollyMsg, Display, TEXT("%s"), *Uri);
        if(Uri == "Regular LLM")
        {
            UE_LOG(LogPollyMsg, Display, TEXT("If Regular LLM"));
            ComboBoxUri = "<ADD TextApiEndpointUrl VALUE FROM CLOUDFORMATION>";
        } else {
            UE_LOG(LogPollyMsg, Display, TEXT("If Else"));
            
            ComboBoxUri = "<ADD RagApiEndpointUrl VALUE FROM CLOUDFORMATION>";
        }
    ```
9. Save the file.
10. In Visual Studio, select `Build` --> `Build Solution` to compile the project.
11. Once the build completes successfully, close Visual Studio.
12. Open the `AmazonPollyMetaHuman.uproject` file to launch Unreal Engine.
13. Click the `Play` button to interact with the Ada NPC.

>__NOTE:__ Review the detailed [installation guide](assets/docs/metahuman_windows.md) for Windows 2022 for more information on installing, and configuring both Unreal Engine, and the sample project.

## Next Steps

Once the sample application has been validated using the `QA` deployment, you can deploy the infrastructure into production, as part of an LLMOps pipeline, using the following steps:

1. Open the `stacks/toolchain.py` file for editing.
2. Uncomment the following code to enable the `PROD`, and `TUNING` stages of the LLMOps pipeline:
    ```python
    # Add Production Stage
    ToolChainStack._add_stage(
        pipeline=pipeline,
        stage_name=constants.PROD_ENV_NAME,
        stage_account=self.account,
        stage_region=self.region,
        model_parameter_name="CustomModelName"
    )

    # Add tuning stack as CT stage
    ToolChainStack._add_stage(
        pipeline=pipeline,
        stage_name="TUNING",
        stage_account=self.account,
        stage_region=self.region,
        model_parameter_name="CustomModelName"
    )
    ```
3. Save the `toolchain.py` file.
4. Commit the updates to the source repository using the following commands:
    ```bash
    git add -A

    git commit -m "Enabled PROD and TUNING stages"

    git push
    ```
5. Open the [CodePipeline](https://console.aws.amazon.com/codesuite/codepipeline/pipelines) console, and click on the LLMOps pipeline for the workload. For example, if your `WORKLOAD_NAME` parameter is `Ada`, CodePipeline will reflect that the `Ada-Pipeline`  is `In progress`.

>__NOTE:__ Review the [Continuous Tuning using FMOps](https://catalog.us-east-1.prod.workshops.aws/workshops/90992473-01e8-42d6-834f-9baf866a9057/en-US/5-continuous-tuning) section of the **Operationalize Generative AI Applications using LLMOps** workshop for a step-by-step guide to implementing continuous fine-tuning of a custom foundation model for the use case.

## Cleanup

To delete the deployed resources, use the AWS CDK CLI to run the following steps:

1. Change to the root of the cloned repository:
    ```bash
    cd dynamic-npc
    ```
2. Run the command to delete the CloudFormation stack:
    ```bash
    cdk destroy
    ```
3. When prompted, `Are you sure you want to delete`, enter `y` to confirm stack deletion.
4. Use the [CloudFormation](https://console.aws.amazon.com/cloudformation/home) console to manually delete the following stacks in order. For example, if your `WORKLOAD_NAME` parameter is `Ada`, CloudFormation will reflect that the `QA` stack is `Ada-QA`.
    - <WORKLOAD_NAME>-Tuning
    - <WORKLOAD_NAME>-PROD
    - <WORKLOAD_NAME>-QA
5. Remove the git repository with the commands:
    ```bash
    cd ~
    rm -r dynamic-npc
    ```

>__NOTE:__ Deleting the deployed resources will not delete the __Amazon S3__ bucket, in order to protect any training data already stored. See the [Deleting a bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/delete-bucket.html) section of the __Amazon Simple Storage Service__ user guide for the various ways to delete the S3 bucket.

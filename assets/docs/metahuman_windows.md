# Install Unreal Engine 4.27.2 on Windows 2019

## Prerequisites

1. Ensure you have ~50GB of available disk space for the installation.
2. Download and run the ___Visual Studio 2019 (Community Edition)___ installer. See [Setting Up Visual Studio for Unreal Engine](https://docs.unrealengine.com/4.26/en-US/ProductionPipelines/DevelopmentSetup/VisualStudioSetup/) for more information.
    - Select ___Game development with C++___ under ___Workloads___.
    - Under ___Optional___, make sure the checkbox for ___Unreal Engine installer___ is checked to enable it.
3. Download and install [Visual Studio Code](https://code.visualstudio.com/download).
4. Download and install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
    - Configure the AWS CLI credentials to use the Access Key ID and the Secret Access Key for the user.
    - Test access with the following command: ```aws polly describe-voices```, using the ___Command Prompt___.

## Unreal Engine 4.27.2 Installation

1. Run the ___Epic Games Launcher___, by double-clicking on the desktop icon.
2. Sign into your ___Epic Games___ account. 
3. Select ___Unreal Engine___ in the left-hand navigation panel, and click on the ___Library__ tab. 
4. Click the ___ENGINE VERSIONS___ "plus" option, and select ___4.27.2___ from the version drop-down.
5. Click the ___Install___ button.
6. Accept the default installation locations, and click ___Install___.

## Open the MetaHuman Project 

1. Download the [MetaHuman](https://artifacts.kits.eventoutfitters.aws.dev/industries/games/AmazonPollyMetaHuman.zip) sample project.
2. Extract the `AmazonPollyMetaHuman` folder, and copy it to the `Documents\Unreal Projects` folder.
3. Using the ___Unreal Games Launcher___, click on the ___Launch___ button to start the ___Unreal Editor___.
4. When prompted to ___Select or Create New Project___, click the ___More___ button in the top right-hand corner.
5. Click the ___Browse...___ button and navigate to the `Documents\Unreal Projects\AmazonPollyMetaHuman` folder, and double-click on the `AmazonPollyMetaHuman.uproject` file.
6. When prompted, click __Yes__ to rebuild the `AmazonPollyMetaHuman` modules.

## Configure the Backend Integration

1. Using the Unreal Editor, select `File` --> `Generate Visual Studio Code Project` to use VS Code for editing source code.
2. Using the Unreal Editor, select `File` --> `Open Visual Studio Code` to open the project for code editing.
3. In VS Code, open the `/Source/AmazonPollyMetaHuman/Private/Private/SpeechComponent.cpp` file for editing.
4. Navigate to the following code section, and replace the `ComboboxUri` variables with the `TextApiEndpointUrl`, and `RagApiEndpointUrl` CloudFormation outputs.
    ```cpp
        void USpeechComponent::CallAPI(const FString Text, const FString Uri)
        {
            FString ComboBoxUri = "";
            FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
            UE_LOG(LogPollyMsg, Display, TEXT("%s"), *Uri);
            if(Uri == "Regular LLM")
            {
                UE_LOG(LogPollyMsg, Display, TEXT("If Regular LLM"));
                ComboBoxUri = "<ADD `TextApiEndpointUrl` VALUE FROM GUIDANCE DEPLOYMENT>";
            } else {
                UE_LOG(LogPollyMsg, Display, TEXT("If Else"));
                
                ComboBoxUri = "<ADD `RagApiEndpointUrl` VALUE FROM GUIDANCE DEPLOYMENT>";
            }
    ```
5. Save the `SpeechComponent.cpp` file, and close VS Code.
6. Using the Unreal Editor, click the `Compile` button to recompile the C++ code.
7. Once the updated code has been compiled, click the `Play` button to interact with the ___Ada___ NPC.
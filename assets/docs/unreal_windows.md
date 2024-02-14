# Install Unreal Engine 4.27.2 on Windows 2019

## Prerequisites

1. Download and run the ___Visual Studio 2019 (Community Edition)___ installer. See [Setting Up Visual Studio for Unreal Engine](https://docs.unrealengine.com/4.26/en-US/ProductionPipelines/DevelopmentSetup/VisualStudioSetup/) for more information.
    - Select ___Game development with C++___ under ___Workloads___.
    - Under ___Optional___, make sure the checkbox for ___Unreal Engine installer___ is checked to enable it.
2. Download and install [Visual Studio Code](https://code.visualstudio.com/download).
3. Download and install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
    - Configure the AWS CLI credentials to use the Access Key ID and the Secret Access Key for the user.
    - Test access with the following command: ```aws polly describe-voices```, using the ___Command Prompt___.

## Unreal Engine 4.27.2 Installation

1. Run the ___Epic Games Launcher___, by double-clicking on the desktop icon.
2. Sign into your ___Epic Games___ account. 
3. Select ___Unreal Engine___ in the left-hand navigation panel, and click on the ___Library__ tab. 
4. Click the ___ENGINE VERSIONS___ "plus" option, and select ___4.27.2___ from the version drop-down.
5. Click the ___Install___ button.
6. Accept the default installation locations, and click ___Install___.
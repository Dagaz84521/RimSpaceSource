// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/MainMenuWidget.h"
#include "Components/TextBlock.h"
#include "Components/Button.h"
#include "Kismet/GameplayStatics.h"
#include "Subsystem/LLMCommunicationSubsystem.h"

void UMainMenuWidget::NativeConstruct()
{
	Super::NativeConstruct();

	if (StatusText) {
		StatusText->SetText(FText::FromString(TEXT("正在连接服务器...")));
	}
	if (StartGameButton) {
		StartGameButton->SetIsEnabled(false);
		StartGameButton->OnClicked.AddDynamic(this, &UMainMenuWidget::OnStartGameClicked);
	}

	if (UGameInstance* GI = GetGameInstance())
	{
		if (ULLMCommunicationSubsystem* Subsystem = GI->GetSubsystem<ULLMCommunicationSubsystem>())
		{
			Subsystem->OnConnectionStatusChanged.AddDynamic(this, &UMainMenuWidget::OnConnectionStatusUpdate);
			
			// 3. 立即发起连接尝试
			Subsystem->CheckServerConnection();
		}
	}
}

void UMainMenuWidget::OnConnectionStatusUpdate(bool bSuccess, FString Message)
{
	if (StatusText)
	{
		StatusText->SetText(FText::FromString(Message));
		// 可以根据 bSuccess 改变颜色，例如绿色成功，红色失败
		StatusText->SetColorAndOpacity(bSuccess ? FLinearColor::Green : FLinearColor::Red);
	}

	if (StartGameButton)
	{
		// 只有连接成功才允许开始游戏
		StartGameButton->SetIsEnabled(bSuccess);
	}
}

void UMainMenuWidget::OnStartGameClicked()
{
	UGameplayStatics::OpenLevel(this, FName("RimSpaceLevel"));
}

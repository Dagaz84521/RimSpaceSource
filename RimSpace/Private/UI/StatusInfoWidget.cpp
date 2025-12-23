// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/StatusInfoWidget.h"
#include "Components/Overlay.h"
#include "Components/TextBlock.h"

void UStatusInfoWidget::UpdateInfo(const FString& ActorName, const FString& ActorInfo)
{
	if (ActorNameText)
	{
		ActorNameText->SetText(FText::FromString(ActorName));
	}

	if (ActorInfoText)
	{
		ActorInfoText->SetText(FText::FromString(ActorInfo));
	}
}



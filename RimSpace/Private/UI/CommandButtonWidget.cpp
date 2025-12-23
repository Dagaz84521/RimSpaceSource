// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/CommandButtonWidget.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "Interface/CommandProvider.h"
#include "Interface/InteractionInterface.h"

void UCommandButtonWidget::Setup(const FText& CommandName, TScriptInterface<ICommandProvider> TargetProvider)
{
	Cmd = CommandName;
	CommandActor = TargetProvider;
	if (Label)
	{
		Label->SetText(CommandName);
	}
	CommandButton->OnClicked.AddDynamic(this, &UCommandButtonWidget::OnButtonClicked);
}

void UCommandButtonWidget::OnButtonClicked()
{
	if (CommandActor)
	{
		if (CommandActor)
		{
			CommandActor->ExecuteCommand(Cmd);
		}
	}
}
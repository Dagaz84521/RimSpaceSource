// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/CommandMenuWidget.h"
#include "UI/CommandButtonWidget.h"
#include "Components/VerticalBox.h"
#include "Interface/CommandProvider.h"
#include "Interface/InteractionInterface.h"

void UCommandMenuWidget::InitializeMenu(TScriptInterface<ICommandProvider> TargetProvider)
{
	CurrentActor = TargetProvider;
	if (!CurrentActor || !CommandButtonClass || !CommandListBox)
	{
		return;
	}
	if (!CurrentActor)
		return;
	TArray<FText> Commands = CurrentActor->GetCommandList();
	CommandListBox->ClearChildren();
	for (const FText& Command : Commands)
	{
		if (UCommandButtonWidget* CommandButton = CreateWidget<UCommandButtonWidget>(this, CommandButtonClass))
		{
			CommandButton->Setup(Command, CurrentActor);
			CommandListBox->AddChild(CommandButton);
		}
	}
}

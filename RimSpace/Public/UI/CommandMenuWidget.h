// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "CommandMenuWidget.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API UCommandMenuWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintCallable)
	void InitializeMenu(TScriptInterface<ICommandProvider> TargetProvider);

protected:
	UPROPERTY(meta = (BindWidget))
	class UVerticalBox* CommandListBox;

	UPROPERTY(EditDefaultsOnly)
	TSubclassOf<class UCommandButtonWidget> CommandButtonClass;

private:
	UPROPERTY()
	TScriptInterface<ICommandProvider> CurrentActor;
};

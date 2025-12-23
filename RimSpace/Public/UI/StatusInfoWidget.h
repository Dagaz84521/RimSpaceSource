// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "StatusInfoWidget.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API UStatusInfoWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintCallable)
	void UpdateInfo(const FString& ActorName, const FString& ActorInfo);

protected:
	UPROPERTY(meta = (BindWidget))
	class UTextBlock* ActorNameText;

	UPROPERTY(meta = (BindWidget))
	class UTextBlock* ActorInfoText;
};

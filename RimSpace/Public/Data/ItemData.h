// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Engine/DataAsset.h"
#include "ItemData.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API UItemData : public UPrimaryDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	int32 ItemID;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	FName ItemName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	int32 SpaceCost;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Food")
	bool bIsFood = false;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Food", meta = (EditCondition = "bIsFood"))
	float NutritionValue = 0.0f; // 提供的饱食度

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Food", meta = (EditCondition = "bIsFood"))
	int32 EatDuration = 20; // 进食耗时(分钟)
	
};

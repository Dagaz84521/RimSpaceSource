// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
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
};

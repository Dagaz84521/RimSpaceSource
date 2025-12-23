// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "Data/ItemData.h"
#include "RimSpaceGameInstance.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API URimSpaceGameInstance : public UGameInstance
{
	GENERATED_BODY()
public:
	virtual void Init() override;

	const UItemData* GetItemData(int32 ItemID) const;

protected:
	UPROPERTY(EditDefaultsOnly, Category = "RimSpace|Items")
	TArray<TObjectPtr<UItemData>> AllItems;

private:
	TMap<int32, TObjectPtr<UItemData>> ItemMap;
};

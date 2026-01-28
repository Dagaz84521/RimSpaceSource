// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "ItemInfo.generated.h"

/**
 * 
 */

USTRUCT(BlueprintType)
struct FItem
{
	GENERATED_BODY()
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

UCLASS()
class RIMSPACE_API UItemInfo : public UDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	TArray<FItem> Items;

	// 根据 ItemID 查找物品
	FItem* GetItem(int32 ItemID);

#if WITH_EDITOR
	// 从 JSON 文件同步数据到此 DataAsset（编辑器中可点击的按钮）
	UFUNCTION(CallInEditor, Category = "Item")
	void SyncFromJSON();
#endif

private:
	// 从 JSON 文件加载物品数据
	void LoadFromJSON(const FString& JSONFilePath);
};

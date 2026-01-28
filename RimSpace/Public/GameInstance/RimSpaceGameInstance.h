// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "RimSpaceGameInstance.generated.h"

struct FTask;
struct FItem;
class UTaskInfo;
class UItemInfo;
/**
 * 
 */
UCLASS()
class RIMSPACE_API URimSpaceGameInstance : public UGameInstance
{
	GENERATED_BODY()
public:
	virtual void Init() override;

	const FItem* GetItemData(int32 ItemID) const;
	const FTask* GetTaskData(int32 TaskID) const;
	
	// 获取所有物品数据的 JSON 格式（供 LLM 使用）
	TSharedPtr<FJsonObject> GetAllItemsDataAsJson() const;
	// 获取所有任务数据的 JSON 格式（供 LLM 使用）
	TSharedPtr<FJsonObject> GetAllTasksDataAsJson() const;
protected:
	UPROPERTY(EditDefaultsOnly, Category = "RimSpace|Items")
	TObjectPtr<UItemInfo> ItemInfo;
	UPROPERTY(EditDefaultsOnly, Category = "RimSpace|Tasks")
	TObjectPtr<UTaskInfo> TaskInfo;
};

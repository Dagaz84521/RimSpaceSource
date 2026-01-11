// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "ItemStack.h"
#include "Actor/EActorType.h"
#include "TaskInfo.generated.h"

USTRUCT(BlueprintType)
struct FTask
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Task")
	int32 TaskID;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Task")
	FName TaskName;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Task")
	int32 ProductID;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Task")
	int32 TaskWorkload; // 任务工作量，单位：分钟
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Task")
	TArray<FItemStack> Ingredients; // 原料列表
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Task")
	EInteractionType RequiredFacility; // 需要的设施类型
};

/**
 * 
 */
UCLASS()
class RIMSPACE_API UTaskInfo : public UDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
	TArray<FTask> Tasks;
	
	FTask* GetTask(int32 TaskID);
};

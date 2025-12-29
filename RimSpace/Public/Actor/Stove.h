// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Interface/CommandProvider.h"
#include "Stove.generated.h"

struct FTask;
/**
 * 
 */
UCLASS()
class RIMSPACE_API AStove : public ARimSpaceActorBase, public ICommandProvider
{
	GENERATED_BODY()
public:
	virtual TArray<FText> GetCommandList() const override;
	virtual void ExecuteCommand(const FText& Command) override;
	// ActorInfo接口
	virtual FString GetActorInfo() const override;
	AStove();

	//工作相关逻辑
	void SetWorker(class ARimSpaceCharacterBase* NewWorker, int32 TaskID);
	virtual void UpdateEachMinute_Implementation(int32 NewMinute) override;
protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory")
	TObjectPtr<class UInventoryComponent> Inventory;
	
private:
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "WorkStation", meta = (AllowPrivateAccess = "true"))
	TMap<int32, int32> TaskList; // TaskID, 剩余任务数
	UPROPERTY()
	class ARimSpaceCharacterBase* CurrentWorker;

	int32 CurrentTaskID; // 当前任务数据
	int32 CurrentWorkProgress = 0; // 当前工作进度，单位：分钟

	bool HasIngredients(const FTask& Task) const;
	bool ConsumeIngredients(const FTask& Task);
	const FTask* GetCurrentTaskData() const;
};

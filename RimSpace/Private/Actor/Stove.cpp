// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/Stove.h"
#include "Component/InventoryComponent.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "Data/TaskInfo.h"
#include "Character/RimSpaceCharacterBase.h"

TArray<FText> AStove::GetCommandList() const
{
	TArray<FText> CommandList;
	return CommandList;
}

void AStove::ExecuteCommand(const FText& Command)
{
	
}

FString AStove::GetActorInfo() const
{
	FString Info;
	FString InventoryInfo = Inventory->GetInventoryInfo();
	Info += TEXT("=== 库存 ===\n");
	Info += InventoryInfo;
	return Info;
}

AStove::AStove()
{
	Inventory = CreateDefaultSubobject<UInventoryComponent>(TEXT("InputInventory"));
	ActorType = EInteractionType::EAT_Stove;
}

void AStove::SetWorker(class ARimSpaceCharacterBase* NewWorker, int32 TaskID)
{
	if(NewWorker == nullptr)
	{
		UE_LOG(LogTemp, Warning, TEXT("Stove: Worker set to null."));
		CurrentWorker = nullptr;
		CurrentTaskID = 0;
		CurrentWorkProgress = 0;
		return;
	}
	CurrentWorker = NewWorker;
	CurrentTaskID = TaskID; // 记录 Agent 想要做的具体任务
	if (CurrentWorker && CurrentWorker != NewWorker) {
		UE_LOG(LogTemp, Warning, TEXT("Stove is occupied by %s!"), *CurrentWorker->GetName());
		return; 
	}
    
	// 如果换人了或者换任务了，重置进度
	// (这里可以加细致判断，比如同一个人做同一个任务就不重置)
	CurrentWorkProgress = 0;
}

// 当原料不足的时候是否应该把Character转为Idle？
void AStove::UpdateEachMinute_Implementation(int32 NewMinute)
{
	Super::UpdateEachMinute_Implementation(NewMinute);
	// 1. 基础检查：没人或者人没在干活，直接退出
	if (!CurrentWorker || CurrentWorker->GetActionState() != ECharacterActionState::Working) 
	{
		UE_LOG(LogTemp, Warning, TEXT("[Stove]1：没有工人或工人未工作，跳过工作流程。"));
		return;
	}

	// 2. 核心变更：不再自动从 TaskList 取任务
	// 如果 Agent 没有指定任务 (CurrentTaskID 为 0)，则设施不工作
	if (CurrentTaskID <= 0) 
	{
		UE_LOG(LogTemp, Warning, TEXT("[Stove]2：当前任务ID无效，跳过工作流程。"));
		return;
	}

	// 3. 获取任务数据
	const FTask* TaskData = GetCurrentTaskData();
	if (!TaskData) return;

	// 4. 检查原料 (如果是刚开始)
	if (CurrentWorkProgress == 0)
	{
		// 如果原料不足，这里可以选择：
		// A. 直接中断工作 (SetWorker(nullptr, 0))
		// B. 保持等待 (什么都不做)
		// 这里演示简单逻辑：检查通过才干活
		if (!HasIngredients(*TaskData))
		{
			UE_LOG(LogTemp, Warning, TEXT("[Stove] 原料不足，中断工作。"));
			if (CurrentWorker)
			{
				CurrentWorker->SetActionState(ECharacterActionState::Idle);
			}
			SetWorker(nullptr, 0);
			return;
		}
	}

	// 5. 增加进度
	CurrentWorkProgress++;
	GEngine->AddOnScreenDebugMessage(6, 5.f, FColor::Purple,
		FString::Printf(TEXT("[Stove] 工作中... 进度：%d / %d"), 
		CurrentWorkProgress, TaskData->TaskWorkload));
	// 6. 检查完成
	if (CurrentWorkProgress >= TaskData->TaskWorkload)
	{
		// 消耗原料
		if (ConsumeIngredients(*TaskData))
		{
			// 产出产品
			FItemStack Product;
			Product.ItemID = TaskData->ProductID;
			Product.Count = 1; 
			Inventory->AddItem(Product);
		}

		// === 关键修改：结算逻辑 ===
        
		// 检查这个任务是否在玩家的“订单列表”中
		if (TaskList.Contains(CurrentTaskID))
		{
			// 如果在，说明 Agent 完成了玩家的一项指标，扣除次数
			TaskList[CurrentTaskID]--;
            
			// 如果次数归零，从列表中移除
			if (TaskList[CurrentTaskID] <= 0)
			{
				TaskList.Remove(CurrentTaskID);
			}
            
			// 可以在这里给 Agent 一些奖励反馈：“你完成了玩家的任务”
		}
		else
		{
			// 如果不在，说明这是 Agent“自主”决定做的额外储备
			// 不对 TaskList 做任何操作，仅保留产物
		}

		// 重置进度，准备下一个循环
		CurrentWorkProgress = 0;
		CurrentTaskID = 0;
		if (CurrentWorker)
		{
			CurrentWorker->SetActionState(ECharacterActionState::Idle);
			SetWorker(nullptr, 0);
		}
	}
}

bool AStove::HasIngredients(const FTask& Task) const
{
	for (const FItemStack& Ingredient : Task.Ingredients)
	{
		int32 AvailableCount = Inventory->GetItemCount(Ingredient.ItemID);
		if (AvailableCount < Ingredient.Count)
		{
			return false; // 原料不足
		}
	}
	return true;
}

bool AStove::ConsumeIngredients(const FTask& Task)
{
	for (const FItemStack& Ingredient : Task.Ingredients)
	{
		bool bRemoved = Inventory->RemoveItem(Ingredient);
		if (!bRemoved)
		{
			return false; // 消耗失败（理论上不应该发生，因为之前已经检查过）
		}
	}
	return true;
}

const FTask* AStove::GetCurrentTaskData() const
{
	URimSpaceGameInstance* GameInstance = Cast<URimSpaceGameInstance>(GetGameInstance());
	if (!GameInstance) return nullptr;
	return GameInstance->GetTaskData(CurrentTaskID);
}


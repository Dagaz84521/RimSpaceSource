// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/WorkStation.h"
#include "Component/InventoryComponent.h"
#include "Character/RimSpaceCharacterBase.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "Player/RimSpacePlayerController.h"

TArray<FText> AWorkStation::GetCommandList() const
{
	TArray<FText> result;
	// 简单示例：提供三种生产命令
	result.Add(FText::FromString(TEXT("生产棉线")));
	result.Add(FText::FromString(TEXT("生产棉布")));
	result.Add(FText::FromString(TEXT("生产棉衣")));
	return result;
}

void AWorkStation::ExecuteCommand(const FText& Command)
{
	FString CmdString = Command.ToString();
	int32 TargetTaskID = -1;
	FText TitleText;

	// 1. 简单的字符串匹配来确定任务
	// (对应上一步定义的 ID: 1001-棉线, 1002-棉布, 1003-棉衣)
	if (CmdString.Contains(TEXT("棉线")))
	{
		TargetTaskID = 2001;
		TitleText = FText::FromString(TEXT("请输入棉线生产数量"));
	}
	else if (CmdString.Contains(TEXT("棉布")))
	{
		TargetTaskID = 2002;
		TitleText = FText::FromString(TEXT("请输入棉布生产数量"));
	}
	else if (CmdString.Contains(TEXT("棉衣")))
	{
		TargetTaskID = 3001;
		TitleText = FText::FromString(TEXT("请输入棉衣生产数量"));
	}

	// 2. 如果识别到了有效指令，呼出 UI
	if (TargetTaskID != -1)
	{
		// 获取当前已有的任务数（方便玩家在此基础上修改，或者直接覆盖）
		int32 CurrentCount = TaskList.Contains(TargetTaskID) ? TaskList[TargetTaskID] : 0;

		if (ARimSpacePlayerController* PC = Cast<ARimSpacePlayerController>(GetWorld()->GetFirstPlayerController()))
		{
			// 3. 打开输入框
			PC->OpenQuantityInputWidget(
				TitleText,
				CurrentCount,
				[this, TargetTaskID](int32 InputValue) // Lambda 回调
				{
					// 玩家点击确认后，这里的代码会执行：
                    
					if (InputValue > 0)
					{
						// 更新任务列表：直接设置为玩家输入的数字
						this->TaskList.FindOrAdd(TargetTaskID) = InputValue;
                        
						UE_LOG(LogTemp, Log, TEXT("[WorkStation] 任务 %d 更新为: %d"), TargetTaskID, InputValue);
					}
					else
					{
						// 如果输入 0，视为取消任务
						this->TaskList.Remove(TargetTaskID);
						UE_LOG(LogTemp, Log, TEXT("[WorkStation] 任务 %d 已移除"), TargetTaskID);
					}
				}
			);
		}
	}
}

FString AWorkStation::GetActorInfo() const
{
	FString Info;
	FString InventoryInfo = Inventory->GetInventoryInfo();
	Info += TEXT("=== 库存 ===\n");
	Info += InventoryInfo;
	Info += TEXT("\n=== 任务列表 ===\n");
	for (auto& Elem : TaskList)
	{
		const URimSpaceGameInstance* GI = Cast<URimSpaceGameInstance>(GetGameInstance());
		
		if (const FTask* TaskData = GI ? GI->GetTaskData(Elem.Key) : nullptr)
		{
			Info += FString::Printf(TEXT("任务: %s - 剩余次数: %d\n"), *TaskData->TaskName.ToString(), Elem.Value);	
		}
	}
	return Info;
}

AWorkStation::AWorkStation()
{
	Inventory = CreateDefaultSubobject<UInventoryComponent>(TEXT("Inventory"));
	ActorType = EInteractionType::EAT_WorkStation;
}

void AWorkStation::SetWorker(class ARimSpaceCharacterBase* NewWorker, int32 TaskID)
{
	CurrentWorker = NewWorker;
	CurrentTaskID = TaskID; // 记录 Agent 想要做的具体任务
    
	// 如果换人了或者换任务了，重置进度
	// (这里可以加细致判断，比如同一个人做同一个任务就不重置)
	CurrentWorkProgress = 0;
}

void AWorkStation::UpdateEachMinute_Implementation(int32 NewMinute)
{
	// 1. 基础检查：没人或者人没在干活，直接退出
	if (!CurrentWorker || CurrentWorker->GetActionState() != ECharacterActionState::Working) 
	{
		return;
	}

	// 2. 核心变更：不再自动从 TaskList 取任务
	// 如果 Agent 没有指定任务 (CurrentTaskID 为 0)，则设施不工作
	if (CurrentTaskID <= 0) 
	{
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
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Work finished but ingredients missing! Production failed."));
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

bool AWorkStation::HasIngredients(const FTask& Task) const
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

bool AWorkStation::ConsumeIngredients(const FTask& Task)
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

const FTask* AWorkStation::GetCurrentTaskData() const
{
	URimSpaceGameInstance* GameInstance = Cast<URimSpaceGameInstance>(GetGameInstance());
	if (!GameInstance) return nullptr;
	return GameInstance->GetTaskData(CurrentTaskID);
}

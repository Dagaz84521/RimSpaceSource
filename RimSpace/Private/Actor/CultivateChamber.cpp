// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/CultivateChamber.h"
#include "Component/InventoryComponent.h"
#include "Character/RimSpaceCharacterBase.h"
#include "Data/ItemStack.h"


TArray<FText> ACultivateChamber::GetCommandList() const
{
	// 玩家命令：设定要种植什么
	switch (CurrentPhase)
	{
	case ECultivatePhase::ECP_Idle:
		// 空闲时可以选择种植什么
		return { FText::FromString(TEXT("种植棉花")), FText::FromString(TEXT("种植玉米")) };
	case ECultivatePhase::ECP_WaitingToPlant:
	case ECultivatePhase::ECP_Planting:
	case ECultivatePhase::ECP_Growing:
	case ECultivatePhase::ECP_ReadyToHarvest:
	case ECultivatePhase::ECP_Harvesting:
		// 其他阶段可以取消
		return { FText::FromString(TEXT("取消种植")) };
	}
	return {};
}


FString ACultivateChamber::GetActorInfo() const
{
	FString Info;
	Info += TEXT("=== 培养仓信息 ===\n");
	
	// 显示当前种植类型
	Info += TEXT("种植作物: ");
	switch (TargetCultivateType)
	{
	case ECultivateType::ECT_None:
		Info += TEXT("无\n");
		break;
	case ECultivateType::ECT_Cotton:
		Info += TEXT("棉花\n");
		break;
	case ECultivateType::ECT_Corn:
		Info += TEXT("玉米\n");
		break;
	}
	
	// 显示当前阶段和进度
	Info += TEXT("当前阶段: ");
	switch (CurrentPhase)
	{
	case ECultivatePhase::ECP_Idle:
		Info += TEXT("空闲\n");
		break;
	case ECultivatePhase::ECP_WaitingToPlant:
		Info += TEXT("等待工人种植\n");
		break;
	case ECultivatePhase::ECP_Planting:
		Info += FString::Printf(TEXT("种植中 (%d/%d)\n"), CurrentWorkProgress, PlantingWorkload);
		break;
	case ECultivatePhase::ECP_Growing:
		Info += FString::Printf(TEXT("成长中 (%d/%d 小时)\n"), GrowthProgress, GrowthMaxProgress);
		break;
	case ECultivatePhase::ECP_ReadyToHarvest:
		Info += TEXT("等待工人收获\n");
		break;
	case ECultivatePhase::ECP_Harvesting:
		Info += FString::Printf(TEXT("收获中 (%d/%d)\n"), CurrentWorkProgress, HarvestWorkload);
		break;
	}
	
	Info += TEXT("=== 临时存储区 ===\n");
	Info += Inventory->GetInventoryInfo();
	return Info;
}

void ACultivateChamber::ExecuteCommand(const FText& Command)
{
	if (Command.EqualTo(FText::FromString(TEXT("种植棉花"))))
	{
		TargetCultivateType = ECultivateType::ECT_Cotton;
		CurrentPhase = ECultivatePhase::ECP_WaitingToPlant;
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("设定种植棉花，等待工人"));
	}
	else if (Command.EqualTo(FText::FromString(TEXT("种植玉米"))))
	{
		TargetCultivateType = ECultivateType::ECT_Corn;
		CurrentPhase = ECultivatePhase::ECP_WaitingToPlant;
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("设定种植玉米，等待工人"));
	}
	else if (Command.EqualTo(FText::FromString(TEXT("取消种植"))))
	{
		TargetCultivateType = ECultivateType::ECT_None;
		CurrentCultivateType = ECultivateType::ECT_None;
		CurrentPhase = ECultivatePhase::ECP_Idle;
		CurrentWorkProgress = 0;
		GrowthProgress = 0;
		if (CurrentWorker)
		{
			CurrentWorker->SetActionState(ECharacterActionState::Idle);
			CurrentWorker = nullptr;
		}
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("取消种植"));
	}
}

void ACultivateChamber::SetWorker(ARimSpaceCharacterBase* NewWorker)
{
	// 检查是否可以接受工人
	if (NewWorker == nullptr)
	{
		CurrentWorker = nullptr;
		CurrentWorkProgress = 0;
		return;
	}

	// 如果已有其他工人在工作
	if (CurrentWorker && CurrentWorker != NewWorker)
	{
		UE_LOG(LogTemp, Warning, TEXT("CultivateChamber: 已被 %s 占用!"), *CurrentWorker->GetName());
		return;
	}

	// 只有在等待种植或等待收获阶段才能接受工人
	if (CurrentPhase == ECultivatePhase::ECP_WaitingToPlant)
	{
		CurrentWorker = NewWorker;
		CurrentPhase = ECultivatePhase::ECP_Planting;
		CurrentWorkProgress = 0;
		CurrentCultivateType = TargetCultivateType;
		GEngine->AddOnScreenDebugMessage(2, 5.f, FColor::Cyan, TEXT("[培养仓] 工人开始种植"));
	}
	else if (CurrentPhase == ECultivatePhase::ECP_ReadyToHarvest)
	{
		CurrentWorker = NewWorker;
		CurrentPhase = ECultivatePhase::ECP_Harvesting;
		CurrentWorkProgress = 0;
		GEngine->AddOnScreenDebugMessage(2, 5.f, FColor::Cyan, TEXT("[培养仓] 工人开始收获"));
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("CultivateChamber: 当前阶段不需要工人"));
	}
}

void ACultivateChamber::UpdateEachHour_Implementation(int32 NewHour)
{
	Super::UpdateEachHour_Implementation(NewHour);
	
	// 成长阶段：每小时自动增加进度
	if (CurrentPhase == ECultivatePhase::ECP_Growing)
	{
		GrowthProgress++;
		GEngine->AddOnScreenDebugMessage(3, 5.f, FColor::Green,
			FString::Printf(TEXT("[培养仓] 作物成长中... %d/%d"), GrowthProgress, GrowthMaxProgress));
		
		if (GrowthProgress >= GrowthMaxProgress)
		{
			CurrentPhase = ECultivatePhase::ECP_ReadyToHarvest;
			GEngine->AddOnScreenDebugMessage(3, 5.f, FColor::Yellow, TEXT("[培养仓] 作物成熟，等待收获!"));
		}
	}
}

void ACultivateChamber::UpdateEachMinute_Implementation(int32 NewMinute)
{
	Super::UpdateEachMinute_Implementation(NewMinute);
	
	// 种植阶段：需要工人提供工作进度
	if (CurrentPhase == ECultivatePhase::ECP_Planting)
	{
		if (!CurrentWorker || CurrentWorker->GetActionState() != ECharacterActionState::Working)
		{
			return;
		}
		
		CurrentWorkProgress++;
		GEngine->AddOnScreenDebugMessage(4, 5.f, FColor::Blue,
			FString::Printf(TEXT("[培养仓] 种植中... %d/%d"), CurrentWorkProgress, PlantingWorkload));
		
		if (CurrentWorkProgress >= PlantingWorkload)
		{
			// 种植完成，进入成长阶段
			CurrentPhase = ECultivatePhase::ECP_Growing;
			CurrentWorkProgress = 0;
			GrowthProgress = 0;
			
			// 释放工人
			if (CurrentWorker)
			{
				CurrentWorker->SetActionState(ECharacterActionState::Idle);
				CurrentWorker = nullptr;
			}
			GEngine->AddOnScreenDebugMessage(4, 5.f, FColor::Green, TEXT("[培养仓] 种植完成，开始成长!"));
		}
	}
	// 收获阶段：需要工人提供工作进度
	else if (CurrentPhase == ECultivatePhase::ECP_Harvesting)
	{
		if (!CurrentWorker || CurrentWorker->GetActionState() != ECharacterActionState::Working)
		{
			return;
		}
		
		CurrentWorkProgress++;
		GEngine->AddOnScreenDebugMessage(4, 5.f, FColor::Orange,
			FString::Printf(TEXT("[培养仓] 收获中... %d/%d"), CurrentWorkProgress, HarvestWorkload));
		
		if (CurrentWorkProgress >= HarvestWorkload)
		{
			// 收获完成，产出物品
			FItemStack Product;
			switch (CurrentCultivateType)
			{
			case ECultivateType::ECT_Cotton:
				Product.ItemID = 1; // TODO: 使用正确的棉花ID
				Product.Count = 1;
				break;
			case ECultivateType::ECT_Corn:
				Product.ItemID = 2; // TODO: 使用正确的玉米ID
				Product.Count = 1;
				break;
			default:
				break;
			}
			
			if (Product.ItemID > 0)
			{
				Inventory->AddItem(Product);
			}
			
			// 重置状态，如果玩家设定了目标类型，则回到等待种植状态
			CurrentWorkProgress = 0;
			GrowthProgress = 0;
			CurrentCultivateType = ECultivateType::ECT_None;
			
			// 释放工人
			if (CurrentWorker)
			{
				CurrentWorker->SetActionState(ECharacterActionState::Idle);
				CurrentWorker = nullptr;
			}
			
			// 如果玩家还设定着要种植，自动进入下一轮
			if (TargetCultivateType != ECultivateType::ECT_None)
			{
				CurrentPhase = ECultivatePhase::ECP_WaitingToPlant;
				GEngine->AddOnScreenDebugMessage(4, 5.f, FColor::Green, TEXT("[培养仓] 收获完成! 等待下一轮种植"));
			}
			else
			{
				CurrentPhase = ECultivatePhase::ECP_Idle;
				GEngine->AddOnScreenDebugMessage(4, 5.f, FColor::Green, TEXT("[培养仓] 收获完成!"));
			}
		}
	}
}

ACultivateChamber::ACultivateChamber()
{
	Inventory = CreateDefaultSubobject<UInventoryComponent>(TEXT("OutputInventory"));
	ActorType = EInteractionType::EAT_CultivateChamber;
}

TSharedPtr<FJsonObject> ACultivateChamber::GetActorDataAsJson() const
{
	// 先调用父类获取基础信息（ActorName, ActorType, Inventory）
	TSharedPtr<FJsonObject> JsonObject = Super::GetActorDataAsJson();
	
	// 添加培养仓特有信息
	
	// 当前阶段
	JsonObject->SetStringField(TEXT("CultivatePhase"), UEnum::GetValueAsString(CurrentPhase));
	
	// 玩家设定的种植类型
	JsonObject->SetStringField(TEXT("TargetCultivateType"), UEnum::GetValueAsString(TargetCultivateType));
	
	// 当前正在种植的类型
	JsonObject->SetStringField(TEXT("CurrentCultivateType"), UEnum::GetValueAsString(CurrentCultivateType));
	
	// 成长进度
	JsonObject->SetNumberField(TEXT("GrowthProgress"), GrowthProgress);
	JsonObject->SetNumberField(TEXT("GrowthMaxProgress"), GrowthMaxProgress);
	
	// 工作进度（种植/收获阶段）
	JsonObject->SetNumberField(TEXT("WorkProgress"), CurrentWorkProgress);
	
	// 根据阶段返回对应的工作量上限
	int32 WorkloadMax = 0;
	if (CurrentPhase == ECultivatePhase::ECP_Planting || CurrentPhase == ECultivatePhase::ECP_WaitingToPlant)
	{
		WorkloadMax = PlantingWorkload;
	}
	else if (CurrentPhase == ECultivatePhase::ECP_Harvesting || CurrentPhase == ECultivatePhase::ECP_ReadyToHarvest)
	{
		WorkloadMax = HarvestWorkload;
	}
	JsonObject->SetNumberField(TEXT("WorkloadMax"), WorkloadMax);
	
	// 是否有工人在工作
	JsonObject->SetBoolField(TEXT("HasWorker"), CurrentWorker != nullptr);
	
	return JsonObject;
}


// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/CultivateChamber.h"
#include "Component/InventoryComponent.h"


TArray<FText> ACultivateChamber::GetCommandList() const
{
	switch (CurrentCultivateType)
	{
	case ECultivateType::ECT_None:
		return { FText::FromString(TEXT("种植棉花")), FText::FromString(TEXT("种植玉米")) };
	case ECultivateType::ECT_Cotton:
	case ECultivateType::ECT_Corn:
		return { FText::FromString("取消种植") };
	}
	return {};
}




FString ACultivateChamber::GetActorInfo() const
{
	FString Info;
	Info += TEXT("=== 种植舱信息 ===\n");
	Info += FString::Printf(TEXT("培养类型: "));
	switch (CurrentCultivateType)
	{
	case ECultivateType::ECT_None:
		Info += FString::Printf(TEXT("无\n"));
		break;
	case ECultivateType::ECT_Cotton:
		Info += FString::Printf(TEXT("棉花\n"));
		break;
	case ECultivateType::ECT_Corn:
		Info += FString::Printf(TEXT("玉米\n"));
		break;
	}
	Info += FString::Printf(TEXT("培养进度: %d / %d\n"), CultivateProgress, CultivateMaxProgress);
	Info += TEXT("=== 临时存储区 ===\n");
	Info += Inventory->GetInventoryInfo();
	return Info;
}

void ACultivateChamber::ExecuteCommand(const FText& Command)
{
	if (Command.EqualTo(FText::FromString(TEXT("种植棉花"))))
	{
		TargetCultivateType = ECultivateType::ECT_Cotton;
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("开始种植棉花"));
		
	}
	else if (Command.EqualTo(FText::FromString(TEXT("种植玉米"))))
	{
		TargetCultivateType = ECultivateType::ECT_Corn;
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("开始种植玉米"));
		
	}
	else if (Command.EqualTo(FText::FromString("取消种植")))
	{
		TargetCultivateType = ECultivateType::ECT_None;
		GEngine->AddOnScreenDebugMessage(1, 5.f, FColor::Green, TEXT("取消种植"));
	}
}

void ACultivateChamber::UpdateEachHour_Implementation(int32 NewHour)
{
	Super::UpdateEachHour_Implementation(NewHour);
}

void ACultivateChamber::UpdateCultivateProgress()
{
	
}

void ACultivateChamber::UpdateEachMinute_Implementation(int32 NewMinute)
{
	Super::UpdateEachMinute_Implementation(NewMinute);
}

ACultivateChamber::ACultivateChamber()
{
	Inventory = CreateDefaultSubobject<UInventoryComponent>(TEXT("OutputInventory"));
	ActorType = EInteractionType::EAT_CultivateChamber;
}


// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/WorkStation.h"
#include "Component/InventoryComponent.h"

TArray<FText> AWorkStation::GetCommandList() const
{
	return TArray<FText>();
}

void AWorkStation::ExecuteCommand(const FText& Command)
{
}

FString AWorkStation::GetActorInfo() const
{
	FString Info;
	FString InventoryInfo = Inventory->GetInventoryInfo();
	Info += TEXT("=== 库存 ===\n");
	Info += InventoryInfo;
	return Info;
}

AWorkStation::AWorkStation()
{
	Inventory = CreateDefaultSubobject<UInventoryComponent>(TEXT("Inventory"));
	ActorType = EInteractionType::EAT_WorkStation;
}

// Fill out your copyright notice in the Description page of Project Settings.


#include "GameInstance/RimSpaceGameInstance.h"
#include "Data/TaskInfo.h"

void URimSpaceGameInstance::Init()
{
	Super::Init();

	ItemMap.Empty();

	for (UItemData* Item : AllItems)
	{
		if (!Item) continue;

		if (ItemMap.Contains(Item->ItemID))
		{
			UE_LOG(LogTemp, Warning,
				TEXT("Duplicate ItemID %d in ItemData"), Item->ItemID);
			continue;
		}

		ItemMap.Add(Item->ItemID, Item);
	}
}

const UItemData* URimSpaceGameInstance::GetItemData(int32 ItemID) const
{
	if (const TObjectPtr<UItemData>* Found = ItemMap.Find(ItemID))
	{
		return Found->Get();
	}
	return nullptr;
}

const FTask* URimSpaceGameInstance::GetTaskData(int32 TaskID) const
{
	return TaskInfo->GetTask(TaskID);
}

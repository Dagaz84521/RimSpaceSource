// Fill out your copyright notice in the Description page of Project Settings.


#include "GameInstance/RimSpaceGameInstance.h"
#include "Data/TaskInfo.h"
#include "Dom/JsonObject.h"

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

TSharedPtr<FJsonObject> URimSpaceGameInstance::GetAllItemsDataAsJson() const
{
	TSharedPtr<FJsonObject> RootJson = MakeShareable(new FJsonObject());
	TArray<TSharedPtr<FJsonValue>> ItemsArray;
	
	for (const auto& Pair : ItemMap)
	{
		const UItemData* Item = Pair.Value.Get();
		if (!Item) continue;
		
		TSharedPtr<FJsonObject> ItemJson = MakeShareable(new FJsonObject());
		ItemJson->SetNumberField(TEXT("ItemID"), Item->ItemID);
		ItemJson->SetStringField(TEXT("ItemName"), Item->ItemName.ToString());
		ItemJson->SetStringField(TEXT("DisplayName"), Item->DisplayName.ToString());
		ItemJson->SetNumberField(TEXT("SpaceCost"), Item->SpaceCost);
		ItemJson->SetBoolField(TEXT("IsFood"), Item->bIsFood);
		if (Item->bIsFood)
		{
			ItemJson->SetNumberField(TEXT("NutritionValue"), Item->NutritionValue);
			ItemJson->SetNumberField(TEXT("EatDuration"), Item->EatDuration);
		}
		
		ItemsArray.Add(MakeShareable(new FJsonValueObject(ItemJson)));
	}
	
	RootJson->SetArrayField(TEXT("Items"), ItemsArray);
	return RootJson;
}

TSharedPtr<FJsonObject> URimSpaceGameInstance::GetAllTasksDataAsJson() const
{
	TSharedPtr<FJsonObject> RootJson = MakeShareable(new FJsonObject());
	TArray<TSharedPtr<FJsonValue>> TasksArray;
	
	if (!TaskInfo) return RootJson;
	
	for (const FTask& Task : TaskInfo->Tasks)
	{
		TSharedPtr<FJsonObject> TaskJson = MakeShareable(new FJsonObject());
		TaskJson->SetNumberField(TEXT("TaskID"), Task.TaskID);
		TaskJson->SetStringField(TEXT("TaskName"), Task.TaskName.ToString());
		TaskJson->SetNumberField(TEXT("ProductID"), Task.ProductID);
		TaskJson->SetNumberField(TEXT("Workload"), Task.TaskWorkload);
		TaskJson->SetStringField(TEXT("RequiredFacility"), UEnum::GetValueAsString(Task.RequiredFacility));
		
		// 添加原料列表
		TArray<TSharedPtr<FJsonValue>> IngredientsArray;
		for (const FItemStack& Ingredient : Task.Ingredients)
		{
			TSharedPtr<FJsonObject> IngredientJson = MakeShareable(new FJsonObject());
			IngredientJson->SetNumberField(TEXT("ItemID"), Ingredient.ItemID);
			IngredientJson->SetNumberField(TEXT("Count"), Ingredient.Count);
			
			// 尝试获取物品名称以便 LLM 理解
			if (const UItemData* ItemData = GetItemData(Ingredient.ItemID))
			{
				IngredientJson->SetStringField(TEXT("ItemName"), ItemData->DisplayName.ToString());
			}
			
			IngredientsArray.Add(MakeShareable(new FJsonValueObject(IngredientJson)));
		}
		TaskJson->SetArrayField(TEXT("Ingredients"), IngredientsArray);
		
		// 获取产物名称
		if (const UItemData* ProductData = GetItemData(Task.ProductID))
		{
			TaskJson->SetStringField(TEXT("ProductName"), ProductData->DisplayName.ToString());
		}
		
		TasksArray.Add(MakeShareable(new FJsonValueObject(TaskJson)));
	}
	
	RootJson->SetArrayField(TEXT("Tasks"), TasksArray);
	return RootJson;
}

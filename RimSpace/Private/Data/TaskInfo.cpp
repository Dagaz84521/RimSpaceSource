// Fill out your copyright notice in the Description page of Project Settings.


#include "Data/TaskInfo.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FTask* UTaskInfo::GetTask(int32 TaskID)
{
	return Tasks.FindByPredicate([TaskID](const FTask& Task)
	{
		return Task.TaskID == TaskID;
	});
}

#if WITH_EDITOR
void UTaskInfo::SyncFromJSON()
{
	// 使用项目的 Source/Data/Task.json 路径
	FString JSONFilePath = FPaths::ProjectDir() / TEXT("Source/Data/Task.json");
	LoadFromJSON(JSONFilePath);
	
	// 标记资源为已修改，这样就会在编辑器中显示为需要保存
	Modify();
	
	UE_LOG(LogTemp, Warning, TEXT("Tasks synced from JSON! Please save this asset."));
}
#endif

void UTaskInfo::LoadFromJSON(const FString& JSONFilePath)
{
	FString JsonContent;
	if (!FFileHelper::LoadFileToString(JsonContent, *JSONFilePath))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to load Task.json from: %s"), *JSONFilePath);
		return;
	}

	// 解析 JSON 数组
	TArray<TSharedPtr<FJsonValue>> JsonArray;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonContent);
	
	if (!FJsonSerializer::Deserialize(Reader, JsonArray))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to parse Task.json content!"));
		return;
	}

	// 清空现有任务
	Tasks.Empty();

	// 遍历 JSON 数组并转换为 FTask
	for (const TSharedPtr<FJsonValue>& JsonValue : JsonArray)
	{
		const TSharedPtr<FJsonObject>* JsonObject;
		if (!JsonValue->TryGetObject(JsonObject))
		{
			continue;
		}

		FTask NewTask;
		
		// 读取基本字段
		NewTask.TaskID = (*JsonObject)->GetIntegerField(TEXT("TaskID"));
		NewTask.TaskName = FName(*(*JsonObject)->GetStringField(TEXT("TaskName")));
		NewTask.ProductID = (*JsonObject)->GetIntegerField(TEXT("ProductID"));
		NewTask.TaskWorkload = (*JsonObject)->GetIntegerField(TEXT("TaskWorkLoad"));
		
		// 转换 RequiredFacility 字符串为枚举
		FString FacilityString = (*JsonObject)->GetStringField(TEXT("RequiredFacility"));
		NewTask.RequiredFacility = StringToInteractionType(FacilityString);

		// 读取 Ingredients 数组
		const TArray<TSharedPtr<FJsonValue>>* IngredientsArray;
		if ((*JsonObject)->TryGetArrayField(TEXT("Ingredients"), IngredientsArray))
		{
			for (const TSharedPtr<FJsonValue>& IngredientValue : *IngredientsArray)
			{
				const TSharedPtr<FJsonObject>* IngredientObject;
				if (IngredientValue->TryGetObject(IngredientObject))
				{
					FItemStack Ingredient;
					Ingredient.ItemID = (*IngredientObject)->GetIntegerField(TEXT("ItemID"));
					Ingredient.Count = (*IngredientObject)->GetIntegerField(TEXT("Count"));
					NewTask.Ingredients.Add(Ingredient);
				}
			}
		}

		Tasks.Add(NewTask);
	}

	UE_LOG(LogTemp, Log, TEXT("Successfully loaded %d tasks from JSON"), Tasks.Num());
}

EInteractionType UTaskInfo::StringToInteractionType(const FString& TypeString) const
{
	if (TypeString == TEXT("CultivateChamber"))
	{
		return EInteractionType::EAT_CultivateChamber;
	}
	else if (TypeString == TEXT("Stove"))
	{
		return EInteractionType::EAT_Stove;
	}
	else if (TypeString == TEXT("WorkStation"))
	{
		return EInteractionType::EAT_WorkStation;
	}
	else if (TypeString == TEXT("Fridge"))
	{
		return EInteractionType::EAT_Fridge;
	}
	else if (TypeString == TEXT("Storage"))
	{
		return EInteractionType::EAT_Storage;
	}
	else if (TypeString == TEXT("Bed"))
	{
		return EInteractionType::EAT_Bed;
	}
	else if (TypeString == TEXT("Table"))
	{
		return EInteractionType::EAT_Table;
	}
	
	return EInteractionType::EAT_None;
}

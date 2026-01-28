// Fill out your copyright notice in the Description page of Project Settings.


#include "Data/ItemInfo.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FItem* UItemInfo::GetItem(int32 ItemID)
{
	return Items.FindByPredicate([ItemID](const FItem& Item)
	{
		return Item.ItemID == ItemID;
	});
}

#if WITH_EDITOR
void UItemInfo::SyncFromJSON()
{
	// 使用项目的 Source/Data/Item.json 路径
	FString JSONFilePath = FPaths::ProjectDir() / TEXT("Source/Data/Item.json");
	LoadFromJSON(JSONFilePath);
	
	// 标记资源为已修改，这样就会在编辑器中显示为需要保存
	Modify();
	
	UE_LOG(LogTemp, Warning, TEXT("Items synced from JSON! Please save this asset."));
}
#endif

void UItemInfo::LoadFromJSON(const FString& JSONFilePath)
{
	FString JsonContent;
	if (!FFileHelper::LoadFileToString(JsonContent, *JSONFilePath))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to load Item.json from: %s"), *JSONFilePath);
		return;
	}

	// 解析 JSON 数组
	TArray<TSharedPtr<FJsonValue>> JsonArray;
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonContent);
	
	if (!FJsonSerializer::Deserialize(Reader, JsonArray))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to parse Item.json content!"));
		return;
	}

	// 清空现有物品
	Items.Empty();

	// 遍历 JSON 数组并转换为 FItem
	for (const TSharedPtr<FJsonValue>& JsonValue : JsonArray)
	{
		const TSharedPtr<FJsonObject>* JsonObject;
		if (!JsonValue->TryGetObject(JsonObject))
		{
			continue;
		}

		FItem NewItem;
		
		// 读取基本字段
		NewItem.ItemID = (*JsonObject)->GetIntegerField(TEXT("ItemID"));
		NewItem.ItemName = FName(*(*JsonObject)->GetStringField(TEXT("ItemName")));
		NewItem.DisplayName = FText::FromString((*JsonObject)->GetStringField(TEXT("DisplayName")));
		NewItem.SpaceCost = (*JsonObject)->GetIntegerField(TEXT("SpaceCost"));
		
		// 读取食物相关字段
		NewItem.bIsFood = (*JsonObject)->GetBoolField(TEXT("IsFood"));
		
		if (NewItem.bIsFood)
		{
			// 只有当是食物时才读取这些字段
			if ((*JsonObject)->HasField(TEXT("NutritionValue")))
			{
				NewItem.NutritionValue = (*JsonObject)->GetNumberField(TEXT("NutritionValue"));
			}
			if ((*JsonObject)->HasField(TEXT("EatDuration")))
			{
				NewItem.EatDuration = (*JsonObject)->GetIntegerField(TEXT("EatDuration"));
			}
		}

		Items.Add(NewItem);
	}

	UE_LOG(LogTemp, Log, TEXT("Successfully loaded %d items from JSON"), Items.Num());
}


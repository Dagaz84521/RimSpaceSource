// Fill out your copyright notice in the Description page of Project Settings.


#include "Component/InventoryComponent.h"

#include "Data/ItemData.h"
#include "GameInstance/RimSpaceGameInstance.h"

// Sets default values for this component's properties
UInventoryComponent::UInventoryComponent()
{
	// Set this component to be initialized when the game starts, and to be ticked every frame.  You can turn these features
	// off to improve performance if you don't need them.
	PrimaryComponentTick.bCanEverTick = true;
	TotalSpace = 50;
	// ...
}


// Called when the game starts
void UInventoryComponent::BeginPlay()
{
	Super::BeginPlay();

	// ...
	
}


// Called every frame
void UInventoryComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	// ...
}

FString UInventoryComponent::GetInventoryInfo() const
{
	FString Info = FString::Printf(TEXT("InventorySpace: %d / %d\n"), UsedSpace, TotalSpace);
	auto* GI = Cast<URimSpaceGameInstance>(GetWorld()->GetGameInstance());
	if (!GI) return TEXT("Invalid GameInstance\n");
	for (const FItemStack& Stack : Items)
	{
		if (Stack.Count <= 0)
			continue;

		const UItemData* ItemData = GI->GetItemData(Stack.ItemID);
		if (!ItemData)
			continue;

		Info += FString::Printf(
			TEXT("%s × %d\n"),
			*ItemData->DisplayName.ToString(),
			Stack.Count
		);
	}
	return Info;
}

bool UInventoryComponent::AddItem(const FItemStack& Item)
{
	if (!Item.IsValid())
		return false;

	if (!CheckItemIsAccepted(Item))
		return false;

	URimSpaceGameInstance* GI = GetWorld()->GetGameInstance<URimSpaceGameInstance>();
	if (!GI)
		return false;

	const UItemData* ItemData = GI->GetItemData(Item.ItemID);
	if (!ItemData)
		return false;

	const int32 NeededSpace = Item.Count * ItemData->SpaceCost;
	if (UsedSpace + NeededSpace > TotalSpace)
		return false;

	for (FItemStack& Stack : Items)
	{
		if (Stack.ItemID == Item.ItemID)
		{
			Stack.Count += Item.Count;
			UsedSpace += NeededSpace;
			return true;
		}
	}

	Items.Add(Item);
	UsedSpace += NeededSpace;
	return true;
}

bool UInventoryComponent::RemoveItem(const FItemStack& Item)
{
	if (!Item.IsValid())
		return false;

	URimSpaceGameInstance* GI = GetWorld()->GetGameInstance<URimSpaceGameInstance>();
	if (!GI)
		return false;

	const UItemData* ItemData = GI->GetItemData(Item.ItemID);
	if (!ItemData)
		return false;

	for (int32 i = 0; i < Items.Num(); ++i)
	{
		FItemStack& Stack = Items[i];
		if (Stack.ItemID == Item.ItemID)
		{
			if (Stack.Count < Item.Count)
				return false;

			Stack.Count -= Item.Count;
			UsedSpace = FMath::Max(
				0,
				UsedSpace - Item.Count * ItemData->SpaceCost
			);

			if (Stack.Count == 0)
				Items.RemoveAt(i);

			return true;
		}
	}
	return false;
}

bool UInventoryComponent::CheckItemIsAccepted(const FItemStack& Item)
{
	bool Accepted = false;
	URimSpaceGameInstance* GI = GetWorld()->GetGameInstance<URimSpaceGameInstance>();
	if (!GI)
	{
		const UItemData* ItemData = GI->GetItemData(Item.ItemID);
		if (!ItemData)
			return false;
		// 查看物品是否超过容量
		Accepted = (UsedSpace + Item.Count * ItemData->SpaceCost <= TotalSpace);
	}
	return Accepted;
}


int32 UInventoryComponent::GetItemCount(int32 ItemID) const
{
	for (const FItemStack& Stack : Items)
	{
		if (Stack.ItemID == ItemID)
		{
			return Stack.Count;
		}
	}
	return 0;
}

TSharedPtr<FJsonObject> UInventoryComponent::GetInventoryDataAsJson() const
{
	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	TArray<TSharedPtr<FJsonValue>> ItemsArray;
	auto* GI = Cast<URimSpaceGameInstance>(GetWorld()->GetGameInstance());
	if (!GI) return JsonObject;
	for (const FItemStack& Stack : Items)
	{
		if (Stack.Count <= 0) continue;
		TSharedPtr<FJsonObject> ItemObject = MakeShareable(new FJsonObject());
		// 1. 写入 ID (保留 ID 给程序逻辑用，以防万一)
		ItemObject->SetNumberField(TEXT("id"), Stack.ItemID);
		// 2. 写入数量
		ItemObject->SetNumberField(TEXT("count"), Stack.Count);
		const UItemData* Data = GI->GetItemData(Stack.ItemID);
		if (Data)
		{
			ItemObject->SetStringField(TEXT("name"), Data->DisplayName.ToString());
		}
		else
		{
			ItemObject->SetStringField(TEXT("name"), TEXT("UnknownItem"));
		}
		ItemsArray.Add(MakeShareable(new FJsonValueObject(ItemObject)));
	}
	JsonObject->SetArrayField(TEXT("items"), ItemsArray);
	return JsonObject;
}

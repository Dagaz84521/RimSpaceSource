// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Data/ItemData.h"
#include "Data/ItemStack.h"
#include "InventoryComponent.generated.h"


UCLASS( ClassGroup=(Custom), meta=(BlueprintSpawnableComponent) )
class RIMSPACE_API UInventoryComponent : public UActorComponent
{
	GENERATED_BODY()

public:	
	// Sets default values for this component's properties
	UInventoryComponent();
	// Called every frame
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	FString GetInventoryInfo() const;

	bool AddItem(const FItemStack& Item);
	bool RemoveItem(const FItemStack& Item);
	bool CheckItemIsAccepted(const FItemStack& Item);
	int32 GetItemCount(int32 ItemID) const;

	const TArray<FItemStack>& GetAllItems() const { return Items; }

protected:
	// Called when the game starts
	virtual void BeginPlay() override;
	
	UPROPERTY(EditAnywhere)
	TArray<FItemStack> Items;

	UPROPERTY(EditAnywhere)
	int32 TotalSpace;

	UPROPERTY(EditAnywhere)
	int32 UsedSpace;
};

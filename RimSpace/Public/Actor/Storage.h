// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Storage.generated.h"

class UInventoryComponent;
/**
 * 
 */
UCLASS()
class RIMSPACE_API AStorage : public ARimSpaceActorBase
{
	GENERATED_BODY()
public:
	AStorage();
protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory")
	TObjectPtr<UInventoryComponent> InventoryComponent;
};

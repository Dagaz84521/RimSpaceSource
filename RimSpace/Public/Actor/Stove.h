// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Interface/CommandProvider.h"
#include "Stove.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API AStove : public ARimSpaceActorBase, public ICommandProvider
{
	GENERATED_BODY()
public:
	virtual TArray<FText> GetCommandList() const override;
	virtual void ExecuteCommand(const FText& Command) override;
	// ActorInfo接口
	virtual FString GetActorInfo() const override;
	AStove();

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory")
	TObjectPtr<class UInventoryComponent> Inventory;
	
private:
	void TestAddAndRemoveItem(const FText& Command);
};

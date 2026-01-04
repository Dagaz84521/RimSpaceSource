// Fill out your copyright notice in the Description page of Project Settings.
// 因为历史原因，该类已废弃
#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Interface/CommandProvider.h"
#include "SewingMachine.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API ASewingMachine : public ARimSpaceActorBase, public ICommandProvider
{
	GENERATED_BODY()
public:
	virtual TArray<FText> GetCommandList() const override;
	virtual void ExecuteCommand(const FText& Command) override;
	
	virtual FString GetActorInfo() const override;
private:
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Loom", meta = (AllowPrivateAccess = "true"))
	int32 TaskRemainCount;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Loom", meta = (AllowPrivateAccess = "true"))
	int32 IngredientsCount;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Loom", meta = (AllowPrivateAccess = "true"))
	int32 ProductStorageCount;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Loom", meta = (AllowPrivateAccess = "true"))
	int32 ProductStorageMaxCount;
	
};

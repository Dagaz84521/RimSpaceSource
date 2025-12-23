// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Interface/CommandProvider.h"
#include "CultivateChamber.generated.h"

/**
 * 
 */
UENUM(BlueprintType)
enum class ECultivateType : uint8
{
	ECT_None UMETA(DisplayName = "None"),
	ECT_Wait UMETA(DisplayName = "Waiting"),
	ECT_Cotton UMETA(DisplayName = "Cotton"),
	ECT_Corn UMETA(DisplayName = "Corn")
};	

UCLASS()
class RIMSPACE_API ACultivateChamber : public ARimSpaceActorBase, public ICommandProvider
{
	GENERATED_BODY()
public:
	// CommandProvider接口
	virtual TArray<FText> GetCommandList() const override;
	virtual void ExecuteCommand(const FText& Command) override;
	// ActorInfo接口
	virtual FString GetActorInfo() const override;
	// TimeAffectable接口
	virtual void UpdateEachHour_Implementation(int32 NewHour) override;
	void UpdateCultivateProgress();
	virtual void UpdateEachMinute_Implementation(int32 NewMinute) override;

	ACultivateChamber();
protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory")
	TObjectPtr<class UInventoryComponent> Inventory;
	
private:
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	ECultivateType CurrentCultivateType;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	ECultivateType TargetCultivateType;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 CultivateMaxProgress = 100;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 CultivateProgress;
};

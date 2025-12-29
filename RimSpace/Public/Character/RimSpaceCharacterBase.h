// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include  "Data/TimeTracker.h"
#include "GameFramework/Character.h"
#include "Interface/TimeAffectable.h"
#include "AIController.h"
#include "Interface/InteractionInterface.h"
#include "Navigation/PathFollowingComponent.h"
#include "RimSpaceCharacterBase.generated.h"

struct FAgentCommand;
class UInventoryComponent;
class ARimSpaceActorBase;

USTRUCT(BlueprintType)
struct FRimSpaceCharacterStats
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
	float Hunger; // 饱食度

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
	float MaxHunger; //	最大饱食度

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
	float Energy; //  精力值 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Stats")
	float MaxEnergy; // 最大精力值
};

USTRUCT(BlueprintType)
struct FRimSpaceCharacterSkills
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Skills")
	bool bCanCook; // 烹饪技能
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Skills")
	bool bCanFarm; // 农业技能
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Skills")
	bool bCanCraft; // 制造技能
};

UENUM(BlueprintType)
enum class ECharacterActionState : uint8
{
	Idle        UMETA(DisplayName = "Idle"),
	Moving      UMETA(DisplayName = "Moving"),
	Working     UMETA(DisplayName = "Working"), // 正在向设施输送劳动力
	Eating 		UMETA(DisplayName = "Eating"),  // 正在恢复饱食度
	Sleeping    UMETA(DisplayName = "Sleeping") // 正在恢复自身状态
};

UCLASS()
class RIMSPACE_API ARimSpaceCharacterBase : public ACharacter, public ITimeAffectable, public IInteractionInterface
{
	GENERATED_BODY()

public:
	ARimSpaceCharacterBase();
	
	virtual void Tick(float DeltaTime) override;
	
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;
	
	virtual void UpdateEachMinute_Implementation(int32 NewMinute) override;
	virtual void UpdateEachHour_Implementation(int32 NewHour) override;

	virtual void HighlightActor() override;
	virtual void UnHighlightActor() override;
	virtual FString GetActorName() const override;
	virtual FString GetActorInfo() const override;

	bool ExecuteAgentCommand(const FAgentCommand& Command);
	ECharacterActionState GetActionState() const;

protected:
	virtual void BeginPlay() override;

	UFUNCTION(BlueprintCallable)
	bool MoveTo(const FName& Target); // 移动到指定地点
	UFUNCTION()
	void OnMoveCompleted(FAIRequestID RequestID, EPathFollowingResult::Type Result);
	bool TakeItem(int32 ItemID, int32 Count); // 从当前地点拾取物品
	bool PutItem(int32 ItemId, int32 Count); // 在当前地点放下携带物品
	bool UseFacility(int32 ParamId); // 使用当前地点功能

	int32 FindFoodInInventory() const; // 在背包中寻找食物

	// 人物基本属性
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	FRimSpaceCharacterStats CharacterStats;

	// 人物技能
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	FRimSpaceCharacterSkills CharacterSkills;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	ECharacterActionState CurrentActionState = ECharacterActionState::Idle;
	
	// 人物携带的物品
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	UInventoryComponent* CarriedItems; 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	ARimSpaceActorBase* CurrentPlace;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category="Character")
	ARimSpaceActorBase* TargetPlace;

	int32 CurrentMinute;
	int32 CurrentHour;
	
	// 人物进食
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Character")
	int32 EatRemainingMinutes;
	
	float NutritionPerMinute = 0.0f;
};

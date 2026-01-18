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
	ECT_Cotton UMETA(DisplayName = "Cotton"),
	ECT_Corn UMETA(DisplayName = "Corn")
};

UENUM(BlueprintType)
enum class ECultivatePhase : uint8
{
	ECP_Idle UMETA(DisplayName = "Idle"),           // 空闲，等待玩家设定
	ECP_WaitingToPlant UMETA(DisplayName = "WaitingToPlant"), // 等待工人来种植
	ECP_Planting UMETA(DisplayName = "Planting"),   // 种植中（需要工人）
	ECP_Growing UMETA(DisplayName = "Growing"),     // 成长中（自动）
	ECP_ReadyToHarvest UMETA(DisplayName = "ReadyToHarvest"), // 等待工人来收获
	ECP_Harvesting UMETA(DisplayName = "Harvesting") // 收获中（需要工人）
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
	virtual TSharedPtr<FJsonObject> GetActorDataAsJson() const override;
	// TimeAffectable接口
	virtual void UpdateEachHour_Implementation(int32 NewHour) override;
	virtual void UpdateEachMinute_Implementation(int32 NewMinute) override;

	// 工作相关逻辑
	void SetWorker(class ARimSpaceCharacterBase* NewWorker);

	ACultivateChamber();
protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Inventory")
	TObjectPtr<class UInventoryComponent> Inventory;
	
private:
	// 当前种植的作物类型
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	ECultivateType CurrentCultivateType = ECultivateType::ECT_None;

	// 玩家设定要种植的作物类型
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	ECultivateType TargetCultivateType = ECultivateType::ECT_None;

	// 当前阶段
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	ECultivatePhase CurrentPhase = ECultivatePhase::ECP_Idle;

	// 种植工作量
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 PlantingWorkload = 10;

	// 成长所需时间（游戏内小时）
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 GrowthMaxProgress = 24;

	// 收获工作量
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 HarvestWorkload = 10;

	// 当前工作进度（种植/收获阶段使用）
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 CurrentWorkProgress = 0;

	// 成长进度
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "CultivateChamber", meta = (AllowPrivateAccess = "true"))
	int32 GrowthProgress = 0;

	// 当前工人
	UPROPERTY()
	class ARimSpaceCharacterBase* CurrentWorker = nullptr;
};

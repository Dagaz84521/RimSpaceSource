// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Character/RimSpaceCharacterBase.h"
#include "GameFramework/GameModeBase.h"
#include "RimSpaceGameplayGameMode.generated.h"
USTRUCT()
struct FConfigItem
{
	GENERATED_BODY()
	UPROPERTY()
	int32 ItemID = 0;
	UPROPERTY()
	int32 Count = 0;
};

USTRUCT()
struct FConfigStorage
{
	GENERATED_BODY()
	UPROPERTY()
	FString ActorName;
	UPROPERTY()
	TArray<FConfigItem> Items;
};

USTRUCT()
struct FConfigTask
{
	GENERATED_BODY()
	UPROPERTY()
	int32 TaskID = 0;
	UPROPERTY()
	int32 Quantity = 0;
};

USTRUCT()
struct FConfigWorkStation
{
	GENERATED_BODY()
	UPROPERTY()
	FString ActorName;
	UPROPERTY()
	TArray<FConfigTask> Tasks;
};

USTRUCT()
struct FConfigCultivateChamber
{
	GENERATED_BODY()
	UPROPERTY()
	FString ActorName;
	UPROPERTY()
	int32 PlantedCropID = 0;
};

USTRUCT()
struct FConfigCharacter
{
	GENERATED_BODY()
	UPROPERTY()
	FString CharacterName;
	UPROPERTY()
	FVector SpawnLocation = FVector::ZeroVector;
	UPROPERTY()
	FString AssignedBedName; // 绑定的床名称
	UPROPERTY()
	FString Profession;
	UPROPERTY()
	FRimSpaceCharacterStats Stats;
	UPROPERTY()
	FRimSpaceCharacterSkills Skills;
};

USTRUCT()
struct FGameInitData
{
	GENERATED_BODY()
	UPROPERTY()
	TArray<FConfigStorage> Storages;
	UPROPERTY()
	TArray<FConfigWorkStation> WorkStations;
	UPROPERTY()
	TArray<FConfigCultivateChamber> CultivateChambers;
	UPROPERTY()
	TArray<FConfigCharacter> Characters;
};

/**
 * 
 */
UCLASS()
class RIMSPACE_API ARimSpaceGameplayGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	virtual void BeginPlay() override;

protected:
	UPROPERTY(EditDefaultsOnly, Category = "Config")
	TSubclassOf<class ARimSpaceCharacterBase> DefaultCharacterClass;

	UPROPERTY(EditDefaultsOnly, Category = "Config|Appearance")
	TMap<FString, TObjectPtr<USkeletalMesh>> ProfessionMeshMap;

private:
	void LoadAndApplyConfig();

	void ApplyStorageConfig(const TArray<FConfigStorage>& StorageConfigs);

	void ApplyWorkStationConfig(const TArray<FConfigWorkStation>& WorkStationConfigs);

	void ApplyCultivateChamberConfig(const TArray<FConfigCultivateChamber>& CultivateChamberConfigs);

	void ApplyCharacterConfig(const TArray<FConfigCharacter>& CharacterConfigs);
	
};

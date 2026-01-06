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
struct FConfigCharacter
{
	GENERATED_BODY()
	UPROPERTY()
	FString CharacterName;
	UPROPERTY()
	FVector SpawnLocation = FVector::ZeroVector;
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

	void ApplyCharacterConfig(const TArray<FConfigCharacter>& CharacterConfigs);
	
};

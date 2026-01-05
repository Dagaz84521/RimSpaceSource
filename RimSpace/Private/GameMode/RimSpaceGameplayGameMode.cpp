// Fill out your copyright notice in the Description page of Project Settings.


#include "GameMode/RimSpaceGameplayGameMode.h"
#include "Actor/RimSpaceActorBase.h"
#include "Component/InventoryComponent.h"
#include "JsonObjectConverter.h"
#include "Data/ItemStack.h"
#include "Kismet/GameplayStatics.h"
#include "Subsystem/CharacterManagerSubsystem.h"

void ARimSpaceGameplayGameMode::BeginPlay()
{
	Super::BeginPlay();
	LoadAndApplyConfig();
}

void ARimSpaceGameplayGameMode::LoadAndApplyConfig()
{
	FString ConfigFilePath = FPaths::ProjectContentDir() / TEXT("Configs/InitGameData.json");
	FString JsonContent;
	if (!FFileHelper::LoadFileToString(JsonContent, *ConfigFilePath))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to load config file at: %s"), *ConfigFilePath);
		return;
	}
	// 3. 解析 JSON 到 Struct
	FGameInitData InitData;
	if (!FJsonObjectConverter::JsonObjectStringToUStruct(JsonContent, &InitData, 0, 0))
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to parse JSON content!"));
		return;
	}

	UE_LOG(LogTemp, Log, TEXT("Config Loaded! Found %d storage configs and %d character configs."), 
		InitData.Storages.Num(), InitData.Characters.Num());

	// 4. 应用配置
	ApplyStorageConfig(InitData.Storages);
	ApplyCharacterConfig(InitData.Characters);
}

void ARimSpaceGameplayGameMode::ApplyStorageConfig(const TArray<FConfigStorage>& StorageConfigs)
{
	// 获取场景中所有的 RimSpaceActorBase (包含 Storage, WorkStation 等)
	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsOfClass(GetWorld(), ARimSpaceActorBase::StaticClass(), FoundActors);

	// 建立一个名字到 Actor 的映射，方便快速查找
	TMap<FString, ARimSpaceActorBase*> ActorMap;
	for (AActor* Actor : FoundActors)
	{
		if (ARimSpaceActorBase* RimActor = Cast<ARimSpaceActorBase>(Actor))
		{
			// 注意：这里用的是你在 ARimSpaceActorBase 里写的 GetActorName()
			ActorMap.Add(RimActor->GetActorName(), RimActor);
		}
	}

	// 遍历配置并应用
	for (const FConfigStorage& Config : StorageConfigs)
	{
		if (ARimSpaceActorBase** FoundPtr = ActorMap.Find(Config.ActorName))
		{
			ARimSpaceActorBase* TargetActor = *FoundPtr;
			if (UInventoryComponent* Inv = TargetActor->FindComponentByClass<UInventoryComponent>())
			{
				// 清空旧库存（可选）
				// Inv->Clear(); 
                
				// 添加配置的物品
				for (const FConfigItem& Item : Config.Items)
				{
					FItemStack NewItem;
					NewItem.ItemID = Item.ItemID;
					NewItem.Count = Item.Count;
					Inv->AddItem(NewItem);
				}
				UE_LOG(LogTemp, Log, TEXT("Configured Storage: %s"), *Config.ActorName);
			}
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Config specified actor '%s' but it was not found in the level!"), *Config.ActorName);
		}
	}
}

void ARimSpaceGameplayGameMode::ApplyCharacterConfig(const TArray<FConfigCharacter>& CharacterConfigs)
{
	// 1. 获取场景中现有的所有角色（用于混合模式：如果场景里已经摆了，就直接用）
    TArray<AActor*> FoundActors;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), ARimSpaceCharacterBase::StaticClass(), FoundActors);

    for (const FConfigCharacter& Config : CharacterConfigs)
    {
        ARimSpaceCharacterBase* TargetChar = nullptr;

        // --- 步骤 A: 尝试在场景里找同名角色 ---
        for (AActor* Actor : FoundActors)
        {
            if (ARimSpaceCharacterBase* Char = Cast<ARimSpaceCharacterBase>(Actor))
            {
                // 注意：这里假设你有办法设置或获取 Actor 的唯一名称
                // 如果是编辑器摆放的，GetActorLabel() 在打包后不可用，建议用 GetActorName() 或 tag
                if (Char->GetActorName() == Config.CharacterName)
                {
                    TargetChar = Char;
                    UE_LOG(LogTemp, Log, TEXT("Found existing character in level: %s"), *Config.CharacterName);
                    break;
                }
            }
        }

        // --- 步骤 B: 如果没找到，就动态生成一个 (Spawn) ---
        if (!TargetChar)
        {
            if (DefaultCharacterClass)
            {
                FActorSpawnParameters SpawnParams;
                SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
                // 设置生成时的名字（可选，主要用于调试）
                SpawnParams.Name = FName(*Config.CharacterName);

                TargetChar = GetWorld()->SpawnActor<ARimSpaceCharacterBase>(
                    DefaultCharacterClass, 
                    Config.SpawnLocation, 
                    FRotator::ZeroRotator, 
                    SpawnParams
                );
                
                if (TargetChar)
                {
                    UE_LOG(LogTemp, Log, TEXT("Spawned new character: %s"), *Config.CharacterName);
                    
                    // 【重要】如果是动态生成的，你需要手动把名字赋给它
                    // 假设你在 CharacterBase 里有一个 SetActorName 或类似的函数
                    // TargetChar->SetActorName(FName(*Config.CharacterName)); 
                    
                    // 或者通过 CharacterManager 注册
                    if (UCharacterManagerSubsystem* CM = GetWorld()->GetSubsystem<UCharacterManagerSubsystem>())
                    {
                        CM->RegisterCharacterWithName(FName(*Config.CharacterName), TargetChar);
                    }
                }
            }
            else
            {
                UE_LOG(LogTemp, Error, TEXT("DefaultCharacterClass is not set in GameMode! Cannot spawn %s"), *Config.CharacterName);
                continue;
            }
        }

        // --- 步骤 C: 统一应用属性 ---
        if (TargetChar)
        {
            // 1. 强制设置位置（如果是预设的，可能需要挪窝；如果是新生成的，其实已经对齐了，但再设一次无妨）
            TargetChar->SetActorLocation(Config.SpawnLocation);
        	TargetChar->InitialCharacter(Config.Stats, Config.Skills, FName(*Config.CharacterName));
			UE_LOG(LogTemp, Log, TEXT("Initialized character: %s"), *Config.CharacterName);
        }
    }
}

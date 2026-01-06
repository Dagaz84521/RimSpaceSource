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
    // 获取场景中现有的所有角色
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
                if (Char->GetActorName() == Config.CharacterName)
                {
                    TargetChar = Char;
                    UE_LOG(LogTemp, Log, TEXT("Found existing character in level: %s"), *Config.CharacterName);
                    // 现有角色已经执行过 BeginPlay，直接更新属性即可
                    TargetChar->InitialCharacter(Config.Stats, Config.Skills, FName(*Config.CharacterName));
                    break;
                }
            }
        }

        // --- 步骤 B: 如果没找到，就动态生成一个 (使用延迟生成) ---
        if (!TargetChar)
        {
            if (DefaultCharacterClass)
            {
                FTransform SpawnTransform(FRotator::ZeroRotator, Config.SpawnLocation);

                // 1. 使用 SpawnActorDeferred 进行延迟生成
                // 这会创建 Actor 但暂不调用 BeginPlay
                TargetChar = GetWorld()->SpawnActorDeferred<ARimSpaceCharacterBase>(
                    DefaultCharacterClass,
                    SpawnTransform,
                    nullptr,
                    nullptr,
                    ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn
                );

                if (TargetChar)
                {
                    // 2. 在 BeginPlay 之前初始化数据（设置正确的名字！）
                    TargetChar->InitialCharacter(Config.Stats, Config.Skills, FName(*Config.CharacterName));
                    
                    // 3. 设置职业模型（可选，放在这也行，或者 Finish 之后也行）
                    if (!Config.Profession.IsEmpty())
                    {
                        if (TObjectPtr<USkeletalMesh>* FoundMesh = ProfessionMeshMap.Find(Config.Profession))
                        {
                            if (USkeletalMeshComponent* MeshComp = TargetChar->GetMesh())
                            {
                                MeshComp->SetSkeletalMesh(*FoundMesh);
                            }
                        }
                    }

                    // 4. 手动完成生成过程，这将触发 BeginPlay
                    // 此时 BeginPlay 里的 GetActorName() 将返回刚才设置好的 Config.CharacterName
                    UGameplayStatics::FinishSpawningActor(TargetChar, SpawnTransform);
                    
                    UE_LOG(LogTemp, Log, TEXT("Spawned and Initialized new character: %s"), *Config.CharacterName);
                }
            }
            else
            {
                UE_LOG(LogTemp, Error, TEXT("DefaultCharacterClass is not set in GameMode! Cannot spawn %s"), *Config.CharacterName);
            }
        }
        else 
        {
            // 如果是场景中已有的角色，可能需要在这里处理模型更换（如果需要的话）
            if (!Config.Profession.IsEmpty())
            {
                 if (TObjectPtr<USkeletalMesh>* FoundMesh = ProfessionMeshMap.Find(Config.Profession))
                 {
                     if (USkeletalMeshComponent* MeshComp = TargetChar->GetMesh())
                     {
                         MeshComp->SetSkeletalMesh(*FoundMesh);
                     }
                 }
            }
            // 确保位置正确
            TargetChar->SetActorLocation(Config.SpawnLocation);
        }
    }
}

// Fill out your copyright notice in the Description page of Project Settings.


#include "GameMode/RimSpaceGameplayGameMode.h"
#include "Actor/RimSpaceActorBase.h"
#include "Actor/Bed.h"
#include "Actor/WorkStation.h"
#include "Actor/CultivateChamber.h"
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

	UE_LOG(LogTemp, Log, TEXT("Config Loaded! Found %d storage configs, %d workstation configs, %d cultivatechamber configs, and %d character configs."), 
		InitData.Storages.Num(), InitData.WorkStations.Num(), InitData.CultivateChambers.Num(), InitData.Characters.Num());

	// 4. 应用配置
	ApplyStorageConfig(InitData.Storages);
	ApplyWorkStationConfig(InitData.WorkStations);
	ApplyCultivateChamberConfig(InitData.CultivateChambers);
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

void ARimSpaceGameplayGameMode::ApplyWorkStationConfig(const TArray<FConfigWorkStation>& WorkStationConfigs)
{
	// 获取场景中所有的 WorkStation
	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsOfClass(GetWorld(), AWorkStation::StaticClass(), FoundActors);

	// 建立名字到Actor的映射
	TMap<FString, AWorkStation*> WorkStationMap;
	for (AActor* Actor : FoundActors)
	{
		if (AWorkStation* WS = Cast<AWorkStation>(Actor))
		{
			WorkStationMap.Add(WS->GetActorName(), WS);
		}
	}

	// 应用配置
	for (const FConfigWorkStation& Config : WorkStationConfigs)
	{
		if (AWorkStation** FoundPtr = WorkStationMap.Find(Config.ActorName))
		{
			AWorkStation* TargetWS = *FoundPtr;
			
			// 设置任务列表
			for (const FConfigTask& Task : Config.Tasks)
			{
				TargetWS->AddTask(Task.TaskID, Task.Quantity);
			}
			
			UE_LOG(LogTemp, Log, TEXT("Configured WorkStation: %s with %d tasks"), 
				*Config.ActorName, Config.Tasks.Num());
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Config specified WorkStation '%s' but it was not found!"), *Config.ActorName);
		}
	}
}

void ARimSpaceGameplayGameMode::ApplyCultivateChamberConfig(const TArray<FConfigCultivateChamber>& CultivateChamberConfigs)
{
	// 获取场景中所有的 CultivateChamber
	TArray<AActor*> FoundActors;
	UGameplayStatics::GetAllActorsOfClass(GetWorld(), ACultivateChamber::StaticClass(), FoundActors);

	// 建立名字到Actor的映射
	TMap<FString, ACultivateChamber*> ChamberMap;
	for (AActor* Actor : FoundActors)
	{
		if (ACultivateChamber* CC = Cast<ACultivateChamber>(Actor))
		{
			ChamberMap.Add(CC->GetActorName(), CC);
		}
	}

	// 应用配置
	for (const FConfigCultivateChamber& Config : CultivateChamberConfigs)
	{
		if (ACultivateChamber** FoundPtr = ChamberMap.Find(Config.ActorName))
		{
			ACultivateChamber* TargetCC = *FoundPtr;
			
			// 设置种植的作物
			if (Config.PlantedCropID > 0)
			{
				TargetCC->SetPlantedCrop(Config.PlantedCropID);
			}
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Config specified CultivateChamber '%s' but it was not found!"), *Config.ActorName);
		}
	}
}

void ARimSpaceGameplayGameMode::ApplyCharacterConfig(const TArray<FConfigCharacter>& CharacterConfigs)
{
    // 获取场景中现有的所有角色
    TArray<AActor*> FoundActors;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), ARimSpaceCharacterBase::StaticClass(), FoundActors);

    // 获取场景中所有的床
    TArray<AActor*> FoundBeds;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), ABed::StaticClass(), FoundBeds);
    TMap<FString, ABed*> BedMap;
    for (AActor* Actor : FoundBeds)
    {
        if (ABed* Bed = Cast<ABed>(Actor))
        {
            BedMap.Add(Bed->GetActorName(), Bed);
        }
    }

    for (const FConfigCharacter& Config : CharacterConfigs)
    {
        ARimSpaceCharacterBase* TargetChar = nullptr;
        FVector FinalSpawnLocation = Config.SpawnLocation;

        // 如果配置了床，尝试获取床的位置
        ABed* AssignedBed = nullptr;
        if (!Config.AssignedBedName.IsEmpty())
        {
            if (ABed** FoundBed = BedMap.Find(Config.AssignedBedName))
            {
                AssignedBed = *FoundBed;
                // 使用床的交互点位置，并在Z轴上稍微抬高一些，确保角色站在地面上
                FVector BedInteractionPoint = AssignedBed->GetInteractionPoint()->GetComponentLocation();
                // 添加一个向上的偏移量（例如100单位，约1米），确保角色不会穿过床或悬空
                FinalSpawnLocation = BedInteractionPoint + FVector(0, 0, -50.0f);
                UE_LOG(LogTemp, Log, TEXT("Character %s assigned to bed %s at location %s"), 
                    *Config.CharacterName, *Config.AssignedBedName, *FinalSpawnLocation.ToString());
            }
            else
            {
                UE_LOG(LogTemp, Warning, TEXT("Bed '%s' not found for character %s, using default spawn location"), 
                    *Config.AssignedBedName, *Config.CharacterName);
            }
        }

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
                    // 设置床位并移动到床的位置
                    if (AssignedBed)
                    {
                        TargetChar->SetAssignedBed(AssignedBed);
                        TargetChar->SetActorLocation(FinalSpawnLocation);
                    }
                    break;
                }
            }
        }

        // --- 步骤 B: 如果没找到，就动态生成一个 (使用延迟生成) ---
        if (!TargetChar)
        {
            if (DefaultCharacterClass)
            {
                FTransform SpawnTransform(FRotator::ZeroRotator, FinalSpawnLocation);

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
                    
                    // 2.5 设置绑定的床
                    if (AssignedBed)
                    {
                        TargetChar->SetAssignedBed(AssignedBed);
                    }
                    
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
                    
                    UE_LOG(LogTemp, Log, TEXT("Spawned and Initialized new character: %s at %s"), 
                        *Config.CharacterName, 
                        AssignedBed ? *FString::Printf(TEXT("Bed '%s'"), *AssignedBed->GetActorName()) : TEXT("default location"));
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

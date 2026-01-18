// Fill out your copyright notice in the Description page of Project Settings.


#include "Character/RimSpaceCharacterBase.h"
#include "Actor/RimSpaceActorBase.h"
#include "Controller/RimSpaceAIController.h"
#include "Subsystem/RimSpaceTimeSubsystem.h"
#include "Component/InventoryComponent.h"
#include "Components/StaticMeshComponent.h"
#include "NavigationSystem.h"
#include "Actor/CultivateChamber.h"
#include "Actor/Stove.h"
#include "Actor/WorkStation.h"
#include "Data/AgentCommand.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "RimSpace/RimSpace.h"
#include "Subsystem/ActorManagerSubsystem.h"
#include "Subsystem/CharacterManagerSubsystem.h"
#include "Subsystem/LLMCommunicationSubsystem.h"

// Sets default values
ARimSpaceCharacterBase::ARimSpaceCharacterBase()
{
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	AIControllerClass = ARimSpaceAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	CarriedItems = CreateDefaultSubobject<UInventoryComponent>(TEXT("InventoryComponent"));
	CharacterName = TEXT("Character");
}

// Called when the game starts or when spawned
void ARimSpaceCharacterBase::BeginPlay()
{
	Super::BeginPlay();
	auto TimeSubsystem = GetGameInstance()->GetSubsystem<URimSpaceTimeSubsystem>();
	TimeSubsystem->OnMinutePassed.AddDynamic(this, &ARimSpaceCharacterBase::UpdateEachMinute);
	TimeSubsystem->OnHourPassed.AddDynamic(this, &ARimSpaceCharacterBase::UpdateEachHour);
	if (AAIController* AICon = Cast<AAIController>(GetController()))
	{
		AICon->ReceiveMoveCompleted.AddDynamic(
			this,
			&ARimSpaceCharacterBase::OnMoveCompleted
		);
	}
	// 注册到 CharacterManagerSubsystem
	GetWorld()->GetSubsystem<UCharacterManagerSubsystem>()->RegisterCharacterWithName(FName(*GetActorName()), this);
}

bool ARimSpaceCharacterBase::MoveTo(const FName& TargetName)
{
	ARimSpaceActorBase* Target = GetWorld()->GetSubsystem<UActorManagerSubsystem>()->GetActorByName(TargetName);
	if (!Target) return false;

	AAIController* AICon = Cast<AAIController>(GetController());
	if (!AICon) return false;

	USceneComponent* InteractionPoint = Target->GetInteractionPoint();
	if (!InteractionPoint) return false;

	const FVector GoalLocation = InteractionPoint->GetComponentLocation();

	FAIMoveRequest Request;
	Request.SetGoalLocation(GoalLocation);
	Request.SetAcceptanceRadius(1.f);
	Request.SetUsePathfinding(true);

	FNavPathSharedPtr NavPath;
	const EPathFollowingRequestResult::Type Result = AICon->MoveTo(Request, &NavPath);

	if (Result == EPathFollowingRequestResult::RequestSuccessful)
	{
		CurrentPlace = nullptr;
		TargetPlace = Target;
		return true;
	}
	UE_LOG(LogTemp, Log, TEXT("MoveTo Request Failed"));
	return false;
}

void ARimSpaceCharacterBase::OnMoveCompleted(FAIRequestID RequestID, EPathFollowingResult::Type Result)
{
	if (Result != EPathFollowingResult::Success)
	{
		UE_LOG(LogTemp, Log, TEXT("Move Failed or Aborted"));
		SetActionState(ECharacterActionState::Idle);
		TargetPlace = nullptr;
		FinishCommandAndRequestNext();
		return;
	}

	// 空指针检查：确保 TargetPlace 有效
	if (!IsValid(TargetPlace))
	{
		UE_LOG(LogTemp, Warning, TEXT("OnMoveCompleted: TargetPlace is invalid!"));
		SetActionState(ECharacterActionState::Idle);
		FinishCommandAndRequestNext();
		return;
	}

	USceneComponent* IP = TargetPlace->GetInteractionPoint();
	if (!IP)
	{
		UE_LOG(LogTemp, Warning, TEXT("OnMoveCompleted: InteractionPoint is null!"));
		SetActionState(ECharacterActionState::Idle);
		TargetPlace = nullptr;
		FinishCommandAndRequestNext();
		return;
	}

	// ① 精确站位（暂时采用瞬移）
	const FVector StandLocation = IP->GetComponentLocation();
	SetActorLocation(StandLocation);

	// ② 转向（朝向 Actor）
	const FVector LookDir =
		TargetPlace->GetActorLocation() - StandLocation;

	const FRotator TargetRot = LookDir.Rotation();
	SetActorRotation(TargetRot);

	CurrentPlace = TargetPlace;
	TargetPlace = nullptr;
	CurrentActionState = ECharacterActionState::Idle;

	// 移动完成后，请求下一个指令
	FinishCommandAndRequestNext();
}

bool ARimSpaceCharacterBase::TakeItem(int32 ItemID, int32 Count)
{
	if (!CurrentPlace) return false;
	
	UInventoryComponent* TargetInventory = CurrentPlace->GetComponentByClass<UInventoryComponent>();
    
	// 基础判空
	if (!TargetInventory || !CarriedItems)
	{
		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] TakeItem: 缺少库存组件!"));
		return false;
	}

	FItemStack ToTake;
	ToTake.ItemID = ItemID;
	ToTake.Count = Count;

	if(CarriedItems->CheckItemIsAccepted(ToTake) && TargetInventory->GetItemCount(ItemID) >= Count)
	{
		TargetInventory->RemoveItem(ToTake);
		CarriedItems->AddItem(ToTake);
		return true;
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] TakeItem: 物品不可接受或目标地点物品不足!"));
		return false;
	}

	// === 修改开始：防止物品丢失 ===
    
	// 1. 先尝试从目标移除
	/*if (TargetInventory->RemoveItem(ToTake))
	{
		// 2. 尝试添加到自己背包
		if (CarriedItems->AddItem(ToTake))
		{
			// 成功：交易完成
			return true;
		}
		else
		{
			// 失败（背包满了）：必须把物品还给目标容器！
			UE_LOG(LogTemp, Warning, TEXT("[RimSpace] TakeItem: 背包已满，操作回滚!"));
			TargetInventory->AddItem(ToTake); 
			return false;
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] TakeItem: 目标地点物品不足!"));
		return false;
	}*/
}

bool ARimSpaceCharacterBase::PutItem(int32 ItemId, int32 Count)
{
	if (!CurrentPlace) return false;

	UInventoryComponent* TargetInventory = CurrentPlace->GetComponentByClass<UInventoryComponent>();
    
	if (!TargetInventory || !CarriedItems)
	{
		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] PutItem: 缺少库存组件!"));
		return false; 
	}

	FItemStack ToPut;
	ToPut.ItemID = ItemId;
	ToPut.Count = Count;

	// === 修改开始：防止物品丢失 ===

	// 1. 先从自己背包移除
	if (CarriedItems->RemoveItem(ToPut))
	{
		// 2. 尝试放入目标容器
		if (TargetInventory->AddItem(ToPut))
		{
			// 成功
			return true;
		}
		else
		{
			// 失败（箱子满了）：把物品还给自己
			UE_LOG(LogTemp, Warning, TEXT("[RimSpace] PutItem: 目标容器已满，操作回滚!"));
			CarriedItems->AddItem(ToPut);
			return false;
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] PutItem: 背包内物品不足!"));
		return false; 
	}
	// === 修改结束 ===
}

bool ARimSpaceCharacterBase::UseFacility(int32 ParamId)
{
	if (CurrentPlace == nullptr) return false;
    EInteractionType InteractionType = CurrentPlace->GetInteractionType();
    
    // 获取 GameInstance 用于查询物品数据
    auto* GI = GetWorld()->GetGameInstance<URimSpaceGameInstance>();

    switch (InteractionType)
    {
    case EInteractionType::EAT_Stove:
       if (!CharacterSkills.bCanCook) return false;
       CurrentActionState = ECharacterActionState::Working;
    	if (AStove* Stove = Cast<AStove>(CurrentPlace))
    	{
    		Stove->SetWorker(this, ParamId);
    	}
       break;

    case EInteractionType::EAT_CultivateChamber:
       if (!CharacterSkills.bCanFarm) return false;
       CurrentActionState = ECharacterActionState::Working;
    	if (ACultivateChamber* Chamber = Cast<ACultivateChamber>(CurrentPlace))
    	{
    		Chamber->SetWorker(this);
    	}
       break;

    case EInteractionType::EAT_WorkStation:
       if (!CharacterSkills.bCanCraft) return false;
       CurrentActionState = ECharacterActionState::Working;
    	if (AWorkStation* WorkStation = Cast<AWorkStation>(CurrentPlace))
    	{
    		WorkStation->SetWorker(this, ParamId);
    	}
       break;

    case EInteractionType::EAT_Table:
    {
       // 1. 查找背包里的食物
       int32 FoodID = FindFoodInInventory();
       if (FoodID == -1)
       {
       	   UE_LOG(LogTemp, Warning, TEXT("[RimSpace] UseFacility: 背包内没有食物，无法在桌子处进食!"));
           return false; // 没食物，无法进食
       }

       // 2. 获取食物详细数据
       const UItemData* FoodData = GI ? GI->GetItemData(FoodID) : nullptr;
       if (!FoodData) return false;

       // 3. 尝试从背包扣除 1 个食物
       FItemStack ToEat;
       ToEat.ItemID = FoodID;
       ToEat.Count = 1;
       
       if (CarriedItems && CarriedItems->RemoveItem(ToEat))
       {
           // 4. 设置进食状态参数
           CurrentActionState = ECharacterActionState::Eating;
           
           EatRemainingMinutes = FoodData->EatDuration;
           
           // 计算每分钟恢复量（防止除以0）
           if (EatRemainingMinutes > 0)
               NutritionPerMinute = FoodData->NutritionValue / (float)EatRemainingMinutes;
           else
               NutritionPerMinute = FoodData->NutritionValue; // 瞬间吃完
               
           UE_LOG(LogTemp, Log, TEXT("Started eating %s. Restores %.1f/min"), *FoodData->DisplayName.ToString(), NutritionPerMinute);
       }
       else
       {
           return false; // 扣除失败
       }
       break;
    }

    case EInteractionType::EAT_Bed:
    	if (CharacterStats.Energy >= CharacterStats.MaxEnergy)
    	{
    		UE_LOG(LogTemp, Warning, TEXT("[RimSpace] UseFacility: 体力已满，无需睡觉!"));
    		return false; // 体力已满，无需睡觉
    	}
       CurrentActionState = ECharacterActionState::Sleeping;
    	UE_LOG(LogTemp, Log, TEXT("[RimSpace] Sleeping"));
       break;

    default:
       return false;
    }
    return true;
}

int32 ARimSpaceCharacterBase::FindFoodInInventory() const
{
	if (!CarriedItems) return -1;
    
	auto* GI = GetWorld()->GetGameInstance<URimSpaceGameInstance>();
	if (!GI) return -1;

	// 遍历背包寻找第一个 bIsFood 为 true 的物品
	for (const FItemStack& Stack : CarriedItems->GetAllItems())
	{
		const UItemData* Data = GI->GetItemData(Stack.ItemID);
		if (Data && Data->bIsFood)
		{
			return Stack.ItemID;
		}
	}
	return -1;
}

// Called every frame
void ARimSpaceCharacterBase::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

// Called to bind functionality to input
void ARimSpaceCharacterBase::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

}

void ARimSpaceCharacterBase::UpdateEachMinute_Implementation(int32 NewMinute)
{
	ITimeAffectable::UpdateEachMinute_Implementation(NewMinute);
	switch (CurrentActionState)
	{
	case ECharacterActionState::Thinking: // 和Idle采用相同的开销
		ThinkingMinutes++;
	case ECharacterActionState::Idle:
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy - 0.1f, 0.f, 100.f);
		CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.1f, 0.f, 100.f);
		break;
	case ECharacterActionState::Moving:
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy - 0.1f, 0.f, 100.f);
		CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.1f, 0.f, 100.f);
		break;
	case ECharacterActionState::Working:
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy - 0.2f, 0.f, 100.f);
		CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.2f, 0.f, 100.f);
		
		break;
	case ECharacterActionState::Sleeping:
		CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.05f, 0.f, 100.f);
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy + 1.f, 0.f, 100.f);
		if (CharacterStats.Energy >= CharacterStats.MaxEnergy)
		{
			CurrentActionState = ECharacterActionState::Idle;
		}
		break;
	case ECharacterActionState::Eating:
		if (CurrentActionState == ECharacterActionState::Eating)
		{
			if (EatRemainingMinutes > 0)
			{
				EatRemainingMinutes--;
            
				// 恢复饱食度
				CharacterStats.Hunger += NutritionPerMinute;
            
				// 限制最大值
				if (CharacterStats.Hunger > CharacterStats.MaxHunger)
					CharacterStats.Hunger = CharacterStats.MaxHunger;

				// 吃完了
				if (EatRemainingMinutes <= 0)
				{
					CurrentActionState = ECharacterActionState::Idle;
					UE_LOG(LogTemp, Log, TEXT("Finished eating."));
				}
			}
		}
		break;
	case ECharacterActionState::Waiting:
		if (WaitRemainingMinutes > 0)
		{
			WaitRemainingMinutes--;
            
			// 等待时的消耗（比工作低，比 Idle 略低或持平）
			CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy - 0.05f, 0.f, 100.f);
			CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.05f, 0.f, 100.f);

			// 倒计时结束
			if (WaitRemainingMinutes <= 0)
			{
				UE_LOG(LogTemp, Log, TEXT("Agent %s finished waiting."), *CharacterName.ToString());
				// 切换回 Idle，根据上一节的修改，这里会自动触发 FinishCommandAndRequestNext()
				SetActionState(ECharacterActionState::Idle);
			}
		}
		break;
	}
}

void ARimSpaceCharacterBase::UpdateEachHour_Implementation(int32 NewHour)
{
	ITimeAffectable::UpdateEachHour_Implementation(NewHour);

}

void ARimSpaceCharacterBase::HighlightActor()
{
	GetMesh()->SetRenderCustomDepth(true);
	GetMesh()->SetCustomDepthStencilValue(CUSTOM_DEPTH_GREEN);
}

void ARimSpaceCharacterBase::UnHighlightActor()
{
	GetMesh()->SetRenderCustomDepth(false);
}

FString ARimSpaceCharacterBase::GetActorName() const
{
	return CharacterName.ToString();
}

FString ARimSpaceCharacterBase::GetActorInfo() const
{
	FString Info;
	Info += FString::Printf(TEXT("=== 角色状态 ===\n"));
	Info += FString::Printf(TEXT("体力: %.1f / %.1f\n"), CharacterStats.Energy, CharacterStats.MaxEnergy);
	Info += FString::Printf(TEXT("饱食度: %.1f / %.1f\n"), CharacterStats.Hunger, CharacterStats.MaxHunger);
	Info += FString::Printf(TEXT("当前状态: %s\n"), *UEnum::GetValueAsString(CurrentActionState));
	Info += FString::Printf(TEXT("=== 背包物品 ===\n"));
	if (CarriedItems)
	{
		Info += CarriedItems->GetInventoryInfo();
	}
	return Info;
}

TSharedPtr<FJsonObject> ARimSpaceCharacterBase::GetActorDataAsJson() const
{
	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);

	JsonObject->SetStringField("CharacterName", CharacterName.ToString());

	// 添加当前位置信息
	if (CurrentPlace)
	{
		JsonObject->SetStringField("CurrentLocation", CurrentPlace->GetActorName());
	}
	else
	{
		JsonObject->SetStringField("CurrentLocation", "None");
	}

	// 添加当前行动状态
	JsonObject->SetStringField("ActionState", UEnum::GetValueAsString(CurrentActionState));

	if (CarriedItems)
	{
		JsonObject->SetObjectField("Inventory", CarriedItems->GetInventoryDataAsJson());
	}
	
	TSharedPtr<FJsonObject> StatsObject = MakeShareable(new FJsonObject);
	StatsObject->SetNumberField("Hunger", CharacterStats.Hunger);
	StatsObject->SetNumberField("MaxHunger", CharacterStats.MaxHunger);
	StatsObject->SetNumberField("Energy", CharacterStats.Energy);
	StatsObject->SetNumberField("MaxEnergy", CharacterStats.MaxEnergy);
	JsonObject->SetObjectField("CharacterStats", StatsObject);

	TSharedPtr<FJsonObject> SkillsObject = MakeShareable(new FJsonObject);
	SkillsObject->SetBoolField("CanCook", CharacterSkills.bCanCook);
	SkillsObject->SetBoolField("CanFarm", CharacterSkills.bCanFarm);
	SkillsObject->SetBoolField("CanCraft", CharacterSkills.bCanCraft);
	JsonObject->SetObjectField("CharacterSkills", SkillsObject);
	
	return JsonObject;
}

void ARimSpaceCharacterBase::InitialCharacter(const FRimSpaceCharacterStats& Stats,
                                              const FRimSpaceCharacterSkills& Skills, const FName& Name)
{
	CharacterStats = Stats;
	CharacterSkills = Skills;
	CharacterName = Name;
}

bool ARimSpaceCharacterBase::ExecuteAgentCommand(const FAgentCommand& Command)
{
	bool bResult = false;
	switch (Command.CommandType)
	{
	case EAgentCommandType::Move:
		MoveTo(Command.TargetName);
		SetActionState(ECharacterActionState::Moving);
		return true;
	case EAgentCommandType::Take:
		bResult = TakeItem(Command.ParamID, Command.Count);
		FinishCommandAndRequestNext();
		return bResult;
	case EAgentCommandType::Put:
		bResult = PutItem(Command.ParamID, Command.Count);
		FinishCommandAndRequestNext();
		return bResult;
	case EAgentCommandType::Use:
		return UseFacility(Command.ParamID);
	case EAgentCommandType::Wait:
		// 将 ParamID 作为等待的分钟数
			WaitRemainingMinutes = Command.ParamID;
		// 设为 Waiting 状态
		SetActionState(ECharacterActionState::Waiting);
		UE_LOG(LogTemp, Log, TEXT("Agent %s started waiting for %d minutes."), *CharacterName.ToString(), WaitRemainingMinutes);
		return true;
	default:
		UE_LOG(LogTemp, Warning, TEXT("ExecuteAgentCommand: Received None or Unknown command."));
		return false;
	}
}

ECharacterActionState ARimSpaceCharacterBase::GetActionState() const
{
	return CurrentActionState;
}

void ARimSpaceCharacterBase::SetActionState(ECharacterActionState NewActionState)
{
	bool bJustFinishedTask = (CurrentActionState != ECharacterActionState::Idle) && (NewActionState == ECharacterActionState::Idle);
	CurrentActionState = NewActionState;
	if (bJustFinishedTask)
	{
		FinishCommandAndRequestNext();
	}
}

void ARimSpaceCharacterBase::FinishCommandAndRequestNext()
{
	// 防止在游戏开始初始化等情况下误触发
	if (!GetWorld()) return;
	SetActionState(ECharacterActionState::Thinking);


	UE_LOG(LogTemp, Log, TEXT("Character %s finished task. Requesting next..."), *CharacterName.ToString());
	if (ULLMCommunicationSubsystem* LLMSubsystem = GetGameInstance()->GetSubsystem<ULLMCommunicationSubsystem>())
	{
		LLMSubsystem->RequestNextAgentCommand(FName(*CharacterName.ToString()));
	}
}



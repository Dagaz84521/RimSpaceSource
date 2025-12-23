// Fill out your copyright notice in the Description page of Project Settings.


#include "Character/RimSpaceCharacterBase.h"
#include "Actor/RimSpaceActorBase.h"
#include "Controller/RimSpaceAIController.h"
#include "Subsystem/RimSpaceTimeSubsystem.h"
#include "Component/InventoryComponent.h"
#include "Components/StaticMeshComponent.h"
#include "NavigationSystem.h"
#include "Data/AgentCommand.h"
#include "RimSpace/RimSpace.h"
#include "Subsystem/ActorManagerSubsystem.h"

// Sets default values
ARimSpaceCharacterBase::ARimSpaceCharacterBase()
{
 	// Set this character to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	AIControllerClass = ARimSpaceAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	CarriedItems = CreateDefaultSubobject<UInventoryComponent>(TEXT("InventoryComponent"));

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
		return;
	}

	USceneComponent* IP = TargetPlace->GetInteractionPoint();
	if (!IP) return;

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
	
}

bool ARimSpaceCharacterBase::TakeItem(int32 ItemID, int32 Count)
{
	return true;
}

bool ARimSpaceCharacterBase::PutItem(int32 ItemId, int32 Count)
{
	return true;
}

bool ARimSpaceCharacterBase::UseFacility(int32 ParamId)
{
	if (CurrentPlace == nullptr) return false;
	EInteractionType InteractionType = CurrentPlace->GetInteractionType();
	switch (InteractionType)
	{
	case EInteractionType::EAT_Stove:
		if (!CharacterSkills.bCanCook)
			return false;
		// 在炉灶上烹饪食物
		CurrentActionState = ECharacterActionState::Working;
		break;
	case EInteractionType::EAT_CultivateChamber:
		if (!CharacterSkills.bCanFarm)
			return false;
		// 在培养舱中种植农作物
		CurrentActionState = ECharacterActionState::Working;
		break;
	case EInteractionType::EAT_WorkStation:
		if (!CharacterSkills.bCanCraft)
			return false;
		// 使用工作台制造
		CurrentActionState = ECharacterActionState::Working;
		break;
	case EInteractionType::EAT_Table:
		// 在餐桌上用餐
		break;
	case EInteractionType::EAT_Bed:
		CurrentActionState = ECharacterActionState::Sleeping;
		break;
	default:
		break;
	}
	return true;
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
	case ECharacterActionState::Idle:
		break;
	case ECharacterActionState::Moving:
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy - 0.1f, 0.f, 100.f);
		CharacterStats.Hunger = FMath::Clamp(CharacterStats.Hunger - 0.1f, 0.f, 100.f);
		break;
	case ECharacterActionState::Working:
		break;
	case ECharacterActionState::Sleeping:
		CharacterStats.Energy = FMath::Clamp(CharacterStats.Energy + 1.f, 0.f, 100.f);
		if (CharacterStats.Energy >= CharacterStats.MaxEnergy)
		{
			CurrentActionState = ECharacterActionState::Idle;
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
	return TEXT("Character");
}

FString ARimSpaceCharacterBase::GetActorInfo() const
{
	return FString::Printf(
		TEXT("Hunger: %.1f / %.1f\nEnergy: %.1f / %.1f"),
		CharacterStats.Hunger,
		CharacterStats.MaxHunger,
		CharacterStats.Energy,
		CharacterStats.MaxEnergy
	);
}

bool ARimSpaceCharacterBase::ExecuteAgentCommand(const FAgentCommand& Command)
{
	switch (Command.CommandType)
	{
	case EAgentCommandType::Move:
		MoveTo(Command.TargetName);
		return true;
	case EAgentCommandType::Take:
		return TakeItem(Command.ParamID, Command.Count);
	case EAgentCommandType::Put:
		return PutItem(Command.ParamID, Command.Count);
	case EAgentCommandType::Use:
		return UseFacility(Command.ParamID);
	default:
		UE_LOG(LogTemp, Warning, TEXT("ExecuteAgentCommand: Received None or Unknown command."));
		return false;
	}
}



// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/RimSpaceActorBase.h"
#include "RimSpace/RimSpace.h"
#include "JsonObjectConverter.h"
#include "Component/InventoryComponent.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "Subsystem/ActorManagerSubsystem.h"
#include "Subsystem/RimSpaceTimeSubsystem.h"

// Sets default values
ARimSpaceActorBase::ARimSpaceActorBase()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;
	MeshComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeshComponent"));
	RootComponent = MeshComponent;
	InteractionPoint = CreateDefaultSubobject<USceneComponent>(TEXT("InteractionPoint"));
	InteractionPoint->SetupAttachment(RootComponent);

}

// Called when the game starts or when spawned
void ARimSpaceActorBase::BeginPlay()
{
	Super::BeginPlay();
	auto TimeSubsystem = GetGameInstance()->GetSubsystem<URimSpaceTimeSubsystem>();
	TimeSubsystem->OnMinutePassed.AddDynamic(this, &ARimSpaceActorBase::UpdateEachMinute);
	TimeSubsystem->OnHourPassed.AddDynamic(this, &ARimSpaceActorBase::UpdateEachHour);
	auto ActorManagerSubsystem = GetWorld()->GetSubsystem<UActorManagerSubsystem>();
	ActorManagerSubsystem->RegisterActorWithName(FName(*GetActorName()), this);
}

// Called every frame
void ARimSpaceActorBase::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

}

void ARimSpaceActorBase::HighlightActor()
{
	GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Yellow, TEXT("Highlight Actor Called"));
	GetMeshComponent()->SetRenderCustomDepth(true);
	GetMeshComponent()->SetCustomDepthStencilValue(CUSTOM_DEPTH_RED);
}

void ARimSpaceActorBase::UnHighlightActor()
{
	GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Yellow, TEXT("UnHighlight Actor Called"));
	GetMeshComponent()->SetRenderCustomDepth(false);
}

FString ARimSpaceActorBase::GetActorName() const
{
	return ActorName.ToString();
}

FString ARimSpaceActorBase::GetActorInfo() const
{
	// 默认返回空字符串
	return FString();
}

TSharedPtr<FJsonObject> ARimSpaceActorBase::GetActorDataAsJson() const
{
	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	// 使用 JsonObjectConverter 将 Actor 的属性转换为 JSON 对象
	JsonObject->SetStringField(TEXT("ActorName"), GetActorName());
	JsonObject->SetStringField(TEXT("ActorType"), UEnum::GetValueAsString(ActorType));
	// 如果有物品系统，添加物品
	if (UInventoryComponent* InventoryComponent = GetComponentByClass<UInventoryComponent>())
	{
		JsonObject->SetObjectField(TEXT("Inventory"), InventoryComponent->GetInventoryDataAsJson());
	}
	return JsonObject;
}

void ARimSpaceActorBase::UpdateEachMinute_Implementation(int32 NewMinute)
{
	
}

void ARimSpaceActorBase::UpdateEachHour_Implementation(int32 NewHour)
{
	
}



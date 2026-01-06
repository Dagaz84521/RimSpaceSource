// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "EActorType.h"
#include "GameFramework/Actor.h"
#include "Interface/InteractionInterface.h"
#include "Interface/TimeAffectable.h"
#include "Data/TimeTracker.h"
#include "RimSpaceActorBase.generated.h"



UCLASS()
class RIMSPACE_API ARimSpaceActorBase : public AActor, public IInteractionInterface, public ITimeAffectable
{
	GENERATED_BODY()
	
public:	
	ARimSpaceActorBase();
	virtual void Tick(float DeltaTime) override;
	// Interaction implementation
	virtual void HighlightActor() override;
	virtual void UnHighlightActor() override;
	virtual FString GetActorName() const override;
	virtual FString GetActorInfo() const override;
	virtual TSharedPtr<FJsonObject> GetActorDataAsJson() const override;
	// TimeAffectable implementation
	virtual void UpdateEachMinute_Implementation(int32 NewMinute);
	virtual void UpdateEachHour_Implementation(int32 NewHour);
	

	USceneComponent* GetInteractionPoint() const { return InteractionPoint; }

protected:
	virtual void BeginPlay() override;

	UPROPERTY(EditAnywhere)
	class UStaticMeshComponent* MeshComponent;
	
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	TObjectPtr<class USceneComponent> InteractionPoint;

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	FName ActorName;
	
	UPROPERTY(EditDefaultsOnly)
	EInteractionType ActorType = EInteractionType::EAT_None;

public:
	FORCEINLINE class UStaticMeshComponent* GetMeshComponent() const { return MeshComponent; }
	FORCEINLINE EInteractionType GetInteractionType() const { return ActorType; }
};

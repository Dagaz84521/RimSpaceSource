// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"

#include "ActorManagerSubsystem.generated.h"

class ARimSpaceActorBase;
/**
 * 
 */
UCLASS()
class RIMSPACE_API UActorManagerSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	void RegisterActorWithName(const FName& Name, ARimSpaceActorBase* Actor);
	ARimSpaceActorBase* GetActorByName(const FName& Name);
	TSharedPtr<FJsonObject> GetActorsDataAsJson() const;
private:
	TMap<FName, TObjectPtr<ARimSpaceActorBase>> RegisteredActors;
};

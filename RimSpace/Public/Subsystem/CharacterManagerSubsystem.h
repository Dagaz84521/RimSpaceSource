// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Data/AgentCommand.h"
#include "Subsystems/WorldSubsystem.h"
#include "CharacterManagerSubsystem.generated.h"

class ARimSpaceCharacterBase;
/**
 * 
 */

UCLASS()
class RIMSPACE_API UCharacterManagerSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	void RegisterCharacterWithName(const FName& Name, ARimSpaceCharacterBase* Character);
	bool ExecuteCommand(const FAgentCommand& Command);
private:
	TMap<FName, TObjectPtr<ARimSpaceCharacterBase>> RegisteredCharacters;
};

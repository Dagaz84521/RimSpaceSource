// Fill out your copyright notice in the Description page of Project Settings.


#include "Subsystem/CharacterManagerSubsystem.h"
#include "Character/RimSpaceCharacterBase.h"

void UCharacterManagerSubsystem::RegisterCharacterWithName(const FName& Name, ARimSpaceCharacterBase* Character)
{
	if (RegisteredCharacters.Contains(Name))
	{
		UE_LOG(LogTemp, Warning, TEXT("Character with name %s is already registered."), *Name.ToString())
		return;
	}
	RegisteredCharacters.Add(Name, Character);
	UE_LOG(LogTemp, Log, TEXT("Registered actor with name %s."), *Name.ToString());
}

bool UCharacterManagerSubsystem::ExecuteCommand(const FAgentCommand& Command)
{
    // 1. 查找已注册的角色
    // 注意：这里假设 FAgentCommand 结构体中确实有一个 CharacterName 字段
    // 如果没有，你需要修改结构体或者通过其他方式传递角色名称
    if (!RegisteredCharacters.Contains(Command.CharacterName))
    {
        UE_LOG(LogTemp, Warning, TEXT("ExecuteCommand: Character %s not found."), *Command.CharacterName.ToString());
        return false;
    }

    ARimSpaceCharacterBase* Character = RegisteredCharacters[Command.CharacterName];
    if (!IsValid(Character))
    {
        return false;
    }

    return Character->ExecuteAgentCommand(Command);
}



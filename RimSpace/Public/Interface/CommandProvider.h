// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "CommandProvider.generated.h"

// This class does not need to be modified.
UINTERFACE(MinimalAPI)
class UCommandProvider : public UInterface
{
	GENERATED_BODY()
};

/**
 * 
 */
class RIMSPACE_API ICommandProvider
{
	GENERATED_BODY()

	// Add interface functions to this class. This is the class that will be inherited to implement this interface.
public:
	virtual TArray<FText> GetCommandList() const = 0;
	virtual void ExecuteCommand(const FText& Command) = 0;
};

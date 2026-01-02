// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Table.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API ATable : public ARimSpaceActorBase
{
	GENERATED_BODY()
public:
	ATable();
	FString GetActorInfo() const override;
};

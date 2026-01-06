// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Actor/RimSpaceActorBase.h"
#include "Bed.generated.h"

/**
 * 
 */
UCLASS()
class RIMSPACE_API ABed : public ARimSpaceActorBase
{
	GENERATED_BODY()
public:
	ABed();
	virtual FString GetActorInfo() const;
};

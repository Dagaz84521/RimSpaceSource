// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "WorkableInterface.generated.h"

// This class does not need to be modified.
UINTERFACE(MinimalAPI)
class UWorkableInterface : public UInterface
{
	GENERATED_BODY()
};

UENUM(BlueprintType)
enum class EWorkResult : uint8
{
	Success             UMETA(DisplayName = "Success"),
	Fail_Occupied       UMETA(DisplayName = "Failed: Station Occupied"), // 被占用
	Fail_MissingInput   UMETA(DisplayName = "Failed: Missing Input"),    // 缺原料
	Fail_OutputFull     UMETA(DisplayName = "Failed: Output Full"),      // 产出堆满了
	Fail_NoSkill  UMETA(DisplayName = "Failed: Not Authorized")    // 技能等级不够
};

/**
 * 
 */
class RIMSPACE_API IWorkableInterface
{
	GENERATED_BODY()
	
	// Add interface functions to this class. This is the class that will be inherited to implement this interface.
public:
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Work Interaction")
	EWorkResult AddWorkload();
};

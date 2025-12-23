#pragma once

#include "CoreMinimal.h"
#include "TimeTracker.generated.h"

USTRUCT(BlueprintType)
struct FTimeTracker
{
	GENERATED_BODY()
	// 累积的时间
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cultivate Time")
	int32 TimeAccumulator = 0;

	// 时间间隔
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cultivate Time")
	int32 MinutesInterval = 1;
};

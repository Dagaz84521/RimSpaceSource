#pragma once
#include "CoreMinimal.h"
#include "ItemStack.generated.h"

USTRUCT(BlueprintType)
struct RIMSPACE_API FItemStack
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	int32 ItemID = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	int32 Count = 0;

	bool IsValid() const { return ItemID != 0 && Count > 0; }
};
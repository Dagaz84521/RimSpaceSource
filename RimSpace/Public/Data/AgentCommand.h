#pragma once

#include "CoreMinimal.h"
#include "Actor/EActorType.h"
#include "AgentCommand.generated.h"

UENUM(BlueprintType)
enum class EAgentCommandType : uint8
{
    None,
    Move,
    Take,
    Put,
    Use
};

USTRUCT(BlueprintType)
struct RIMSPACE_API FAgentCommand
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName CharacterName;
    
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    EAgentCommandType CommandType = EAgentCommandType::None;
    
    // 目标名称（用于Move）
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName TargetName;
    
    // 物品ID（用于Take、Put）
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 ParamID = 0; // Take/Put 的 ItemID，或者 Use 的 RecipeID/ActionID

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 Count = 0; // Take/Put 的数量
};
#pragma once
UENUM(BlueprintType)
enum class EInteractionType: uint8
{
	EAT_None UMETA(DisplayName = "无"),
	EAT_CultivateChamber UMETA(DisplayName = "培养仓"),
	EAT_Stove UMETA(DisplayName = "厨房"),
	EAT_WorkStation UMETA(DisplayName = "工作台"),
	EAT_Fridge UMETA(DisplayName = "冰箱"),
	EAT_Storage UMETA(DisplayName = "仓库"),
	EAT_Bed UMETA(DisplayName = "床"),
	EAT_Table UMETA(DisplayName = "桌子"),
};

UENUM(BlueprintType)
enum class EShowInfoType: uint8
{
	EIT_Character UMETA(DisplayName = "角色"),
	EIT_Storage UMETA(DisplayName = "仓库"),
	EIT_Chamber UMETA(DisplayName = "培养仓"),
	EIT_Kitchen UMETA(DisplayName = "厨房"),
	EIT_WorkStation UMETA(DisplayName = "工作台"),
	EIT_Fridge UMETA(DisplayName = "冰箱"),
};


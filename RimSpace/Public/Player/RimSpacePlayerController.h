// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "RimSpacePlayerController.generated.h"

/**
 * 
 */

class UCommandMenuWidget;
class ARimSpaceActorBase;
class IInteractionInterface;
struct FInputActionValue;
class UInputAction;
class UInputMappingContext;
class ICommandProvider;

UCLASS

()
class RIMSPACE_API ARimSpacePlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	virtual void BeginPlay() override;
	virtual void PlayerTick(float DeltaTime) override;
protected:
	virtual void SetupInputComponent() override;

private:

	// 摄像机控制
	UPROPERTY(EditAnywhere, Category = "Camera Settings")
	FVector2D MinMapBounds = FVector2D(-5000.0f, -5000.0f); // 地图左下角
	UPROPERTY(EditAnywhere, Category = "Camera Settings")
	FVector2D MaxMapBounds = FVector2D(5000.0f, 5000.0f);   // 地图右上角
	
	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputMappingContext> RimSpaceContext;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> MoveAction;
	UPROPERTY(EditAnywhere, Category = "Input")
    float MoveSpeed = 800.0f; // 镜头XY轴移动速度（cm/秒）
	void Move(const FInputActionValue& Value);

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> UpDownAction;
	void UpDown(const FInputActionValue& Value);

	UPROPERTY(EditAnywhere, Category = "Input")
	float UpDownSpeed = 100.0f;

	//鼠标控制
	void CursorTrace();
	FHitResult CursorHit;
	UPROPERTY()
	TScriptInterface<IInteractionInterface> LastInteractionTarget;
	UPROPERTY()
	TScriptInterface<IInteractionInterface> CurrentInteractionTarget;
	UPROPERTY()
	TScriptInterface<ICommandProvider> RightClickedCommandTarget;
	//右键
	void RightClick(const FInputActionValue& Value);
	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> RightClickAction;

	//左键
	void LeftClick(const FInputActionValue& Value);
	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> LeftClickAction;
	
	// 悬停信息界面
	UPROPERTY(EditDefaultsOnly, Category = "UI/Hover Info")
	TSubclassOf<UUserWidget> HoverInfoWidgetClass;
	TObjectPtr<UUserWidget> HoverInfoWidget;

	void UpdateHoverInfo();

	// 右键案件界面
	UPROPERTY(EditDefaultsOnly, Category = "UI/Command Menu")
	TSubclassOf<UCommandMenuWidget> CommandMenuWidgetClass;
	TObjectPtr<UCommandMenuWidget> CommandMenuWidget;
	void SpawnCommandMenu();
	void UpdateCommandMenu();
};

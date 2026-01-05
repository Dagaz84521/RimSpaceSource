// Fill out your copyright notice in the Description page of Project Settings.


#include "Player/RimSpacePlayerController.h"
#include "Blueprint/UserWidget.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Actor/RimSpaceActorBase.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "UI/QuantitySelectWidget.h"
#include "Interface/CommandProvider.h"
#include "UI/StatusInfoWidget.h"
#include "Interface/InteractionInterface.h"
#include "Subsystem/RimSpaceTimeSubsystem.h"
#include "UI/CommandMenuWidget.h"

void ARimSpacePlayerController::BeginPlay()
{
	Super::BeginPlay();
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
		Subsystem->AddMappingContext(RimSpaceContext,0);
	bShowMouseCursor = true;
	DefaultMouseCursor = EMouseCursor::Default;
	if (HoverInfoWidgetClass)
	{
		HoverInfoWidget = CreateWidget<UUserWidget>(this, HoverInfoWidgetClass);
		if (HoverInfoWidget)
		{
			HoverInfoWidget->AddToViewport();
			HoverInfoWidget->SetVisibility(ESlateVisibility::Hidden);
		}
	}

	if (URimSpaceGameInstance* GI = Cast<URimSpaceGameInstance>(GetGameInstance()))
	{
		if (URimSpaceTimeSubsystem* TimeSubsystem = GI->GetSubsystem<URimSpaceTimeSubsystem>())
		{
			// 设定从早上 8 点开始
			TimeSubsystem->StartTimeSystem();
		}
	}
}

void ARimSpacePlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);

	CursorTrace();
	UpdateHoverInfo();
	UpdateCommandMenu();
}

void ARimSpacePlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	UEnhancedInputComponent* EnhancedInputComponent = CastChecked<UEnhancedInputComponent>(InputComponent);
	EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ARimSpacePlayerController::Move);
	EnhancedInputComponent->BindAction(UpDownAction, ETriggerEvent::Triggered, this, &ARimSpacePlayerController::UpDown);
	EnhancedInputComponent->BindAction(RightClickAction, ETriggerEvent::Completed, this, &ARimSpacePlayerController::RightClick);
	EnhancedInputComponent->BindAction(LeftClickAction, ETriggerEvent::Completed, this, &ARimSpacePlayerController::LeftClick);
}

void ARimSpacePlayerController::Move(const FInputActionValue& Value)
{
	if (APawn* ControlledPawn = GetPawn<APawn>())
	{
		const FVector2D InputAxisVector = Value.Get<FVector2D>();
		const float DeltaTime = GetWorld()->GetDeltaSeconds();
        
		// 获取镜头控制旋转（仅Yaw生效，保持俯视）
		const FRotator YawRotation(0, GetControlRotation().Yaw, 0);
        
		// 计算世界空间的前后/左右方向
		const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
		const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);
        
		// 计算XY轴位移（结合输入、速度、DeltaTime）
		FVector MovementDelta = (ForwardDirection * InputAxisVector.Y + RightDirection * InputAxisVector.X) 
							  * MoveSpeed * DeltaTime;
        
		// 保持Z轴高度不变（俯视镜头只动XY）
		MovementDelta.Z = 0;

		FVector NewLocation = ControlledPawn->GetActorLocation() + MovementDelta;
		NewLocation.X = FMath::Clamp(NewLocation.X, MinMapBounds.X, MaxMapBounds.X);
		NewLocation.Y = FMath::Clamp(NewLocation.Y, MinMapBounds.Y, MaxMapBounds.Y);
		// 直接更新镜头Pawn位置
		ControlledPawn->SetActorLocation(ControlledPawn->GetActorLocation() + MovementDelta);
	}
}

void ARimSpacePlayerController::UpDown(const FInputActionValue& Value)
{
	if (APawn* ControlledPawn = GetPawn<APawn>())
	{
		const float InputAxisValue = Value.Get<float>();
		const float DeltaTime = GetWorld()->GetDeltaSeconds();
        
		// 计算Z轴位移增量（UpDownSpeed直接控制速度，单位：cm/秒）
		const float ZDelta = InputAxisValue * UpDownSpeed * DeltaTime;
        
		// 获取镜头Pawn当前位置
		FVector NewLocation = ControlledPawn->GetActorLocation();
        
		// 限制镜头高度范围（根据你的需求调整最小值和最大值）
		NewLocation.Z = FMath::Clamp(NewLocation.Z - ZDelta, 500.0f, 5000.0f);
        
		// 直接设置镜头Pawn的位置
		ControlledPawn->SetActorLocation(NewLocation);
	}
}

void ARimSpacePlayerController::CursorTrace()
{
	GetHitResultUnderCursor(ECC_Visibility, false, CursorHit);
	if (!CursorHit.bBlockingHit) return;
	GEngine->AddOnScreenDebugMessage(-1, 0.f, FColor::Green, TEXT("Cursor Trace Called"));
	AActor* HitActor = CursorHit.GetActor();
	TScriptInterface<IInteractionInterface> NewInteractionTarget = HitActor;
	LastInteractionTarget = CurrentInteractionTarget;
	CurrentInteractionTarget = NewInteractionTarget;
	// 由于当鼠标点击不同的Actor的时候，需要将上一个Actor的高光取消，同时将现在的高光开启
	if (LastInteractionTarget != CurrentInteractionTarget)
	{
		if (LastInteractionTarget) LastInteractionTarget->UnHighlightActor();
		if (CurrentInteractionTarget) CurrentInteractionTarget->HighlightActor();
	}
}

void ARimSpacePlayerController::RightClick(const FInputActionValue& Value)
{
	AActor* HitActor = CursorHit.GetActor();
	if (HitActor)
	{
		// 尝试转换为 ICommandProvider
		TScriptInterface<ICommandProvider> NewCommandTarget = HitActor;
       
		if (NewCommandTarget)
		{
			// 命中的 Actor 实现了命令接口
			RightClickedCommandTarget = NewCommandTarget;
			SpawnCommandMenu();
		}
		else
		{
			// 命中了 Actor，但它不能提供命令，清除旧的目标并关闭菜单
			RightClickedCommandTarget = nullptr;
			// 确保如果命中的是不可命令的 Actor，菜单也会关闭
			UpdateCommandMenu(); 
		}
	}
	else
	{
		// 没命中任何 Actor，清除目标并关闭菜单
		RightClickedCommandTarget = nullptr;
		UpdateCommandMenu(); 
	}
}

void ARimSpacePlayerController::LeftClick(const FInputActionValue& Value)
{
	// 获取当前 CursorTrace 悬停的目标 Actor
	AActor* CurrentHoverActor = CursorHit.GetActor();
    
	// 检查右键选中的命令目标是否有效
	if (RightClickedCommandTarget)
	{
		// 如果当前悬停的 Actor 不是或与 RightClickedCommandTarget 不相等
		if (!CurrentHoverActor || CurrentHoverActor != RightClickedCommandTarget.GetObject())
		{
			RightClickedCommandTarget = nullptr; // 清除右键选中状态
			UpdateCommandMenu(); // 关闭命令菜单
			GEngine->AddOnScreenDebugMessage(-1, 5.f, FColor::Yellow, TEXT("Left Clicked: Clear RightClickedActor (Command Target)"));
		}
	}
}

void ARimSpacePlayerController::UpdateHoverInfo()
{
	if (CurrentInteractionTarget && HoverInfoWidget)
	{
		IInteractionInterface* InteractionActor = CurrentInteractionTarget.GetInterface();
		UStatusInfoWidget* StatusInfoWidget = Cast<UStatusInfoWidget>(HoverInfoWidget);
		if (InteractionActor && StatusInfoWidget)
		{
			FString ActorName = InteractionActor->GetActorName();
			FString ActorInfo = InteractionActor->GetActorInfo();
			StatusInfoWidget->UpdateInfo(ActorName, ActorInfo);
			FVector2D MousePosition;
			GetMousePosition(MousePosition.X, MousePosition.Y);
			// 设置位置
			HoverInfoWidget->SetPositionInViewport(MousePosition, true);
			HoverInfoWidget->SetVisibility(ESlateVisibility::Visible);
			return;
		}
	}
	if (HoverInfoWidget)
	{
		HoverInfoWidget->SetVisibility(ESlateVisibility::Hidden);
	}
}

void ARimSpacePlayerController::OpenQuantityInputWidget(const FText& Title,int32 CurrentVal, FOnQuantityInputConfirm Callback)
{
	if (CurrentInputWidget)
	{
		CurrentInputWidget->RemoveFromParent();
		CurrentInputWidget = nullptr;
	}
	if (QuantityInputWidgetClass)
	{
		CurrentInputWidget = CreateWidget<UQuantitySelectWidget>(this, QuantityInputWidgetClass);
		if (CurrentInputWidget)
		{
			FOnQuantityInputConfirm WrappedCallback = [this, Callback](int val)
			{
				Callback(val);
				this->CloseQuantityInputWidget();
			};
			CurrentInputWidget->Setup(Title, CurrentVal, WrappedCallback);
			// 显示在屏幕中央
			CurrentInputWidget->AddToViewport(100);

			FInputModeUIOnly InputMode;
			InputMode.SetWidgetToFocus(CurrentInputWidget->TakeWidget());
			SetInputMode(InputMode);
			bShowMouseCursor = true;
		}
	}
}

void ARimSpacePlayerController::CloseQuantityInputWidget()
{
		FInputModeGameAndUI InputMode;
		SetInputMode(InputMode);
		bShowMouseCursor = true;
		if (CurrentInputWidget)
		{
			CurrentInputWidget = nullptr;
		}
}

void ARimSpacePlayerController::SpawnCommandMenu()
{
	if (CommandMenuWidget)
	{
		CommandMenuWidget->RemoveFromParent();
		CommandMenuWidget = nullptr;
	}
	if (CommandMenuWidgetClass && RightClickedCommandTarget)
	{
		CommandMenuWidget = CreateWidget<UCommandMenuWidget>(this, CommandMenuWidgetClass);
		if (CommandMenuWidget)
		{
			CommandMenuWidget->InitializeMenu(RightClickedCommandTarget);
			CommandMenuWidget->AddToViewport();
			FVector2D MousePosition;
			GetMousePosition(MousePosition.X, MousePosition.Y);
			CommandMenuWidget->SetPositionInViewport(MousePosition, true);
		}
	}
}

void ARimSpacePlayerController::UpdateCommandMenu()
{
	if (CommandMenuWidget && !RightClickedCommandTarget)
	{
		CommandMenuWidget->RemoveFromParent();
		CommandMenuWidget = nullptr;
	}
}
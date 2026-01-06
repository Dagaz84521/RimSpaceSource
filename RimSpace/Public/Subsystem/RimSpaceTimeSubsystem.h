// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "RimSpaceTimeSubsystem.generated.h"

/**
 * 
 */

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnMinutePassed, int32, NewMinute);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnHourPassed, int32, NewHour);

UCLASS()
class RIMSPACE_API URimSpaceTimeSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	bool IsTickable() const override { return true; }
	virtual TStatId GetStatId() const override;

	UFUNCTION(BlueprintCallable)
	void StartTimeSystem(int32 StartDay = 1, int32 StartHour = 6, int32 StartMinute = 0);

	UFUNCTION(BlueprintCallable)
	void StopTimeSystem();
	UFUNCTION(BlueprintCallable)
	void ResumeTimeSystem();

	// 倍速控制（1x，2x等）
	UFUNCTION(BlueprintCallable)
	void SetTimeScale(float NewScale);

	float GetTimeScale() const { return TimeScale; }

	// 游戏时间数值
	int32 TotalTicks = 0;
	int32 Minute = 0;
	int32 Hour = 0;
	int32 Day = 1;
	UFUNCTION()
	FString GetFormattedTime() const;

	// 事件广播
	UPROPERTY(BlueprintAssignable)
	FOnMinutePassed OnMinutePassed;

	UPROPERTY(BlueprintAssignable)
	FOnHourPassed OnHourPassed;

private:
	float TimeAccumulator = 0.0f;
	float GameTickLength = 1.0f / 60.0f;   // RimWorld: 60 GameTick = 1 minute
	float TimeScale = 2.0f;
	bool bIsTimeRunning = false;
};

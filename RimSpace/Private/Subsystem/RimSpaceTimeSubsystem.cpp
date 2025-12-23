// Fill out your copyright notice in the Description page of Project Settings.


#include "Subsystem/RimSpaceTimeSubsystem.h"

void URimSpaceTimeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
}

void URimSpaceTimeSubsystem::Deinitialize()
{
	Super::Deinitialize();
}

void URimSpaceTimeSubsystem::Tick(float DeltaTime)
{
	float GameDelta = DeltaTime * TimeScale;
	TimeAccumulator += GameDelta;

	while (TimeAccumulator >= GameTickLength)
	{
		TimeAccumulator -= GameTickLength;
		TotalTicks++;

		// 60 Tick = 1 minute
		if (TotalTicks % 60 == 0)
		{
			Minute++;
			OnMinutePassed.Broadcast(Minute);

			if (Minute >= 60)
			{
				Minute = 0;
				Hour++;
				OnHourPassed.Broadcast(Hour);

				if (Hour >= 24)
				{
					Hour = 0;
					Day++;
				}
			}
		}
		if (GEngine)
		{
			FString Msg = FString::Printf(TEXT("Day %d  %02d:%02d"), Day, Hour, Minute);
			GEngine->AddOnScreenDebugMessage(1, 1.0f, FColor::Green, Msg);
		}
	}
}

TStatId URimSpaceTimeSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(URimSpaceTimeSubsystem, STATGROUP_Tickables);
}

void URimSpaceTimeSubsystem::SetTimeScale(float NewScale)
{
	TimeScale = NewScale;
}
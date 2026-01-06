// Fill out your copyright notice in the Description page of Project Settings.
#include "Subsystem/ActorManagerSubsystem.h"
#include "Actor/RimSpaceActorBase.h"

void UActorManagerSubsystem::RegisterActorWithName(const FName& Name, ARimSpaceActorBase* Actor)
{
	if (RegisteredActors.Contains(Name))
	{
		UE_LOG(LogTemp, Warning, TEXT("Actor with name %s is already registered."), *Name.ToString());
		return;
	}
	RegisteredActors.Add(Name, Actor);
	UE_LOG(LogTemp, Log, TEXT("Registered actor with name %s."), *Name.ToString());
}

ARimSpaceActorBase* UActorManagerSubsystem::GetActorByName(const FName& Name)
{
	return RegisteredActors.Contains(Name) ? RegisteredActors[Name] : nullptr;
}

TSharedPtr<FJsonObject> UActorManagerSubsystem::GetActorsDataAsJson() const
{
	TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject());
	TArray<TSharedPtr<FJsonValue>> ActorsJsonArray;

	for (const auto& Pair : RegisteredActors)
	{
		ARimSpaceActorBase* Actor = Pair.Value;
		if (Actor)
		{
			TSharedPtr<FJsonObject> ActorJson = Actor->GetActorDataAsJson();
			ActorsJsonArray.Add(MakeShareable(new FJsonValueObject(ActorJson)));
		}
	}

	JsonObject->SetArrayField("Actors", ActorsJsonArray);
	return JsonObject;
}

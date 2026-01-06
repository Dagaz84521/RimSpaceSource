// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/Bed.h"

ABed::ABed()
{
	ActorType = EInteractionType::EAT_Bed;
}

FString ABed::GetActorInfo() const
{
	return FString("This is a bed actor.");
}

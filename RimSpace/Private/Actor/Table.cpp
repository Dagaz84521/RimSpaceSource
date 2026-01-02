// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/Table.h"

ATable::ATable()
{
	ActorType = EInteractionType::EAT_Table;
	ActorName = FName(TEXT("桌子"));
}

FString ATable::GetActorInfo() const
{
	return FString::Printf(TEXT("一张桌子。\n在拥有食物时，可以在此处进食。"));
}

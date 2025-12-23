// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/SewingMachine.h"

TArray<FText> ASewingMachine::GetCommandList() const
{
	TArray<FText> CommandList;
	if (TaskRemainCount > 0)
	{
		CommandList.Add(FText::FromString("取消任务"));
		CommandList.Add(FText::FromString("修改任务"));
	}
	else
	{
		CommandList.Add(FText::FromString("建立任务"));
	}
	return CommandList;
}

void ASewingMachine::ExecuteCommand(const FText& Command)
{
}

FString ASewingMachine::GetActorInfo() const
{
	FString Info;
	Info += FString::Printf(TEXT("剩余任务量: %d\n"), TaskRemainCount);
	Info += FString::Printf(TEXT("原料数量: %d\n"), IngredientsCount);
	Info += FString::Printf(TEXT("产品存储: %d / %d\n"), ProductStorageCount, ProductStorageMaxCount);
	return Info;
}

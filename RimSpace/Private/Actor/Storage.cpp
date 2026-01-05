// Fill out your copyright notice in the Description page of Project Settings.


#include "Actor/Storage.h"

#include <Windows.Data.Text.h>

#include "Component/InventoryComponent.h"

AStorage::AStorage()
{
	InventoryComponent = CreateDefaultSubobject<UInventoryComponent>(TEXT("InputInventory"));
}

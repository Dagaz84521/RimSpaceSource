// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Http.h"
#include "Data/AgentCommand.h"
#include "LLMCommunicationSubsystem.generated.h"

// 解析LLM服务器返回的JSON结构
USTRUCT()
struct FLLMResponse
{
	GENERATED_BODY()
	UPROPERTY()
	FString CharacterName;
	UPROPERTY()
	FString CommandType;
	UPROPERTY()
	FString TargetName;
	UPROPERTY()
	int32 ParamID;
	UPROPERTY()
	int32 Count;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnServerConnectionStatusChanged, bool, bSuccess, FString, Message);

/**
 * 
 */
UCLASS()
class RIMSPACE_API ULLMCommunicationSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	UFUNCTION(BlueprintCallable, Category = "LLM")
	void SendGameStateToLLM();
	UFUNCTION(BlueprintCallable, Category = "LLM")
	void RequestNextAgentCommand(FName CharacterName);
	UFUNCTION(BlueprintCallable, Category = "LLM")
	void CheckServerConnection();
	UPROPERTY(BlueprintAssignable, Category = "LLM")
	FOnServerConnectionStatusChanged OnConnectionStatusChanged;
	
private:
	void OnCheckConnectionComplete(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnCommandResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	void OnResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful);
	
	FTimerHandle AutoUpdateTimerHandle;
	EAgentCommandType StringToCommandType(const FString& CmdStr);
	FString ServerURL = TEXT("http://localhost:5000");
	double RequestStartTime = 0.0;
	
};

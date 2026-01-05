// Fill out your copyright notice in the Description page of Project Settings.


#include "Subsystem/LLMCommunicationSubsystem.h"

void ULLMCommunicationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
}

void ULLMCommunicationSubsystem::SendGameStateToLLM()
{
}

void ULLMCommunicationSubsystem::CheckServerConnection()
{
	FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
	// 假设服务器有一个 /health 或 /ping 接口，或者直接请求根路径
	Request->SetURL(ServerURL + "/health"); 
	Request->SetVerb("GET");
	Request->SetTimeout(5.0f); // 设置超时，避免卡住太久
	Request->OnProcessRequestComplete().BindUObject(this, &ULLMCommunicationSubsystem::OnCheckConnectionComplete);
	Request->ProcessRequest();

	UE_LOG(LogTemp, Log, TEXT("Attempting to connect to LLM Server..."));
}

void ULLMCommunicationSubsystem::OnCheckConnectionComplete(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bWasSuccessful)
{
	if (bWasSuccessful && Response.IsValid())
	{
		// 如果服务器返回 200 OK，视为成功
		if (Response->GetResponseCode() == 200)
		{
			OnConnectionStatusChanged.Broadcast(true, TEXT("服务器连接正常"));
			UE_LOG(LogTemp, Log, TEXT("Server Connected!"));
			return;
		}
	}

	// 失败情况
	OnConnectionStatusChanged.Broadcast(false, TEXT("无法连接到服务器"));
	UE_LOG(LogTemp, Warning, TEXT("Server Connection Failed."));
}

void ULLMCommunicationSubsystem::OnResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response,
	bool bWasSuccessful)
{
}

EAgentCommandType ULLMCommunicationSubsystem::StringToCommandType(const FString& CmdStr)
{
	return EAgentCommandType::None;
}

// Fill out your copyright notice in the Description page of Project Settings.


#include "Subsystem/LLMCommunicationSubsystem.h"

#include "JsonObjectConverter.h"
#include "GameInstance/RimSpaceGameInstance.h"
#include "Subsystem/ActorManagerSubsystem.h"
#include "Subsystem/CharacterManagerSubsystem.h"
#include "Subsystem/RimSpaceTimeSubsystem.h"

void ULLMCommunicationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
}

void ULLMCommunicationSubsystem::SendGameStateToLLM()
{
	TSharedPtr<FJsonObject> RootJson = MakeShareable(new FJsonObject());
	URimSpaceTimeSubsystem* TimeSubsystem = GetGameInstance()->GetSubsystem<URimSpaceTimeSubsystem>();
	if (TimeSubsystem)
	{
		FString FormattedTime = TimeSubsystem->GetFormattedTime();
		RootJson->SetStringField("GameTime", FormattedTime);
	}
	UActorManagerSubsystem* ActorManager = GetWorld()->GetSubsystem<UActorManagerSubsystem>();
	if (ActorManager)
	{
		RootJson->SetObjectField("Actors", ActorManager->GetActorsDataAsJson());
	}

	UCharacterManagerSubsystem* CharacterManager = GetWorld()->GetSubsystem<UCharacterManagerSubsystem>();
	if (CharacterManager)
	{
		RootJson->SetObjectField("Characters", CharacterManager->GetCharactersDataAsJson());
	}

	// 序列化为字符串
	FString RequestBody;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
	FJsonSerializer::Serialize(RootJson.ToSharedRef(), Writer);
	// 创建HTTP请求
	FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(ServerURL + "/UpdateGameState");
	Request->SetVerb("POST");
	Request->SetHeader("Content-Type", "application/json");
	Request->SetContentAsString(RequestBody);
	Request->OnProcessRequestComplete().BindUObject(this, &ULLMCommunicationSubsystem::OnResponseReceived);
	Request->ProcessRequest();

	UE_LOG(LogTemp, Warning, TEXT("Process response successfully"));
}

void ULLMCommunicationSubsystem::RequestNextAgentCommand(FName CharacterName)
{
	// 1. 暂停游戏时间 (保持上一轮的逻辑)
    URimSpaceTimeSubsystem* TimeSubsystem = GetGameInstance()->GetSubsystem<URimSpaceTimeSubsystem>();
	
    // 2. 构建请求数据 (这是修改的重点)
    TSharedPtr<FJsonObject> RootJson = MakeShareable(new FJsonObject());
    
    // A. 基础请求信息
    RootJson->SetStringField("RequestType", "GetInstruction");
    RootJson->SetStringField("TargetAgent", CharacterName.ToString());

    // B. 收集世界状态 (把之前的 SendGameStateToLLM 逻辑搬过来)
    
    // B.1 时间信息
    if (TimeSubsystem)
    {
        RootJson->SetStringField("GameTime", TimeSubsystem->GetFormattedTime());
    }

    // B.2 环境中所有 Actor 的信息 (灶台、工作台、仓库等)
    UActorManagerSubsystem* ActorManager = GetWorld()->GetSubsystem<UActorManagerSubsystem>();
    if (ActorManager)
    {
        // 假设 ActorManager 已经实现了 GetActorsDataAsJson
        RootJson->SetObjectField("Environment", ActorManager->GetActorsDataAsJson());
    }

    // B.3 所有角色的信息 (尤其是为了知道其他人在干嘛，避免抢同一个工作台)
    UCharacterManagerSubsystem* CharacterManager = GetWorld()->GetSubsystem<UCharacterManagerSubsystem>();
    if (CharacterManager)
    {
        // 假设 CharacterManager 已经实现了 GetCharactersDataAsJson
        RootJson->SetObjectField("Characters", CharacterManager->GetCharactersDataAsJson());
    }

    // B.4 物品和任务配方信息（让 LLM 知道有哪些物品和可用的配方）
    URimSpaceGameInstance* GI = Cast<URimSpaceGameInstance>(GetGameInstance());
    if (GI)
    {
        RootJson->SetObjectField("ItemDatabase", GI->GetAllItemsDataAsJson());
        RootJson->SetObjectField("TaskRecipes", GI->GetAllTasksDataAsJson());
    }

    // 3. 序列化并发送
    FString RequestBody;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
    FJsonSerializer::Serialize(RootJson.ToSharedRef(), Writer);

    FHttpRequestRef Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(ServerURL + "/GetInstruction"); // 统一使用获取指令的接口
    Request->SetVerb("POST");
    Request->SetHeader("Content-Type", "application/json");
    Request->SetContentAsString(RequestBody);
    Request->OnProcessRequestComplete().BindUObject(this, &ULLMCommunicationSubsystem::OnCommandResponseReceived);
    Request->ProcessRequest();

    UE_LOG(LogTemp, Log, TEXT("Requesting command for %s with Full World State. Game Paused."), *CharacterName.ToString());
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

void ULLMCommunicationSubsystem::OnCommandResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response,
	bool bWasSuccessful)
{
	
	if (bWasSuccessful && Response.IsValid() && Response->GetResponseCode() == 200)
	{
		FString ResponseStr = Response->GetContentAsString();
		UE_LOG(LogTemp, Log, TEXT("Received Command: %s"), *ResponseStr);

		// 解析指令
		FAgentCommand NewCommand;
		// 假设服务器返回的 JSON 符合 FAgentCommand 的结构
		if (FJsonObjectConverter::JsonObjectStringToUStruct(ResponseStr, &NewCommand, 0, 0))
		{
			// 4. 执行指令
			UCharacterManagerSubsystem* CharacterManager = GetWorld()->GetSubsystem<UCharacterManagerSubsystem>();
			if (CharacterManager)
			{
				CharacterManager->ExecuteCommand(NewCommand);
			}
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("Failed to parse command JSON."));
		}
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Failed to get command from server."));
	}
}

void ULLMCommunicationSubsystem::OnResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response,
                                                    bool bWasSuccessful)
{
}

EAgentCommandType ULLMCommunicationSubsystem::StringToCommandType(const FString& CmdStr)
{
	return EAgentCommandType::None;
}

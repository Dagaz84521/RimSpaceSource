# RimSpace Actor / Subsystem / Character Class Diagram

## Thesis Version

```mermaid
classDiagram
    direction TB

    class ARimSpaceActorBase {
        可交互设施基类
    }

    class ABed
    class ATable
    class AStorage
    class AStove
    class AWorkStation
    class ACultivateChamber

    class ARimSpaceCharacterBase {
        智能体状态
        移动行为
        物品操作
        设施使用
    }

    class UActorManagerSubsystem {
        设施注册表
        设施状态收集
    }

    class UCharacterManagerSubsystem {
        角色注册表
        指令分发
    }

    class URimSpaceTimeSubsystem {
        游戏时间
        分钟/小时事件
    }

    class ULLMCommunicationSubsystem {
        世界状态上传
        智能体指令请求
    }

    class UInventoryComponent {
        物品存储
    }

    ARimSpaceActorBase <|-- ABed
    ARimSpaceActorBase <|-- ATable
    ARimSpaceActorBase <|-- AStorage
    ARimSpaceActorBase <|-- AStove
    ARimSpaceActorBase <|-- AWorkStation
    ARimSpaceActorBase <|-- ACultivateChamber

    ARimSpaceActorBase o-- UInventoryComponent : 设施库存
    ARimSpaceCharacterBase o-- UInventoryComponent : 携带物品

    UActorManagerSubsystem o-- ARimSpaceActorBase : 管理
    UCharacterManagerSubsystem o-- ARimSpaceCharacterBase : 管理

    URimSpaceTimeSubsystem ..> ARimSpaceActorBase : 时间事件更新
    URimSpaceTimeSubsystem ..> ARimSpaceCharacterBase : 时间事件更新

    ULLMCommunicationSubsystem ..> UActorManagerSubsystem : 收集设施状态
    ULLMCommunicationSubsystem ..> UCharacterManagerSubsystem : 收集角色状态
    ULLMCommunicationSubsystem ..> URimSpaceTimeSubsystem : 暂停/恢复时间
    UCharacterManagerSubsystem ..> ARimSpaceCharacterBase : 分发指令

    ARimSpaceCharacterBase --> ARimSpaceActorBase : 移动/使用
    ARimSpaceCharacterBase --> AStove : 分配工人
    ARimSpaceCharacterBase --> AWorkStation : 分配工人
    ARimSpaceCharacterBase --> ACultivateChamber : 分配工人
```

## Detailed Version

```mermaid
classDiagram
    direction LR

    class AActor
    class ACharacter
    class UWorldSubsystem
    class UGameInstanceSubsystem
    class FTickableGameObject
    class UActorComponent

    class IInteractionInterface {
        <<interface>>
        +HighlightActor()
        +UnHighlightActor()
        +GetActorName() FString
        +GetActorInfo() FString
        +GetActorDataAsJson() JsonObject
    }

    class ITimeAffectable {
        <<interface>>
        +UpdateEachMinute(int32)
        +UpdateEachHour(int32)
    }

    class ICommandProvider {
        <<interface>>
        +GetCommandList() TArray~FText~
        +ExecuteCommand(FText)
    }

    class UInventoryComponent {
        +AddItem(FItemStack) bool
        +RemoveItem(FItemStack) bool
        +GetItemCount(int32) int32
        +GetInventoryDataAsJson() JsonObject
        -Items TArray~FItemStack~
        -TotalSpace int32
        -UsedSpace int32
    }

    class ARimSpaceActorBase {
        +Tick(float)
        +GetInteractionPoint() USceneComponent*
        +GetMeshComponent() UStaticMeshComponent*
        +GetInteractionType() EInteractionType
        +GetActorDataAsJson() JsonObject
        #MeshComponent UStaticMeshComponent*
        #InteractionPoint USceneComponent
        #ActorName FName
        #ActorType EInteractionType
    }

    class ABed {
        +GetActorInfo() FString
    }

    class ATable {
        +GetActorInfo() FString
    }

    class AStorage {
        #InventoryComponent UInventoryComponent
    }

    class AStove {
        +GetCommandList() TArray~FText~
        +ExecuteCommand(FText)
        +SetWorker(ARimSpaceCharacterBase*, int32)
        +AddTask(int32, int32)
        +UpdateEachMinute(int32)
        -TaskList TMap~int32,int32~
        -CurrentWorker ARimSpaceCharacterBase*
        -CurrentTaskID int32
        -CurrentWorkProgress int32
    }

    class AWorkStation {
        +GetCommandList() TArray~FText~
        +ExecuteCommand(FText)
        +SetWorker(ARimSpaceCharacterBase*, int32)
        +AddTask(int32, int32)
        +UpdateEachMinute(int32)
        -TaskList TMap~int32,int32~
        -CurrentWorker ARimSpaceCharacterBase*
        -CurrentTaskID int32
        -CurrentWorkProgress int32
    }

    class ACultivateChamber {
        +GetCommandList() TArray~FText~
        +ExecuteCommand(FText)
        +SetWorker(ARimSpaceCharacterBase*)
        +SetPlantedCrop(int32)
        +UpdateEachMinute(int32)
        +UpdateEachHour(int32)
        -CurrentPhase ECultivatePhase
        -CurrentWorker ARimSpaceCharacterBase*
        -CurrentWorkProgress int32
        -GrowthProgress int32
    }

    class ARimSpaceCharacterBase {
        +InitialCharacter(Stats, Skills, FName)
        +ExecuteAgentCommand(FAgentCommand) bool
        +GetActionState() ECharacterActionState
        +SetActionState(ECharacterActionState)
        +FinishCommandAndRequestNext()
        #MoveTo(FName) bool
        #TakeItem(int32, int32) bool
        #PutItem(int32, int32) bool
        #UseFacility(int32) bool
        #CharacterName FName
        #CharacterStats FRimSpaceCharacterStats
        #CharacterSkills FRimSpaceCharacterSkills
        #CurrentActionState ECharacterActionState
        #CarriedItems UInventoryComponent*
        #CurrentPlace ARimSpaceActorBase*
        #TargetPlace ARimSpaceActorBase*
        #AssignedBed ABed*
    }

    class UActorManagerSubsystem {
        +RegisterActorWithName(FName, ARimSpaceActorBase*)
        +GetActorByName(FName) ARimSpaceActorBase*
        +GetActorsDataAsJson() JsonObject
        -RegisteredActors TMap~FName,ARimSpaceActorBase~
    }

    class UCharacterManagerSubsystem {
        +RegisterCharacterWithName(FName, ARimSpaceCharacterBase*)
        +GetCharacterByName(FName) ARimSpaceCharacterBase*
        +ExecuteCommand(FAgentCommand) bool
        +GetCharactersDataAsJson() JsonObject
        -RegisteredCharacters TMap~FName,ARimSpaceCharacterBase~
    }

    class URimSpaceTimeSubsystem {
        +StartTimeSystem(int32, int32, int32)
        +StopTimeSystem()
        +ResumeTimeSystem()
        +SetTimeScale(float)
        +GetFormattedTime() FString
        +OnMinutePassed FOnMinutePassed
        +OnHourPassed FOnHourPassed
        -TimeScale float
        -bIsTimeRunning bool
    }

    class ULLMCommunicationSubsystem {
        +SendGameStateToLLM()
        +RequestNextAgentCommand(FName)
        +CheckServerConnection()
        -OnCommandResponseReceived(...)
        -PendingRequestCount int32
        -ServerURL FString
    }

    AActor <|-- ARimSpaceActorBase
    ACharacter <|-- ARimSpaceCharacterBase
    UActorComponent <|-- UInventoryComponent
    UWorldSubsystem <|-- UActorManagerSubsystem
    UWorldSubsystem <|-- UCharacterManagerSubsystem
    UGameInstanceSubsystem <|-- URimSpaceTimeSubsystem
    FTickableGameObject <|.. URimSpaceTimeSubsystem
    UGameInstanceSubsystem <|-- ULLMCommunicationSubsystem

    IInteractionInterface <|.. ARimSpaceActorBase
    ITimeAffectable <|.. ARimSpaceActorBase
    IInteractionInterface <|.. ARimSpaceCharacterBase
    ITimeAffectable <|.. ARimSpaceCharacterBase
    ICommandProvider <|.. AStove
    ICommandProvider <|.. AWorkStation
    ICommandProvider <|.. ACultivateChamber

    ARimSpaceActorBase <|-- ABed
    ARimSpaceActorBase <|-- ATable
    ARimSpaceActorBase <|-- AStorage
    ARimSpaceActorBase <|-- AStove
    ARimSpaceActorBase <|-- AWorkStation
    ARimSpaceActorBase <|-- ACultivateChamber

    ARimSpaceActorBase *-- UInventoryComponent : optional component
    ARimSpaceCharacterBase *-- UInventoryComponent : CarriedItems
    ARimSpaceCharacterBase --> ARimSpaceActorBase : CurrentPlace / TargetPlace
    ARimSpaceCharacterBase --> ABed : AssignedBed
    AStove --> ARimSpaceCharacterBase : CurrentWorker
    AWorkStation --> ARimSpaceCharacterBase : CurrentWorker
    ACultivateChamber --> ARimSpaceCharacterBase : CurrentWorker

    UActorManagerSubsystem o-- ARimSpaceActorBase : RegisteredActors
    UCharacterManagerSubsystem o-- ARimSpaceCharacterBase : RegisteredCharacters
    URimSpaceTimeSubsystem ..> ITimeAffectable : OnMinute/HourPassed
    ULLMCommunicationSubsystem ..> UActorManagerSubsystem : collect actor state
    ULLMCommunicationSubsystem ..> UCharacterManagerSubsystem : execute command
    ULLMCommunicationSubsystem ..> URimSpaceTimeSubsystem : pause/resume time
    ARimSpaceCharacterBase ..> UActorManagerSubsystem : MoveTo target lookup
    ARimSpaceCharacterBase ..> ULLMCommunicationSubsystem : request next command
    ARimSpaceCharacterBase ..> AStove : UseFacility
    ARimSpaceCharacterBase ..> AWorkStation : UseFacility
    ARimSpaceCharacterBase ..> ACultivateChamber : UseFacility
```

## Notes

- `ARimSpaceActorBase` is the common base for placeable interactive actors. It registers itself in `UActorManagerSubsystem` during `BeginPlay` and subscribes to `URimSpaceTimeSubsystem` minute/hour events.
- `ARimSpaceCharacterBase` registers itself in `UCharacterManagerSubsystem`, also subscribes to time events, and uses `UActorManagerSubsystem` to resolve movement targets by name.
- `AStove`, `AWorkStation`, and `ACultivateChamber` are the main worker-driven facilities. They keep a `CurrentWorker` reference and advance work from time updates.
- `ULLMCommunicationSubsystem` gathers time, actor, and character state, pauses/resumes game time while waiting for LLM responses, and sends returned `FAgentCommand` objects into `UCharacterManagerSubsystem`.

## LLMServer 模块关系图

```mermaid
classDiagram
    direction LR

    class FlaskAPI {
        <<服务入口>>
        llm_server.py
        更新游戏状态接口
        获取智能体指令接口
        游戏状态缓存
        智能体实例表
    }

    class Perceiver {
        <<感知模块>>
        perceiver.py
        +perceive_environment_tasks()
        扫描设施状态
        生成隐式任务
    }

    class Blackboard {
        <<黑板模块>>
        blackboard.py
        任务列表
        进度计数器
        +post_task()
        +update()
        +get_executable_tasks()
    }

    class BlackboardTask {
        <<任务数据>>
        任务ID
        任务描述
        优先级
        所需技能
        前置条件
    }

    class Goal {
        <<目标条件>>
        目标对象
        状态类型
        状态键
        比较操作符
        目标值
        +is_satisfied()
    }

    class RimSpaceAgent {
        <<智能体决策模块>>
        agent_manager.py
        +make_decision()
        +update_state()
        +generate_observation_text()
        动作队列
        反馈缓存
        欲望状态
    }

    class LLMClient {
        <<大语言模型接口>>
        llm_client.py
        +query()
        +parse_json_response()
    }

    namespace planner.py {
        class TaskPlanner {
            <<任务规划器>>
            +analyze_and_post_crafting_task()
            +ensure_min_stock()
            -_build_supply_chain()
        }

        class BehaviorPlanner {
            <<行为规划器>>
            +generate_plan()
            +_plan_eat()
            +_plan_craft()
            +_plan_transport()
            +_plan_wait()
        }
    }

    class GameDataManager {
        <<游戏数据模块>>
        game_data_manager.py
        物品数据表
        配方任务表
        产物配方索引
        物品名称索引
    }

    class UnrealClient {
        <<外部系统>>
        RimSpace客户端
    }

    UnrealClient ..> FlaskAPI : 发送世界状态 / 请求角色指令

    FlaskAPI *-- Blackboard : 全局黑板实例
    FlaskAPI *-- TaskPlanner : 全局任务规划器
    FlaskAPI o-- RimSpaceAgent : 按角色维护智能体
    FlaskAPI ..> Perceiver : 触发环境感知

    Perceiver ..> Blackboard : 发布感知任务
    Perceiver ..> TaskPlanner : 委托制造/库存需求拆解

    Blackboard *-- BlackboardTask : 存储任务
    BlackboardTask *-- Goal : 目标与前置条件

    RimSpaceAgent *-- LLMClient : 持有LLM客户端
    RimSpaceAgent *-- BehaviorPlanner : 持有行为规划器
    RimSpaceAgent --> Blackboard : 读取可执行任务
    RimSpaceAgent ..> LLMClient : 请求高层决策
    RimSpaceAgent ..> BehaviorPlanner : 生成低层动作序列

    TaskPlanner --> Blackboard : 发布供应链任务
    BehaviorPlanner --> Blackboard : 资源不足时发布补充任务
    TaskPlanner *-- GameDataManager : 读取物品与配方数据
    BehaviorPlanner *-- GameDataManager : 读取物品与配方数据
    RimSpaceAgent ..> GameDataManager : 查询配方提示/物品ID
```

## LLMServer 运行时序图

```mermaid
sequenceDiagram
    participant UE as RimSpace客户端
    participant S as llm_server.py
    participant P as 感知模块
    participant BB as 黑板
    participant GP as 任务规划器
    participant A as RimSpaceAgent
    participant L as LLM
    participant AP as 行为规划器

    UE->>S: POST /GetInstruction(游戏状态, 目标角色)
    S->>BB: 更新黑板任务状态
    S->>P: 感知环境任务
    P->>BB: 发布种植/收获任务
    P->>GP: 分析制造与库存需求
    GP->>BB: 发布主任务与供应链任务
    S->>A: 请求角色决策
    A->>BB: 获取可执行任务
    BB-->>A: 返回过滤后的任务
    A->>L: 发送提示词与环境观察
    L-->>A: 返回高层决策JSON
    A->>AP: 生成动作计划
    AP-->>A: 返回动作队列或失败反馈
    AP->>BB: 资源不足时发布补充任务
    A-->>S: 返回下一条低层指令
    S-->>UE: 返回指令JSON
```

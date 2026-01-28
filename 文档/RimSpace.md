# RimSpace 项目文档

## 📋 项目概述

**RimSpace** 是一个基于Unreal Engine开发的太空殖民地模拟游戏，融合了**大语言模型（LLM）驱动的智能体系统**。项目的核心创新在于使用LLM为游戏角色提供智能决策，让NPC能够像真人玩家一样思考、规划和执行复杂任务。

### 核心特性
- 🤖 **LLM驱动的AI系统**：角色由大语言模型控制，能够理解上下文、规划任务链、协作完成目标
- 🏗️ **生产链模拟**：完整的资源采集→加工→制造→交易经济系统
- 🎭 **角色专业化**：Farmer（农民）、Crafter（手艺人）、Chef（厨师）各司其职
- 🔄 **动态世界状态**：实时同步游戏状态到LLM服务器，AI基于完整信息做决策
- 🧠 **欲望驱动架构（D2A）**：模拟饥饿、疲劳、责任感等心理状态影响决策
- 📋 **共享任务黑板**：多智能体通过黑板系统协作，可发布任务请求（如"需要食物"、"搬运物品"）
- 🎯 **计划分解机制**：LLM生成高层决策后自动分解为具体指令序列，节省token消耗并提升执行质量

---

## 🎮 游戏机制

### 角色系统
游戏中有三种专业角色，每个角色有独特的技能和职责：

| 角色 | 技能 | 主要工作 | 核心设施 |
|------|------|----------|----------|
| **Farmer** | CanFarm | 种植Cotton（棉花）、Corn（玉米） | CultivateChamber（培养舱） |
| **Crafter** | CanCraft | 制作Thread（棉线）、Cloth（布料）、Coat（衣服） | WorkStation（工作台） |
| **Chef** | CanCook | 烹饪Meal（套餐） | Stove（炉灶） |

### 生产链设计

```
Farmer 种植
├─ Cotton（棉花）───→ Crafter 加工
│   ├─ Thread（棉线）─┐
│   ├─ Cloth（布料）──┼─→ Coat（衣服）[商品]
│   └─ [5个Cotton]    │
│                      │
└─ Corn（玉米）────→ Chef 烹饪 → Meal（套餐）[唯一食物来源]
    [5个Corn]
```

### 资源与物品

参考文件：[Item.json](../Data/Item.json)

| 物品ID | 名称 | 类型 | 用途 |
|--------|------|------|------|
| 1001 | Cotton（棉花） | 原料 | 制作Thread和Cloth |
| 1002 | Corn（玉米） | 原料 | 烹饪Meal |
| 2001 | Thread（棉线） | 材料 | 制作Coat |
| 2002 | Cloth（布料） | 材料 | 制作Coat |
| 2003 | Meal（套餐） | 食物 | 恢复饥饿值（营养值80） |
| 3001 | Coat（衣服） | 商品 | 高价值交易品 |

### 任务与配方

参考文件：[Task.json](../Data/Task.json)

任务系统定义了所有生产配方，包括：
- **原料需求**：需要哪些材料、数量多少
- **工作量**：完成任务需要的工作时长
- **所需设施**：必须在特定设施才能执行
- **技能要求**：角色必须具备相应技能

示例：制作Coat需要2个Cloth + 3个Thread，工作量250，在WorkStation完成。

---

## 🏗️ 技术架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│           Unreal Engine 游戏客户端                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Character    │  │  Actor       │  │ AIController │ │
│  │  - Farmer    │  │  - Storage   │  │  - HTTP请求  │ │
│  │  - Crafter   │  │  - WorkStation│  │  - 指令执行  │ │
│  │  - Chef      │  │  - Stove     │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP JSON
                          │ (状态上传 + 指令请求)
┌─────────────────────────▼───────────────────────────────┐
│         Python LLM Server (Flask)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ llm_server.py│  │agent_manager │  │ llm_client   │ │
│  │  - Flask路由 │  │  - 状态映射  │  │  - API调用   │ │
│  │  - 数据解析  │  │  - D2A欲望   │  │  - JSON解析  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                          │                              │
│                  ┌───────▼──────────┐                   │
│                  │  Profile文档集    │                   │
│                  │  - Farmer角色档案 │                   │
│                  │  - Crafter角色档案│                   │
│                  │  - Chef角色档案   │                   │
│                  └──────────────────┘                   │
└─────────────────────────┬───────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │ 大语言模型  │
                    │ (GPT/Claude)│
                    └────────────┘
```

### 通信流程

1. **请求指令**：角色需要新指令时，通过`POST /GetInstruction`发送当前状态
2. **LLM决策**：服务器将状态映射为自然语言prompt，调用LLM生成决策
3. **指令返回**：解析LLM输出，转换为游戏可执行的指令（Move/Take/Put/Use/Wait）
4. **执行反馈**：游戏执行指令后更新状态，进入下一轮循环

### 关键文件结构

```
RimSpace/Source/
├── RimSpace/                      # Unreal C++ 游戏代码
│   ├── Public/
│   │   ├── Character/             # 角色类
│   │   ├── Controller/            # AI控制器
│   │   ├── Actor/                 # 交互物体（设施）
│   │   └── Data/                  # 数据结构
│   └── Private/                   # 实现代码
│
├── LLMServerNew/                  # Python LLM服务器
│   ├── llm_server.py              # Flask服务器主文件
│   ├── agent_manager.py           # Agent决策管理器
│   ├── llm_client.py              # LLM API客户端
│   └── config.py                  # 配置文件（提示词模板、阈值）
│
├── Data/                          # 游戏数据配置
│   ├── Item.json                  # 物品定义
│   ├── Task.json                  # 任务配方
│   ├── CharacterProfiles.json     # 角色基础信息
│   └── InitGameData.json          # 初始游戏状态
│
├── 文档/                          # 角色档案（Prompt工程）
│   ├── profile_farmer.txt         # Farmer角色提示词
│   ├── profile_crafter.txt        # Crafter角色提示词
│   └── profile_chef.txt           # Chef角色提示词
│
└── Log/                           # 运行日志（用于调试）
    ├── ServerReceive/             # 接收到的请求
    └── Round_XXX/                 # 每回合的决策记录
```

---

## 🧠 LLM Agent系统详解

### D2A欲望驱动架构

系统实现了一个简化版的"Desire to Action"（欲望驱动）模型：

```python
desires = {
    "hunger": 0-100,      # 饥饿值，越高越饿
    "exhaustion": 0-100,  # 疲劳值，越高越累
    "duty": 0-100         # 责任感，取决于任务黑板上的待办任务
}
```

**决策逻辑**：
1. 如果`hunger`或`exhaustion` > 80 → 生存优先（吃饭/睡觉）
2. 如果生存无虞且`duty` > 40 → 执行工作任务
3. 否则 → 自由活动/等待

### Prompt工程策略

每个角色的档案包含：
- **角色身份**：性格、背景、价值观
- **核心职责**：主要工作内容
- **工作流程**：详细的操作步骤和数据
- **决策优先级**：如何权衡不同目标
- **协作关系**：与其他角色的互动建议
- **工作建议**：实用的执行技巧

这些档案会被动态注入到LLM的system prompt中，引导AI做出符合角色设定的决策。

### 指令系统

游戏支持5种基础指令：

| 指令 | 参数 | 功能 |
|------|------|------|
| **Move** | TargetName | 移动到指定地点 |
| **Take** | TargetName, ItemID, Count | 从目标处拿取物品 |
| **Put** | TargetName, ItemID, Count | 将物品放到目标处 |
| **Use** | TargetName, ParamID | 使用设施（ParamID指定配方/作物类型） |
| **Wait** | ParamID（时长） | 等待指定时间 |

LLM生成的高级决策会被分解为这些基础指令序列。

---

### 共享任务黑板系统

**设计理念**：为多智能体协作提供统一的信息交换平台，让角色能够发布需求、认领任务、协调工作。

#### 黑板结构

```python
blackboard = {
    "tasks": [
        {
            "task_id": "unique_id",
            "task_type": "RequestFood|RequestTransport|RequestMaterial|...",
            "requester": "角色名称",
            "priority": 1-10,  # 优先级
            "status": "Pending|InProgress|Completed",
            "params": {
                # 任务特定参数
                "item_id": 2003,
                "count": 5,
                "from": "Storage",
                "to": "Stove"
            },
            "assigned_to": "执行者名称或空"
        }
    ]
}
```

#### 典型协作场景

**场景1：请求制作食物**
1. **Farmer检测到**：Storage中Meal库存低于阈值
2. **发布任务**：`RequestFood(ItemID=2003, Count=3, Priority=8)`
3. **Chef读取黑板**：看到食物请求，检查是否有原料（Corn）
4. **Chef认领任务**：标记任务为InProgress，执行制作流程
5. **完成反馈**：制作完成后标记为Completed

**场景2：请求搬运物品**
1. **Crafter规划制作Coat**：需要Thread和Cloth，但当前WorkStation附近没有材料
2. **发布搬运任务**：`RequestTransport(ItemID=2001, Count=3, From=Storage, To=WorkStation)`
3. **空闲角色响应**：任何精力充沛且无紧急任务的角色可以认领
4. **执行搬运**：移动→拿取→移动→放置
5. **Crafter继续工作**：材料到位后继续生产

**场景3：请求种植原料**
1. **Chef发现**：Storage中Corn库存告急（< 20）
2. **发布任务**：`RequestMaterial(ItemID=1002, Count=50, Priority=9)`
3. **Farmer看到请求**：调整种植计划，优先种植Corn
4. **持续反馈**：Farmer在工作时更新任务进度

#### 设计优势

- ✅ **解耦协作**：角色无需直接通信，通过黑板间接协调
- ✅ **优先级管理**：紧急任务（如食物短缺）自动获得更高优先级
- ✅ **提升效率**：空闲角色可主动认领搬运任务，避免专业角色浪费时间
- ✅ **LLM友好**：黑板状态以自然语言形式注入prompt，便于理解和决策

---

### 计划分解机制

**设计理念**：将LLM的token消耗集中在高层决策上，而具体的指令序列由确定性算法生成，既保证质量又节省成本。

#### 两层决策架构

```
┌─────────────────────────────────────────┐
│  Layer 1: 高层决策（LLM生成）           │
│  ┌─────────────────────────────────┐   │
│  │ "我需要制作Meal来补充食物库存"  │   │
│  │ Action: CraftMeal               │   │
│  │ Reasoning: 仓库里有足够的Corn... │   │
│  └─────────────────────────────────┘   │
└───────────────┬─────────────────────────┘
                │ 自动分解
┌───────────────▼─────────────────────────┐
│  Layer 2: 指令序列（程序生成）          │
│  1. Move(Storage)      ← 自动推导      │
│  2. Take(Corn, 5)      ← 查配方表      │
│  3. Move(Stove)        ← 自动推导      │
│  4. Put(Corn, 5)       ← 必需步骤      │
│  5. Use(Stove, MealRecipe) ← 执行制作   │
└─────────────────────────────────────────┘
```

#### 分解流程

**输入**：LLM返回的高层决策
```json
{
  "thought": "仓库有充足的Corn，我应该制作Meal",
  "high_level_action": "CraftMeal",
  "target_recipe_id": 200,  // 制作套餐的配方ID
  "reasoning": "当前Meal库存为1，低于安全阈值3"
}
```

**处理步骤**：
1. **查询配方表**：`Task.json` → TaskID=200需要5个Corn，在Stove完成
2. **检查当前状态**：
   - 角色位置：Table附近
   - 角色库存：空
   - Stove库存：空
   - Storage库存：Corn × 50
3. **生成指令序列**：
   ```python
   steps = [
       Move("Storage"),           # 去仓库拿原料
       Take("Storage", 1002, 5),  # 拿5个Corn
       Move("Stove"),             # 去炉灶
       Put("Stove", 1002, 5),     # 放入原料
       Use("Stove", 200)          # 执行配方200
   ]
   ```
4. **逐步执行**：每次返回一条指令，执行完成后继续下一条

#### 关键优势

| 传统方案 | 分解机制 |
|---------|---------|
| 每条指令都调用LLM | 只在高层决策时调用 |
| Token消耗：~1000/步 | Token消耗：~1000/决策（覆盖多步） |
| 指令质量不稳定 | 指令确定性生成，质量稳定 |
| 易出现逻辑错误 | 基于配方表，逻辑严密 |

**示例对比**：完成"制作Meal"任务

- **传统方案**：调用LLM 5次（每步询问），消耗~5000 tokens
- **分解机制**：调用LLM 1次（决策），消耗~1000 tokens，节省80%

#### 实现细节

**决策缓存**：
```python
class AgentState:
    current_plan = {
        "action": "CraftMeal",
        "steps": [Move(...), Take(...), ...],
        "current_step": 0,
        "total_steps": 5
    }
    
    def get_next_instruction(self):
        if self.current_plan and not self.plan_completed():
            # 返回计划中的下一步
            return self.current_plan["steps"][self.current_step]
        else:
            # 计划完成或无计划，调用LLM生成新决策
            return self.request_llm_decision()
```

**动态调整**：
- 如果执行过程中环境变化（如原料被他人拿走），重新调用LLM
- 支持"中断"机制：紧急情况（如饥饿值过高）可打断当前计划

---

## 🚀 开发指南

### 环境要求

- **游戏引擎**：Unreal Engine 5.x
- **编程语言**：C++（游戏逻辑）、Python 3.8+（LLM服务器）
- **依赖库**：Flask, Flask-CORS, requests（Python端）
- **LLM API**：支持OpenAI格式的API（GPT-4/Claude等）

### 快速启动

1. **启动LLM服务器**：
   ```bash
   cd Source/LLMServerNew
   python llm_server.py
   ```
   服务器将监听 `http://127.0.0.1:5000`

2. **配置API密钥**：
   在`config.py`中设置：
   ```python
   LLM_API_KEY = "your-api-key"
   LLM_MODEL = "gpt-4"
   LLM_URL = "https://api.openai.com/v1"
   ```

3. **启动Unreal编辑器**：
   打开`.uproject`文件，运行关卡

### 调试技巧

- **查看请求日志**：`Log/ServerReceive/` 记录所有HTTP请求
- **查看决策日志**：`Log/Round_XXX/` 记录每回合的AI决策过程
- **测试API连接**：访问 `http://127.0.0.1:5000/health`
- **单独测试Agent**：可以手动构造JSON请求测试`/GetInstruction`端点

---

## 📊 数据流示例

### 典型的决策流程（含计划分解）

**场景**：Chef需要制作Meal，展示完整的两层决策流程

#### 第一阶段：高层决策（调用LLM）

**1. 游戏发送状态**：
```json
{
  "TargetAgent": "Chef",
  "GameTime": "Day 1 08:00",
  "Characters": {
    "Chef": {
      "Location": "Table",
      "Stats": {"Hunger": 30, "Energy": 85},
      "Inventory": [],
      "CurrentPlan": null  // 无进行中的计划
    }
  },
  "Environment": {
    "Storage": {
      "Inventory": [
        {"ItemID": 1002, "ItemName": "Corn", "Count": 50}
      ]
    },
    "Stove": {
      "Inventory": [],
      "IsOccupied": false
    }
  },
  "Blackboard": {
    "Tasks": [
      {
        "TaskType": "RequestFood",
        "Requester": "Farmer",
        "Priority": 8,
        "Status": "Pending"
      }
    ]
  }
}
```

**2. 服务器构建Prompt**：
```
你是Chef，当前状态：
- 位置: Table
- Hunger: 30/100 (饥饿度低)
- Energy: 85/100 (精力充沛)
- Duty: 80/100 (任务黑板上有紧急食物请求)

环境状态：
- Storage中有50个Corn
- Stove空闲可用
- 黑板任务：Farmer请求食物（优先级8）

请决策下一步高层行动。
```

**3. LLM返回高层决策**：
```json
{
  "thought": "黑板上有紧急的食物请求，且我精力充沛，仓库有充足原料。作为厨师，我应该立即制作Meal来响应需求。",
  "high_level_action": "CraftMeal",
  "target_recipe_id": 200,
  "expected_steps": ["获取原料", "前往炉灶", "执行烹饪"],
  "reasoning": "履行厨师职责，响应黑板上的食物需求"
}
```

#### 第二阶段：计划分解（程序自动生成）

**4. 服务器执行分解算法**：
```python
def decompose_craft_action(character, recipe_id, environment):
    # 查询配方
    recipe = get_recipe(recipe_id)  # TaskID=200
    # recipe = {ingredients: [{ItemID:1002, Count:5}], facility: "Stove"}
    
    steps = []
    
    # 步骤1: 检查库存并规划拿取
    for ingredient in recipe.ingredients:
        item_location = find_item_in_environment(ingredient.ItemID, environment)
        if character.location != item_location:
            steps.append(Move(item_location))  # "Storage"
        steps.append(Take(item_location, ingredient.ItemID, ingredient.Count))
    
    # 步骤2: 移动到设施
    facility_name = recipe.facility  # "Stove"
    if character.location != facility_name:
        steps.append(Move(facility_name))
    
    # 步骤3: 放置原料
    for ingredient in recipe.ingredients:
        steps.append(Put(facility_name, ingredient.ItemID, ingredient.Count))
    
    # 步骤4: 执行制作
    steps.append(Use(facility_name, recipe_id))
    
    return steps
```

**5. 生成的指令序列**：
```json
{
  "plan": {
    "action": "CraftMeal",
    "steps": [
      {"type": "Move", "target": "Storage"},
      {"type": "Take", "target": "Storage", "itemID": 1002, "count": 5},
      {"type": "Move", "target": "Stove"},
      {"type": "Put", "target": "Stove", "itemID": 1002, "count": 5},
      {"type": "Use", "target": "Stove", "paramID": 200}
    ],
    "current_step": 0,
    "total_steps": 5
  }
}
```

#### 第三阶段：逐步执行（无需再调用LLM）

**6. 返回第一条指令给游戏**：
```json
{
  "CharacterName": "Chef",
  "CommandType": "Move",
  "TargetName": "Storage",
  "ParamID": 0,
  "Count": 0,
  "Decision": {
    "action": "CraftMeal",
    "current_step": "1/5: 移动到Storage获取原料",
    "reasoning": "执行制作Meal计划的第1步"
  },
  "RemainingSteps": 4
}
```

**7-10. 后续指令**（游戏每次执行完一条后请求下一条）：
- 第2次请求 → 返回 `Take(Storage, Corn, 5)` 
- 第3次请求 → 返回 `Move(Stove)`
- 第4次请求 → 返回 `Put(Stove, Corn, 5)`
- 第5次请求 → 返回 `Use(Stove, 200)` ，完成制作

**11. 计划完成**：
- Chef完成Meal制作，产出1个Meal到Stove
- 下次请求指令时，检测到计划已完成，重新调用LLM生成新决策

---

### 多智能体协作示例

**场景**：通过黑板系统协作，Crafter请求搬运，Farmer响应

**时间轴**：

| 时间 | Crafter | Farmer | 黑板状态 |
|------|---------|--------|----------|
| 08:00 | 决策：制作Coat<br>检测到缺少Thread | 正在CultivateChamber种植 | 空 |
| 08:05 | 发布任务到黑板：<br>`RequestTransport(Thread, 3)` | 继续种植 | Task#1: 搬运Thread |
| 08:15 | 等待Thread到达<br>（执行Wait指令） | 种植完成，检查黑板<br>发现搬运任务 | Task#1: Pending |
| 08:20 | 继续等待 | 决策：认领搬运任务<br>生成计划分解 | Task#1: InProgress<br>(Farmer) |
| 08:25 | 继续等待 | 执行：Move→Take→Move→Put | Task#1: InProgress |
| 08:30 | 检测到Thread到达<br>继续制作Coat | 完成搬运，标记任务完成 | Task#1: Completed |
| 08:35 | 执行Use(WorkStation) | 检查是否有新任务 | 空 |

**关键代码逻辑**：

```python
# Crafter的决策逻辑
def crafter_decision(character, environment, blackboard):
    # 检查是否能够制作Coat
    workstation = environment.get("WorkStation")
    has_thread = count_items(workstation, ItemID=2001) >= 3
    has_cloth = count_items(workstation, ItemID=2002) >= 2
    
    if not has_thread:
        # 发布搬运请求到黑板
        blackboard.post_task({
            "task_type": "RequestTransport",
            "requester": "Crafter",
            "item_id": 2001,
            "count": 3,
            "from": "Storage",
            "to": "WorkStation",
            "priority": 6
        })
        return Wait(duration=300)  # 等待5分钟
    
    # 如果材料齐全，执行制作
    return HighLevelAction("CraftCoat")

# Farmer的决策逻辑
def farmer_decision(character, environment, blackboard):
    # 先检查紧急的生理需求
    if character.hunger > 80:
        return HighLevelAction("Eat")
    
    # 检查黑板上的任务
    pending_tasks = blackboard.get_tasks(status="Pending")
    if pending_tasks:
        # 可以选择认领搬运类任务
        transport_tasks = [t for t in pending_tasks if t.type == "RequestTransport"]
        if transport_tasks and character.energy > 50:
            task = transport_tasks[0]
            blackboard.claim_task(task.id, character.name)
            return HighLevelAction("Transport", params=task.params)
    
    # 否则执行本职工作
    return HighLevelAction("PlantCrop")
```

**效率提升**：
- ⏱️ **节省时间**：Crafter无需亲自搬运，继续准备其他材料或休息
- 🔄 **资源优化**：空闲角色主动认领任务，避免产能浪费
- 🤝 **自然协作**：无需硬编码协作逻辑，AI通过理解黑板自主决策

---

## 🎯 项目目标与愿景

### 当前阶段
- ✅ 基础游戏框架搭建完成
- ✅ LLM服务器架构设计完成
- ✅ 角色档案（Prompt工程）初版完成
- 🚧 Agent决策逻辑实现中
- 🚧 多角色协作机制优化中

### 短期目标
- 实现完整的工作流：种植→收获→加工→烹饪
- 优化LLM prompt，提升决策质量
- 添加更多角色交互和社交机制
- 实现任务黑板和协作分配系统

### 长期愿景
- 支持更多角色类型和职业
- 引入随机事件和挑战
- 实现角色记忆系统（使用向量数据库）
- 多殖民地交易和外交系统
- 角色情感和关系网络
- 支持玩家与AI角色混合游戏

---

## 🤝 为其他AI助手的说明

### 如果你是帮助开发此项目的AI助手，请注意：

1. **理解核心理念**：这是一个LLM驱动的游戏AI项目，不是传统的行为树/状态机AI
2. **Prompt是关键**：角色档案（profile_*.txt）是AI行为的核心，修改时要考虑对决策的影响
3. **保持一致性**：Item.json、Task.json和角色档案中的数据必须同步
4. **分层设计**：游戏层（C++）负责执行，LLM层（Python）负责决策，职责分明
5. **日志很重要**：查看Log目录下的日志能快速理解系统行为
6. **测试策略**：可以先在Python端测试Agent逻辑，再集成到游戏中
7. **两层决策架构**：理解LLM只负责高层决策，具体指令由分解算法生成，避免过度依赖LLM
8. **黑板系统优先**：多角色协作问题首先考虑使用黑板机制，而非直接通信

### 常见任务参考

- **添加新物品**：修改Item.json + Task.json + 对应角色档案
- **添加新角色**：创建profile + CharacterProfiles.json + C++角色类
- **优化决策**：调整config.py中的阈值 + 角色档案中的决策优先级
- **调试AI行为**：查看Log/Round_XXX/下的决策推理过程
- **添加新的高层动作**：在agent_manager.py中实现对应的分解算法
- **优化协作效率**：调整黑板任务的优先级算法和认领条件
- **减少Token消耗**：扩展分解算法覆盖更多场景，减少LLM调用频率

---

## 📞 联系与贡献

本项目是一个实验性的LLM+游戏融合项目，旨在探索大语言模型在游戏AI中的应用潜力。

**项目特点**：
- 🔬 实验性质，大胆尝试新架构
- 📚 重视文档和可读性
- 🧪 持续迭代和优化中

---

*最后更新：2026年1月28日*
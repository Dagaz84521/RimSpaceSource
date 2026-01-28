# RimSpace Multi-Agent LLM Server

一个基于LLM的Multi-Agent系统，用于控制RimSpace游戏中的NPC角色。

## 特性

- **Multi-Agent协作**: 通过任务黑板(TaskBlackboard)实现角色间的任务发布和认领
- **智能决策**: 使用LLM进行高级决策，权衡生理需求、任务优先级等因素
- **计划分解**: Planner将高级决策分解为可执行的单步指令
- **协作机制**: 
  - 没有食物时自动请求厨师制作
  - 搬运物品时可发布部分任务给其他角色，实现并行协作

## 快速开始

### 1. 安装依赖

```bash
cd LLMServer
pip install -r requirements.txt
```

### 2. 配置OpenAI API（可选）

创建`.env`文件：
```
OPENAI_API_KEY=your_api_key_here
```

如果不配置LLM，系统将使用内置的规则引擎。

### 3. 启动服务器

```bash
python LLMServer.py
```

服务器将在 `http://localhost:5000` 启动

### 4. 测试连接

在Unreal Editor中，运行游戏并点击"连接服务器"按钮。

## 架构说明

```
游戏 <--HTTP--> LLMServer
                   |
                   +-- TaskBlackboard (任务黑板)
                   |
                   +-- LLM (高级决策)
                   |
                   +-- Planner (计划分解)
```

### 工作流程

1. **角色请求指令**: 游戏通过`/GetInstruction`接口发送角色状态和世界信息
2. **LLM决策**: 服务器将信息整理成Prompt，调用LLM做出高级决策（Sleep/Eat/Craft等）
3. **计划分解**: Planner将高级决策分解为单步指令（Move/Take/Put/Use/Wait）
4. **协作判断**: 如果需要协作（如缺食物、缺原料），发布任务到黑板
5. **返回指令**: 返回下一个单步指令给游戏执行

## API接口

### GET /health
健康检查

### POST /GetInstruction
获取角色的下一个指令（核心接口）

**请求格式**:
```json
{
  "TargetAgent": "CharacterName",
  "GameTime": "Day 1, 08:30",
  "Environment": {
    "Storage_1": {"Type": "Storage", "Inventory": [...]},
    "Stove_1": {"Type": "Stove", "Inventory": [...]}
  },
  "Characters": {
    "CharacterName": {
      "Hunger": 50,
      "Energy": 70,
      "Position": "Storage_1",
      "Inventory": [...]
    }
  },
  "TaskRecipes": [...],
  "ItemDatabase": {...}
}
```

**响应格式**:
```json
{
  "CharacterName": "CharacterName",
  "CommandType": "Move",
  "TargetName": "Stove_1",
  "ParamID": 0,
  "Count": 0
}
```

### POST /UpdateGameState
更新游戏状态（可选，如果不在GetInstruction中传递）

### GET /GetBlackboard
查看任务黑板状态（调试用）

## 协作机制示例

### 场景1: 食物请求
```
1. Alice 饥饿度低于30
2. LLM决策: Eat
3. Planner检查: 背包无食物，仓库无食物
4. 发布任务到黑板: "请求制作食物"
5. Alice 执行: Wait
6. Bob (厨师) 检查黑板，认领任务
7. Bob 制作食物放入仓库
8. Alice 下次循环时去仓库取食物
```

### 场景2: 并行搬运
```
1. Charlie 决定制作物品A
2. Planner检查: 工作台缺5个原料，仓库有货
3. 发布任务: 搬运2个原料（发布到黑板）
4. Charlie自己: 搬运3个原料
5. Dave空闲，认领黑板任务，搬运2个
6. Charlie和Dave并行工作，节省时间
```

## 扩展开发

### 添加新的高级动作

1. 在Planner.py中添加对应的`_plan_xxx`方法
2. 在`_generate_plan`中添加新的动作分支
3. 更新LLM的Prompt，让它知道新动作

### 自定义规则引擎

修改`rule_based_decision`函数，实现自己的决策逻辑。

### 调整LLM模型

在`call_llm_for_decision`中修改模型参数：
```python
model="gpt-4o-mini",  # 改为 gpt-4 或其他模型
temperature=0.7,      # 调整创造性
```

## 故障排查

### 连接失败
- 检查服务器是否运行
- 检查防火墙设置
- 确认端口5000未被占用

### LLM不工作
- 检查.env中的API Key
- 查看控制台错误信息
- 降级到规则引擎模式

### 角色卡住
- 查看服务器日志
- 检查黑板状态 (GET /GetBlackboard)
- 重启服务器清空状态

## 开发计划

- [ ] 支持更多协作场景
- [ ] 优化LLM Prompt
- [ ] 添加记忆系统
- [ ] 实现角色间对话
- [ ] 性能优化和缓存

## License

MIT

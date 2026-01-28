# 自适应规划机制 - 解决动态环境问题

## 🎯 问题背景

在动态游戏环境中，预先生成的计划队列可能因为世界状态变化而失效：

### 典型失效场景：

1. **资源竞争**
   ```
   Alice计划: [Move->Storage, Take(食物), Use(食物)]
   执行到Take时: Bob已经把食物拿走了 ❌
   ```

2. **设施占用**
   ```
   Alice计划: [Move->Stove, Use(Stove, 煮饭)]
   执行到Use时: Charlie正在使用Stove ❌
   ```

3. **紧急状态**
   ```
   Alice计划: [搬运物品的5步序列]
   执行到第3步: Hunger突然降到5，应该立即去吃饭 ❌
   ```

## ✅ 解决方案

### 1. **每步验证机制** (Step Validation)

在返回每个指令之前，验证其可行性：

```python
def decompose_action(self, ...):
    if self.agent_plans[character_name]:
        next_step = self.agent_plans[character_name][0]  # 先查看
        
        # ⭐ 关键：验证这一步是否仍然可行
        if self._validate_step(next_step, game_state, character_name):
            return self.agent_plans[character_name].pop(0)  # 可行，执行
        else:
            # 不可行，清空计划重新规划
            self.agent_plans[character_name] = []
            # 继续生成新计划
```

### 2. **验证逻辑** (Validation Logic)

```python
def _validate_step(self, step, game_state, character_name):
    """验证单步指令是否仍然可行"""
    
    # Move: 检查目标是否存在
    if step.CommandType == "Move":
        return step.TargetName in game_state["Environment"]
    
    # Take: 检查物品是否足够
    if step.CommandType == "Take":
        inventory = get_inventory(step.TargetName)
        item = find_item(inventory, step.ParamID)
        return item and item["Count"] >= step.Count
    
    # Put: 检查角色是否持有该物品
    if step.CommandType == "Put":
        inventory = get_character_inventory(character_name)
        item = find_item(inventory, step.ParamID)
        return item and item["Count"] >= step.Count
    
    # Use: 检查设施是否存在
    if step.CommandType == "Use":
        return step.TargetName in game_state["Environment"]
```

### 3. **限制计划长度** (Plan Length Limit)

避免过长的预规划：

```python
self.max_plan_length = 5  # 最多5步

if len(plan) > self.max_plan_length:
    plan = plan[:self.max_plan_length]  # 截断
```

**好处**：
- 减少失效概率
- 更频繁地重新评估状态
- 更快响应环境变化

### 4. **紧急状态打断** (Emergency Override)

检测危急情况并强制重规划：

```python
# 在LLMServer中
if energy < 10 or hunger < 10:
    planner.clear_plan(character_name)  # 清空当前计划
    # 重新决策，LLM会优先处理生理需求
```

## 🔄 完整执行流程

```
请求1: Alice计划去制作物品
  ├─ LLM决策: Craft(recipe_id=1)
  ├─ Planner生成: [Move->Storage, Take(原料), Move->Stove, Put(原料), Use(Stove)]
  ├─ 验证第1步: Move->Storage ✓ Storage存在
  └─ 返回: Move->Storage

游戏: Alice移动 ✓

请求2: Alice到达Storage
  ├─ 队列剩余: [Take(原料), Move->Stove, Put(原料), Use(Stove)]
  ├─ 验证第1步: Take(原料) ✓ Storage中有原料
  └─ 返回: Take(原料)

游戏: Alice取原料 ✓

请求3: Alice准备去Stove
  ├─ 队列剩余: [Move->Stove, Put(原料), Use(Stove)]
  ├─ 检测: Hunger=8 (紧急状态!) ⚠️
  ├─ 清空队列: []
  ├─ LLM重新决策: Eat (优先生理需求)
  ├─ Planner生成: [Move->Storage, Take(食物), Use(食物)]
  └─ 返回: Move->Storage

游戏: Alice去找食物 ✓ (中断了制作任务)

请求4: Alice到达Storage
  ├─ 队列剩余: [Take(食物), Use(食物)]
  ├─ 验证第1步: Take(食物) ❌ Bob刚把最后的食物拿走了!
  ├─ 计划失效，清空队列: []
  ├─ LLM重新决策: Eat
  ├─ Planner检查: 无食物
  ├─ 发布黑板任务: "请求制作食物"
  └─ 返回: Wait

游戏: Alice等待厨师制作 ✓ (自适应处理资源竞争)
```

## 📊 机制对比

| 场景 | 原始设计 | 自适应规划 |
|------|---------|-----------|
| Bob拿走食物 | Alice执行Take失败，卡住 ❌ | 验证失败，重新规划 ✓ |
| 突然饥饿 | 继续执行搬运任务 ❌ | 清空计划，优先吃饭 ✓ |
| 长期计划(10步) | 容易失效 ❌ | 限制5步，频繁重评估 ✓ |
| LLM调用次数 | 少 (成本低) | 适中 (平衡) |
| 响应速度 | 慢 | 快 ✓ |

## ⚙️ 可调参数

### 1. 计划长度限制
```python
self.max_plan_length = 5  # 根据游戏节奏调整
# 快节奏: 3步
# 慢节奏: 8步
```

### 2. 紧急状态阈值
```python
# 保守策略（频繁打断）
if energy < 15 or hunger < 15:
    clear_plan()

# 激进策略（减少打断）
if energy < 5 or hunger < 5:
    clear_plan()
```

### 3. 验证强度
```python
# 完整验证（最安全）
def _validate_step(self, step, ...):
    # 检查所有可能的失效条件
    
# 轻量验证（性能优先）
def _validate_step(self, step, ...):
    # 只检查关键条件
    return True  # 信任计划
```

## 🚀 性能优化

### 问题：验证增加了开销

**解决方案1：缓存验证结果**
```python
self.validation_cache = {}

def _validate_step(self, step, game_state, ...):
    cache_key = f"{step.CommandType}_{step.TargetName}_{step.ParamID}"
    if cache_key in self.validation_cache:
        return self.validation_cache[cache_key]
    
    result = self._do_validation(...)
    self.validation_cache[cache_key] = result
    return result
```

**解决方案2：异步验证**
```python
# 在后台验证整个队列，提前发现问题
async def validate_plan_async(self, character_name, game_state):
    for step in self.agent_plans[character_name]:
        if not self._validate_step(step, game_state):
            self.agent_plans[character_name] = []
            break
```

## 💡 最佳实践

1. **短期计划 + 频繁重规划**
   - 比长期预规划更稳定
   - LLM成本略增但可接受

2. **分层规划**
   ```
   高层: LLM决策 (战略)
   中层: Planner分解 (战术，3-5步)
   底层: 游戏执行 (操作)
   ```

3. **异常处理**
   ```python
   try:
       execute_step(step)
   except ExecutionError:
       # 通知Planner失效
       planner.clear_plan(character_name)
   ```

4. **监控和日志**
   ```python
   print(f"[验证失败] {reason}")  # 记录失效原因
   metrics.increment("plan_invalidations")  # 统计失效率
   ```

## 🔮 未来改进

1. **预测性验证**
   - 提前预测下2-3步是否可行
   - 提前规避失效

2. **部分重规划**
   - 只修改失效的部分，保留有效步骤
   - 减少重规划开销

3. **多候选方案**
   - 生成Plan A和Plan B
   - Plan A失效时自动切换

4. **学习失效模式**
   - 记录哪些场景容易失效
   - 调整规划策略

## 📝 总结

通过 **每步验证 + 限制长度 + 紧急打断** 三重机制，系统能够：

✅ 自动检测计划失效  
✅ 快速响应环境变化  
✅ 优先处理紧急状态  
✅ 在效率和稳定性间平衡  

这是一个**实用且鲁棒**的解决方案！

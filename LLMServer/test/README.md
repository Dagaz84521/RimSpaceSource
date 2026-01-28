# LLMServer Test 目录

这个目录包含 Agent 决策系统的测试用例。

## 测试文件

### test_agent_decision.py
测试 RimSpace Agent 的单步决策功能，使用真实游戏数据。

#### 运行方法：
```bash
# 激活 conda 环境
conda activate RimSpace

# 进入 Source 目录
cd D:\Unreal\Projects\RimSpace\Source

# 运行测试
python .\LLMServer\test\test_agent_decision.py
```

#### 测试内容：
1. **基础功能测试 (无需 LLM)**
   - 数据提取：从游戏 JSON 提取角色和环境数据
   - 状态更新：测试欲望值计算是否正确
   - 观察文本生成：验证生成的文本格式
   - Profile 加载：测试职业描述文件加载

2. **完整决策测试 (需要 LLM API)**
   - Agent 创建和初始化
   - 内部状态映射 (D2A 欲望系统)
   - LLM 决策调用
   - 决策结果验证

#### 测试数据来源：
使用真实游戏发送的 JSON 数据 (`InstructionRequest_Farmer_20260128_163229.json`)

#### 注意事项：
- 基础测试可以直接运行，无需配置
- LLM 决策测试需要在 `config.py` 中配置 `LLM_API_KEY`
- 如果 `文档/profile_farmer.txt` 不存在，会使用默认描述

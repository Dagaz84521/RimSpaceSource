# RimSpace Multi-Agent 系统快速开始指南

## 📋 前置要求

- Python 3.8 或更高版本
- （可选）OpenAI API Key（不配置将使用规则引擎）

## 🚀 快速启动

### Windows用户

1. **双击运行启动脚本**
   ```
   start_server.bat
   ```
   
   脚本会自动：
   - 创建虚拟环境
   - 安装依赖包
   - 启动服务器

### 手动启动

1. **安装依赖**
   ```bash
   cd LLMServer
   pip install -r requirements.txt
   ```

2. **（可选）配置API Key**
   
   复制`.env.example`为`.env`并填入你的API Key：
   ```bash
   copy .env.example .env
   ```
   
   编辑`.env`文件：
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

3. **启动服务器**
   ```bash
   python LLMServer.py
   ```

4. **验证运行**
   
   打开浏览器访问: http://localhost:5000/health
   
   或运行测试脚本：
   ```bash
   python test_server.py
   ```

## 🎮 在Unreal中使用

1. 启动Unreal Editor
2. 打开RimSpace项目
3. 运行游戏（PIE）
4. 在主菜单点击"连接服务器"按钮
5. 看到"服务器连接正常"后即可开始游戏

## 🔧 配置说明

### 使用OpenAI官方API

`.env`文件：
```
OPENAI_API_KEY=sk-your-key-here
```

### 使用本地LLM（Ollama）

1. 安装并启动Ollama
2. `.env`文件：
   ```
   OPENAI_API_KEY=ollama
   OPENAI_BASE_URL=http://localhost:11434/v1
   ```

### 只使用规则引擎（不需要LLM）

不配置任何API Key，服务器会自动使用内置的规则引擎。

## 📊 监控和调试

### 查看黑板状态

浏览器访问: http://localhost:5000/GetBlackboard

### 查看服务器日志

服务器控制台会实时输出：
- 角色请求
- LLM决策
- Planner分解
- 返回指令

示例输出：
```
============================================================
[GetInstruction] 处理 Alice 的指令请求
游戏时间: Day 1, 08:30
黑板任务: 0 待认领, 0 进行中
[高级决策] Eat - 参数: {}
[Planner] 没有食物，发布烹饪任务到黑板
[Planner] 下一步: Wait
[返回指令] {'CharacterName': 'Alice', 'CommandType': 'Wait', ...}
============================================================
```

## ⚠️ 常见问题

### Q: 连接失败怎么办？

**A:** 检查以下几点：
1. 服务器是否启动成功
2. 防火墙是否拦截5000端口
3. Unreal中的ServerURL是否正确（应为`http://localhost:5000`）

### Q: LLM不工作？

**A:** 
1. 检查`.env`中的API Key是否正确
2. 查看服务器启动时的提示信息
3. 如果API调用失败，系统会自动降级到规则引擎

### Q: 角色一直Wait？

**A:** 可能原因：
1. 黑板没有可认领的任务
2. 游戏状态数据不完整
3. Planner无法生成有效计划

查看服务器日志获取详细信息。

### Q: 如何添加新的协作场景？

**A:** 
1. 在`Planner.py`中添加新的`_plan_xxx`方法
2. 在需要协作的地方调用`blackboard.publish_task()`
3. 更新LLM的Prompt让它知道新场景

## 📝 开发建议

### 调试流程

1. 先用`test_server.py`测试服务器基本功能
2. 再在Unreal中测试实际集成
3. 查看服务器日志定位问题

### 性能优化

- 如果LLM调用慢，考虑使用缓存
- 可以限制每次GetInstruction的数据量
- 黑板任务定期清理（已实现）

### 扩展功能

参考`README.md`中的扩展开发章节。

## 📞 获取帮助

- 查看`README.md`获取完整文档
- 查看代码注释了解实现细节
- 运行`test_server.py`进行功能测试

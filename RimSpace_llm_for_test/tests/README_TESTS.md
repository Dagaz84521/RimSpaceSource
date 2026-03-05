测试说明
===========

快速开始：

1. 安装 pytest：

```powershell
pip install pytest
```

2. 运行测试：

```powershell
cd d:\Work\RimSpaceLLM_Server
pytest -q
```

模板说明：
- 文件：[tests/test_template.py](tests/test_template.py) 包含示例 fixture 和占位测试。
- 根据需要修改或新增测试文件，推荐以 `test_*.py` 命名。

建议：将项目依赖（如 pytest）加入 `requirements.txt` 或使用虚拟环境。

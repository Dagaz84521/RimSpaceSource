"""
测试模板（pytest）

用法:
    pip install pytest
    cd d:\Work\RimSpaceLLM_Server
    pytest -q

说明：此文件为模板，包含示例测试和占位符，方便后续扩展。
"""
import pytest

from environment_translator import (
    get_all_actor_names,
    get_target_actor_state,
    get_target_type_actor_state,
)


@pytest.fixture
def sample_environment():
    return {
        "actors": [
            {"ActorName": "Farm", "ActorType": "EInteractionType::EAT_Storage"},
            {"ActorName": "Stove1", "ActorType": "EInteractionType::EAT_Stove"},
            {"ActorName": "Bench", "ActorType": "EInteractionType::EAT_WorkStation"},
        ]
    }


def test_get_all_actor_names_basic(sample_environment):
    res = get_all_actor_names(sample_environment)
    assert "3 个场所" in res or "3" in res
    assert "Farm" in res
    assert "Stove1" in res
    assert "Bench" in res


@pytest.mark.parametrize(
    "target,expected_contains",
    [
        ("Farm", "仓库"),
        ("Stove1", "炉灶"),
        ("Bench", "工作台"),
    ],
)
def test_get_target_actor_state_known_types(sample_environment, target, expected_contains):
    res = get_target_actor_state(sample_environment, target)
    # 模板：根据实际实现细化断言
    assert target in res
    # 如果实现返回类型中文说明，可检查关键字
    # 允许两种情况：具体提示或默认提示
    assert ("当前状态未知" in res) or (expected_contains in res)


def test_get_target_actor_state_not_found(sample_environment):
    res = get_target_actor_state(sample_environment, "不存在的场所")
    assert "未找到名为" in res or "不可用" not in res


def test_get_target_type_actor_state_list(sample_environment):
    res = get_target_type_actor_state(sample_environment, "EInteractionType::EAT_Stove")
    assert "Stove1" in res


# TODO:
# - 增加更复杂 environment 的 fixture
# - 对返回的文本做更严格的正则/格式检查
# - 如需测试边界条件、异常或 IO，可用 monkeypatch/临时文件

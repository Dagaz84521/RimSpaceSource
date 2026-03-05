"""
感知器模块：将感知环境并生成黑板任务的逻辑抽离到此文件。
提供函数 `perceive_environment_tasks(environment_data, blackboard_instance, global_planner, meal_min_stock)`。
"""
from typing import Dict, Any
from blackboard import BlackboardTask, Goal
from rimspace_enum import EInteractionType, ECultivatePhase


def perceive_environment_tasks(environment_data: Dict[str, Any],
                               blackboard_instance,
                               global_planner,
                               meal_min_stock: int):
    """
    感知层：扫描环境中的 Actor 状态，自动生成隐式任务并注入到黑板中。

    参数:
    - environment_data: 来自游戏的 Environment 数据（dict）
    - blackboard_instance: 黑板实例，用于发布任务
    - global_planner: Planner 实例，用于拆解配方类需求
    - meal_min_stock: 炉子最小备餐数量阈值
    """
    # 获取环境中的所有 Actor
    actors = environment_data.get("Actors", [])
    if isinstance(actors, dict):  # 处理一下数据结构可能的不一致（列表或字典）
        actors = list(actors.values())  # 如果是 {"ActorName": {...}} 的形式
    stove_name = None
    for actor in actors:
        actor_name = actor.get("ActorName", "")
        actor_type = actor.get("ActorType", "")
        if actor_type == EInteractionType.CultivateChamber.value:
            cultivate_info = actor.get("CultivateInfo", {})
            cultivate_phase = cultivate_info.get("CurrentPhase", "")
            if cultivate_phase == ECultivatePhase.WaitingToPlant.value:
                cultivate_type = cultivate_info.get("TargetCultivateType", "")
                cultivate_type_str = cultivate_type.replace("ECultivateType::ECT_", "")
                goal = Goal(
                    target_actor=actor_name,
                    property_type="CultivateInfo",
                    key="CurrentPhase",
                    operator="==",
                    value=ECultivatePhase.Growing.value
                )
                task = BlackboardTask(
                    description=f"Plant {cultivate_type_str} in {actor_name}",
                    goal=goal,
                    required_skill="canFarm"
                )
                blackboard_instance.post_task(task)
            elif cultivate_phase == ECultivatePhase.ReadyToHarvest.value:
                cultivate_type = cultivate_info.get("CurrentCultivateType", "")
                cultivate_type_str = cultivate_type.replace("ECultivateType::ECT_", "")
                goal = Goal(
                    target_actor=actor_name,
                    property_type="CultivateInfo",
                    key="CurrentPhase",
                    operator="==",
                    value=ECultivatePhase.WaitingToPlant.value
                )
                task = BlackboardTask(
                    description=f"Harvest {cultivate_type_str} from {actor_name}",
                    goal=goal,
                    required_skill="canFarm"
                )
                blackboard_instance.post_task(task)
        elif actor_type == EInteractionType.WorkStation.value or actor_type == EInteractionType.Stove.value:
            task_list = actor.get("TaskList", {})
            for task_id, count in task_list.items():
                # 感知层不再构建 Goal 和 Preconditions，
                # 只是把“需求”抛给 Planner 进行统一调度和拆解。
                global_planner.analyze_and_post_crafting_task(
                    facility_name=actor_name,
                    task_id=task_id,
                    count=count,
                    environment=environment_data
                )
            if actor_type == EInteractionType.Stove.value:
                stove_name = actor_name

    if stove_name and meal_min_stock > 0:
        meal_id = getattr(global_planner, 'game_data', None)
        if meal_id and hasattr(global_planner.game_data, 'item_name_to_id'):
            meal_id = global_planner.game_data.item_name_to_id.get("Meal")
        else:
            meal_id = None

        if meal_id:
            global_planner.ensure_min_stock(
                item_id=meal_id,
                min_count=meal_min_stock,
                target_facility=stove_name,
                environment=environment_data
            )

    return None

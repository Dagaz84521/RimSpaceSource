import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover - runtime check
    requests = None


def _fmt_time(day: int, hour: int, minute: int) -> str:
    return f"Day {day}  {hour:02d}:{minute:02d}"


def _add_item(inv: Dict[str, int], item_id: int, count: int) -> bool:
    if count <= 0:
        return False
    key = str(item_id)
    inv[key] = inv.get(key, 0) + count
    return True


def _remove_item(inv: Dict[str, int], item_id: int, count: int) -> bool:
    if count <= 0:
        return False
    key = str(item_id)
    if inv.get(key, 0) < count:
        return False
    inv[key] -= count
    if inv[key] <= 0:
        inv.pop(key, None)
    return True


def _load_task_product_map() -> Dict[str, int]:
    data_dir = os.path.join(os.path.dirname(__file__), "..", "Data")
    task_path = os.path.join(data_dir, "Task.json")
    try:
        with open(task_path, "r", encoding="utf-8") as handle:
            tasks = json.load(handle)
        return {str(t["TaskID"]): int(t.get("ProductID", t["TaskID"])) for t in tasks}
    except Exception:
        return {}


def _load_task_ingredients_map() -> Dict[str, List[Dict[str, int]]]:
    data_dir = os.path.join(os.path.dirname(__file__), "..", "Data")
    task_path = os.path.join(data_dir, "Task.json")
    try:
        with open(task_path, "r", encoding="utf-8") as handle:
            tasks = json.load(handle)
        return {str(t["TaskID"]): t.get("Ingredients", []) for t in tasks}
    except Exception:
        return {}


TASK_PRODUCT_MAP = _load_task_product_map()
TASK_INGREDIENTS_MAP = _load_task_ingredients_map()
CULTIVATE_PRODUCT_MAP = {
    "ECultivateType::ECT_Cotton": 1001,
    "ECultivateType::ECT_Corn": 1002,
}


@dataclass
class SimTime:
    day: int = 1
    hour: int = 6
    minute: int = 0

    def advance_minutes(self, minutes: int) -> None:
        if minutes <= 0:
            return
        total = self.minute + minutes
        self.minute = total % 60
        carry_hours = total // 60
        self.hour += carry_hours
        if self.hour >= 24:
            carry_days = self.hour // 24
            self.hour = self.hour % 24
            self.day += carry_days

    def formatted(self) -> str:
        return _fmt_time(self.day, self.hour, self.minute)


class SimWorld:
    def __init__(self, data: Dict):
        self.time = SimTime()
        self.environment = data.get("Environment", {})
        self.characters = data.get("Characters", {})

    def has_pending_tasks(self) -> bool:
        """检查是否还有待执行的任务（TaskList 非空）"""
        for actor in self.environment.get("Actors", []):
            task_list = actor.get("TaskList", {})
            if isinstance(task_list, dict) and task_list:
                return True
        return False

    def build_request(self, target_agent: str) -> Dict:
        return {
            "RequestType": "GetInstruction",
            "TargetAgent": target_agent,
            "GameTime": self.time.formatted(),
            "Environment": copy.deepcopy(self.environment),
            "Characters": copy.deepcopy(self.characters),
        }

    def _find_actor(self, name: str) -> Optional[Dict]:
        for actor in self.environment.get("Actors", []):
            if actor.get("ActorName") == name:
                return actor
        return None

    def _find_character(self, name: str) -> Optional[Dict]:
        for char in self.characters.get("Characters", []):
            if char.get("CharacterName") == name:
                return char
        return None

    def apply_command(self, character_name: str, command: Dict) -> None:
        char = self._find_character(character_name)
        if not char:
            return

        cmd_type = command.get("CommandType", "Wait")
        target_name = command.get("TargetName", "")
        param_id = int(command.get("ParamID", 0))
        count = int(command.get("Count", 0))

        if cmd_type == "Move":
            if target_name:
                char["CurrentLocation"] = target_name
            char["ActionState"] = "ECharacterActionState::Idle"
            self.time.advance_minutes(1)
            return

        if cmd_type in {"Take", "Put", "Use"}:
            current_location = char.get("CurrentLocation", "None")
            actor = self._find_actor(current_location) if current_location else None
            if not actor:
                char["ActionState"] = "ECharacterActionState::Idle"
                self.time.advance_minutes(1)
                return

        if cmd_type == "Take":
            inv_actor = actor.setdefault("Inventory", {})
            inv_char = char.setdefault("Inventory", {})
            if _remove_item(inv_actor, param_id, count):
                _add_item(inv_char, param_id, count)
            char["ActionState"] = "ECharacterActionState::Idle"
            self.time.advance_minutes(1)
            return

        if cmd_type == "Put":
            inv_actor = actor.setdefault("Inventory", {})
            inv_char = char.setdefault("Inventory", {})
            if _remove_item(inv_char, param_id, count):
                _add_item(inv_actor, param_id, count)
            char["ActionState"] = "ECharacterActionState::Idle"
            self.time.advance_minutes(1)
            return

        if cmd_type == "Use":
            actor_type = actor.get("ActorType", "")
            if "CultivateChamber" in actor_type:
                cultivate_info = actor.setdefault("CultivateInfo", {})
                phase = cultivate_info.get("CurrentPhase")
                if phase == "ECultivatePhase::ECP_WaitingToPlant":
                    cultivate_info["CurrentPhase"] = "ECultivatePhase::ECP_Growing"
                    cultivate_info["CurrentCultivateType"] = cultivate_info.get("TargetCultivateType", "ECultivateType::ECT_None")
                elif phase == "ECultivatePhase::ECP_ReadyToHarvest":
                    crop_type = cultivate_info.get("CurrentCultivateType", "ECultivateType::ECT_None")
                    product_id = CULTIVATE_PRODUCT_MAP.get(crop_type)
                    if product_id is not None:
                        inv_actor = actor.setdefault("Inventory", {})
                        _add_item(inv_actor, product_id, 3)
                    cultivate_info["CurrentPhase"] = "ECultivatePhase::ECP_WaitingToPlant"
                    cultivate_info["CurrentCultivateType"] = "ECultivateType::ECT_None"
                    cultivate_info["GrowthProgress"] = 0
            elif "WorkStation" in actor_type or "Stove" in actor_type:
                task_key = str(param_id)
                # 检查任务是否是有效的任务（由 LLM 指令动态触发）
                if task_key in TASK_PRODUCT_MAP:
                    inv_actor = actor.setdefault("Inventory", {})
                    ingredients = TASK_INGREDIENTS_MAP.get(task_key, [])
                    task_list = actor.get("TaskList", {})
                    remaining_tasks = int(task_list.get(task_key, 0)) if isinstance(task_list, dict) else 0
                    has_all_ingredients = True
                    for ing in ingredients:
                        ing_id = int(ing.get("ItemID", 0))
                        ing_count = int(ing.get("Count", 0))
                        if ing_count <= 0:
                            continue
                        if inv_actor.get(str(ing_id), 0) < ing_count:
                            has_all_ingredients = False
                            break

                    if has_all_ingredients:
                        for ing in ingredients:
                            ing_id = int(ing.get("ItemID", 0))
                            ing_count = int(ing.get("Count", 0))
                            if ing_count > 0:
                                _remove_item(inv_actor, ing_id, ing_count)
                        product_id = TASK_PRODUCT_MAP.get(task_key)
                        if product_id is not None:
                            _add_item(inv_actor, product_id, 1)
                        # 制作完成后，只有当任务列表中有该任务时才减少
                        if isinstance(task_list, dict) and remaining_tasks > 0:
                            remaining_tasks = max(0, remaining_tasks - 1)
                            if remaining_tasks == 0:
                                task_list.pop(task_key, None)
                            else:
                                task_list[task_key] = remaining_tasks
            elif "Table" in actor_type:
                # 吃饭逻辑：消耗背包中的 Meal (ID: 2003)，恢复 Hunger
                inv_char = char.get("Inventory", {})
                meal_id = "2003"
                if meal_id in inv_char and inv_char[meal_id] > 0:
                    if _remove_item(inv_char, 2003, 1):
                        stats = char.get("CharacterStats", {})
                        max_hunger = stats.get("MaxHunger", 100)
                        stats["Hunger"] = min(max_hunger, stats.get("Hunger", 0) + 30)
            elif "Bed" in actor_type:
                # 睡眠逻辑：恢复 Energy
                stats = char.get("CharacterStats", {})
                max_energy = stats.get("MaxEnergy", 100)
                stats["Energy"] = min(max_energy, stats.get("Energy", 0) + 30)
            char["ActionState"] = "ECharacterActionState::Idle"
            self.time.advance_minutes(1)
            return

        if cmd_type == "Wait":
            minutes = max(0, param_id)
            char["ActionState"] = "ECharacterActionState::Waiting"
            self.time.advance_minutes(minutes)
            char["ActionState"] = "ECharacterActionState::Idle"
            return

        char["ActionState"] = "ECharacterActionState::Idle"
        self.time.advance_minutes(1)

    def tick_environment(self, minutes: int = 1) -> None:
        if minutes <= 0:
            return
        for _ in range(minutes):
            self.time.advance_minutes(1)
            for actor in self.environment.get("Actors", []):
                if "CultivateChamber" not in actor.get("ActorType", ""):
                    continue
                cultivate_info = actor.get("CultivateInfo", {})
                if cultivate_info.get("CurrentPhase") != "ECultivatePhase::ECP_Growing":
                    continue
                cultivate_info["GrowthProgress"] = cultivate_info.get("GrowthProgress", 0) + 1
                if cultivate_info["GrowthProgress"] >= cultivate_info.get("GrowthMaxProgress", 24):
                    cultivate_info["CurrentPhase"] = "ECultivatePhase::ECP_ReadyToHarvest"

    def degrade_character_stats(self, degradation: int = 10) -> None:
        """每轮结束后，所有角色的 Hunger 和 Energy 降低"""
        for char in self.characters.get("Characters", []):
            stats = char.get("CharacterStats", {})
            stats["Hunger"] = max(0, stats.get("Hunger", 0) - degradation)
            stats["Energy"] = max(0, stats.get("Energy", 0) - degradation)


def build_default_world() -> Dict:
    """构建默认世界，目标是生产 1 件衣服（ID 3001）"""
    return {
        "Environment": {
            "Actors": [
                {
                    "ActorName": "CultivateChamber_1",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Cotton",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_2",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Cotton",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_3",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Corn",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "CultivateChamber_4",
                    "ActorType": "EInteractionType::EAT_CultivateChamber",
                    "Inventory": {},
                    "CultivateInfo": {
                        "CurrentPhase": "ECultivatePhase::ECP_WaitingToPlant",
                        "TargetCultivateType": "ECultivateType::ECT_Corn",
                        "CurrentCultivateType": "ECultivateType::ECT_None",
                        "GrowthProgress": 0,
                        "GrowthMaxProgress": 24,
                    },
                    "WorkProgress": 0,
                    "WorkloadMax": 10,
                    "HasWorker": False,
                },
                {
                    "ActorName": "WorkStation",
                    "ActorType": "EInteractionType::EAT_WorkStation",
                    "Inventory": {
                    },
                    "TaskList": {
                        "3001": 3,
                    },
                },
                {
                    "ActorName": "Stove",
                    "ActorType": "EInteractionType::EAT_Stove",
                    "Inventory": {},
                },
                {
                    "ActorName": "Storage",
                    "ActorType": "EInteractionType::EAT_None",
                    "Inventory": {
                        "1002": 10, # Corn
                    },
                },
                {
                    "ActorName": "Table",
                    "ActorType": "EInteractionType::EAT_Table",
                },
                {
                    "ActorName": "Bed_1",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
                {
                    "ActorName": "Bed_2",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
                {
                    "ActorName": "Bed_3",
                    "ActorType": "EInteractionType::EAT_Bed",
                },
            ]
        },
        "Characters": {
            "Characters": [
                {
                    "CharacterName": "Farmer",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Thinking",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.75,
                        "MaxHunger": 100.0,
                        "Energy": 99.75,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanFarm"],
                },
                {
                    "CharacterName": "Crafter",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Waiting",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.8,
                        "MaxHunger": 100.0,
                        "Energy": 99.8,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanCraft"],
                },
                {
                    "CharacterName": "Chef",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Waiting",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 99.8,
                        "MaxHunger": 100.0,
                        "Energy": 99.8,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanCook"],
                },
            ]
        },
    }


def _send_request(server_url: str, payload: Dict, timeout: Optional[float] = None) -> Dict:
    if requests is None:
        raise RuntimeError("requests is not installed. Run: pip install requests")
    kwargs = {"json": payload, "headers": {"Content-Type": "application/json"}}
    if timeout is not None:
        kwargs["timeout"] = timeout
    response = requests.post(server_url, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Simulate RimSpace production mission: Make 1 Clothes.")
        parser.add_argument("--server", default="http://127.0.0.1:5000/GetInstruction", help="LLM server endpoint")
        parser.add_argument("--agents", default="Farmer,Crafter,Chef", help="Comma-separated agent names")
        parser.add_argument("--rounds", type=int, default=10, help="Number of rounds (each round = all agents act once)")
        parser.add_argument("--timeout", type=float, default=None, help="HTTP timeout in seconds")
        parser.add_argument("--print-state", action="store_true", help="Print world state after each round")
        parser.add_argument("--print-inventory", action="store_true", help="Print each actor inventory after each round")
        parser.add_argument("--degradation", type=int, default=10, help="Hunger/Energy degradation per round")
        parser.add_argument("--interactive", action="store_true", help="Wait for 'n' input after each round")
        parser.add_argument("--task", action="store_true", help="Auto-run until TaskList is empty (no interaction needed)")
        args = parser.parse_args()

        world = SimWorld(build_default_world())
        agent_list = [a.strip() for a in args.agents.split(",") if a.strip()]

        print("=" * 70, flush=True)
        print("  Production Mission: Make 1 Clothes (ID: 3001)", flush=True)
        print("=" * 70, flush=True)
        print(f"  Agents: {', '.join(agent_list)}", flush=True)
        if args.task:
            print(f"  Mode: Auto-run (stops when TaskList is empty)", flush=True)
        else:
            print(f"  Mode: Interactive (press 'n' + Enter to advance each round)", flush=True)
        print(f"  Stats degradation per round: {args.degradation}", flush=True)
        print("=" * 70, flush=True)
        print(flush=True)

        round_num = 1
        auto_advance = 0
        while True:
            # 在 --task 模式下，如果没有待执行的任务，停止模拟
            if args.task:
                if not world.has_pending_tasks():
                    print(f"\n[Task Check] No pending tasks found, stopping simulation...", flush=True)
                    break
                else:
                    pending_info = []
                    for actor in world.environment.get("Actors", []):
                        task_list = actor.get("TaskList", {})
                        if isinstance(task_list, dict) and task_list:
                            pending_info.append(f"{actor.get('ActorName')}: {task_list}")
                    if pending_info:
                        print(f"[Task Check] Pending tasks: {', '.join(pending_info)}", flush=True)
            
            print(f"\n[===== ROUND {round_num} =====]", flush=True)
            print(f"Time: {world.time.formatted()}", flush=True)
            
            # 每轮中的每个 agent 请求一次
            for agent in agent_list:
                payload = world.build_request(agent)
                print(f"  [{agent}] Requesting...", flush=True)
                try:
                    decision = _send_request(args.server, payload, args.timeout)
                except Exception as exc:
                    print(f"  [{agent}] Request failed: {exc}", flush=True)
                    return 1
                world.apply_command(agent, decision)
                cmd_type = decision.get("CommandType", "Wait")
                target = decision.get("TargetName", "")
                print(f"  [{agent}] -> {cmd_type} {target}", flush=True)

            # 每轮结束后，降低所有角色的 Hunger 和 Energy
            world.degrade_character_stats(args.degradation)
            # 每轮结束后，作物生长推进
            world.tick_environment(12)
            
            # 输出当前角色状态
            print(f"\n  [Character Stats after round {round_num}]:", flush=True)
            for char in world.characters.get("Characters", []):
                name = char.get("CharacterName")
                hunger = char.get("CharacterStats", {}).get("Hunger", 0)
                energy = char.get("CharacterStats", {}).get("Energy", 0)
                print(f"    {name}: Hunger={hunger:.1f}, Energy={energy:.1f}", flush=True)

            if args.print_inventory:
                print(f"\n  [Actor Inventories after round {round_num}]", flush=True)
                for actor in world.environment.get("Actors", []):
                    actor_name = actor.get("ActorName", "Unknown")
                    inv = actor.get("Inventory", {})
                    if isinstance(inv, dict) and inv:
                        print(f"    {actor_name}: {inv}", flush=True)
                    else:
                        print(f"    {actor_name}: (empty)", flush=True)

            # 可选：打印完整世界状态
            if args.print_state:
                snapshot = {
                    "GameTime": world.time.formatted(),
                    "Environment": world.environment,
                    "Characters": world.characters,
                }
                print("\n  [World State]:", flush=True)
                print(json.dumps(snapshot, indent=4), flush=True)

            # 在 --task 模式下自动继续，否则等待用户输入
            if args.task:
                round_num += 1
            else:
                if auto_advance > 0:
                    auto_advance -= 1
                    round_num += 1
                    continue

                print(f"\n  Press 'n' + Enter to continue to Round {round_num + 1}, 'nX' to run X rounds, or 'q' + Enter to quit...", flush=True)
                while True:
                    user_input = input().strip().lower()
                    if user_input.startswith('n'):
                        count_text = user_input[1:].strip()
                        if not count_text:
                            advance_count = 1
                        else:
                            try:
                                advance_count = int(count_text)
                            except ValueError:
                                advance_count = 0
                        if advance_count <= 0:
                            print("  Invalid input. Use 'n' or 'nX' with a positive number, or 'q' to quit: ", flush=True)
                            continue
                        auto_advance = max(0, advance_count - 1)
                        round_num += 1
                        break
                    elif user_input == 'q':
                        print("\n" + "=" * 70, flush=True)
                        print("  Simulation Stopped by User", flush=True)
                        print("=" * 70, flush=True)
                        return 0
                    else:
                        print("  Invalid input. Use 'n' or 'nX' with a positive number, or 'q' to quit: ", flush=True)

        # 模拟完成
        print("\n" + "=" * 70, flush=True)
        if args.task:
            print("  Simulation Completed: All tasks finished!", flush=True)
            print(f"  Final Time: {world.time.formatted()}", flush=True)
            print(f"  Total Rounds: {round_num - 1}", flush=True)
        else:
            print("  Simulation Stopped by User", flush=True)
            print(f"  Final Time: {world.time.formatted()}", flush=True)
            print(f"  Total Rounds: {round_num - 1}", flush=True)
        print("=" * 70, flush=True)
        return 0
    
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


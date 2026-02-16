import argparse
import copy
import json
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
                    cultivate_info["CurrentPhase"] = "ECultivatePhase::ECP_WaitingToPlant"
                    cultivate_info["CurrentCultivateType"] = "ECultivateType::ECT_None"
            elif "WorkStation" in actor_type or "Stove" in actor_type:
                task_list = actor.setdefault("TaskList", {})
                task_key = str(param_id)
                if task_key in task_list:
                    task_list[task_key] = max(0, int(task_list[task_key]) - 1)
                    if task_list[task_key] == 0:
                        task_list.pop(task_key, None)
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


def build_default_world() -> Dict:
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
                    "Inventory": {},
                    "TaskList": {"2001": 2},
                },
                {"ActorName": "Stove", "ActorType": "EInteractionType::EAT_Stove", "Inventory": {}},
                {"ActorName": "Storage", "ActorType": "EInteractionType::EAT_Storage", "Inventory": {"1001": 10}},
                {"ActorName": "Table", "ActorType": "EInteractionType::EAT_Table"},
                {"ActorName": "Bed_1", "ActorType": "EInteractionType::EAT_Bed"},
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
                        "Hunger": 95.0,
                        "MaxHunger": 100.0,
                        "Energy": 95.0,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanFarm"],
                },
                {
                    "CharacterName": "Crafter",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Thinking",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 95.0,
                        "MaxHunger": 100.0,
                        "Energy": 95.0,
                        "MaxEnergy": 100.0,
                    },
                    "CharacterSkills": ["CanCraft"],
                },
                {
                    "CharacterName": "Chef",
                    "CurrentLocation": "None",
                    "ActionState": "ECharacterActionState::Thinking",
                    "Inventory": {},
                    "CharacterStats": {
                        "Hunger": 95.0,
                        "MaxHunger": 100.0,
                        "Energy": 95.0,
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
    parser = argparse.ArgumentParser(description="Simulate RimSpace world and call LLM server.")
    parser.add_argument("--server", default="http://127.0.0.1:5000/GetInstruction", help="LLM server endpoint")
    parser.add_argument("--agents", default="Farmer", help="Comma-separated agent names")
    parser.add_argument("--steps", type=int, default=5, help="Number of steps to simulate")
    parser.add_argument("--timeout", type=float, default=None, help="HTTP timeout in seconds")
    parser.add_argument("--print-state", action="store_true", help="Print world state after each step")
    args = parser.parse_args()

    world = SimWorld(build_default_world())
    agent_list = [a.strip() for a in args.agents.split(",") if a.strip()]

    for step in range(1, args.steps + 1):
        for agent in agent_list:
            payload = world.build_request(agent)
            print(f"[Step {step}] Sending request for {agent}...", flush=True)
            try:
                decision = _send_request(args.server, payload, args.timeout)
            except Exception as exc:
                print(f"[Step {step}] Request failed: {exc}", flush=True)
                return 1
            world.apply_command(agent, decision)
            print(
                f"[Step {step}] {agent} -> {decision.get('CommandType')} {decision.get('TargetName', '')}",
                flush=True,
            )
        if args.print_state:
            snapshot = {
                "GameTime": world.time.formatted(),
                "Environment": world.environment,
                "Characters": world.characters,
            }
            print(json.dumps(snapshot, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())

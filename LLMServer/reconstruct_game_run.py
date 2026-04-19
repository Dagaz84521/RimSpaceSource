import argparse
import ast
import copy
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from sim_production_mission import SimWorld, build_default_world


DECISION_RE = re.compile(r"^\[(?P<role>[^\]]+?)\s+决策\]\s+(?P<payload>\{.*\})\s*$")
COAT_GOAL_RE = re.compile(r"Make\s+(?P<count>\d+)\D+Coat", re.IGNORECASE)
MEAL_GOAL_RE = re.compile(r"Make\s+(?P<count>\d+)\D+Meal", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay RimSpace server decisions and reconstruct world-state changes."
    )
    parser.add_argument("--input", required=True, help="Path to server log file")
    parser.add_argument(
        "--output-json",
        default=None,
        help="Output path for replay timeline JSON. Default: <input_basename>_replay.json",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Output path for world-change markdown report. Default: <input_basename>_replay.md",
    )
    parser.add_argument(
        "--meal-goal",
        type=int,
        default=None,
        help="Initial meal task goal. If omitted, try infer from log; fallback to 3.",
    )
    parser.add_argument(
        "--coat-goal",
        type=int,
        default=None,
        help="Initial coat task goal. If omitted, try infer from log; fallback to 3.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="If > 0, limit markdown output to first N replay steps.",
    )
    parser.add_argument(
        "--include-no-change",
        action="store_true",
        help="Include no-op steps in markdown output.",
    )
    parser.add_argument(
        "--agents-order",
        default="Farmer,Crafter,Chef",
        help="Comma-separated agent order used to detect round end.",
    )
    parser.add_argument(
        "--round-degradation",
        type=int,
        default=10,
        help="Hunger/Energy degradation applied at each round end.",
    )
    parser.add_argument(
        "--round-tick-minutes",
        type=int,
        default=12,
        help="Environment growth tick minutes applied at each round end.",
    )
    return parser.parse_args()


def _safe_literal_eval(payload_str: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        parsed = ast.literal_eval(payload_str)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "payload is not a dict"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _normalize_count(value: Any) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return 0


def _extract_decisions(log_path: str) -> List[Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.rstrip("\n")
            match = DECISION_RE.match(line)
            if not match:
                continue

            payload_str = match.group("payload")
            payload, parse_error = _safe_literal_eval(payload_str)
            if payload is None:
                payload = {
                    "CharacterName": match.group("role"),
                    "CommandType": "Wait",
                    "TargetName": "",
                    "ParamID": 1,
                    "Count": 0,
                    "_parse_error": parse_error,
                    "_raw": payload_str,
                }

            decisions.append(
                {
                    "line_no": line_no,
                    "character": str(payload.get("CharacterName", match.group("role"))).strip(),
                    "command": {
                        "CommandType": str(payload.get("CommandType", "Wait")),
                        "TargetName": str(payload.get("TargetName", "")),
                        "ParamID": _normalize_count(payload.get("ParamID", 0)),
                        "Count": _normalize_count(payload.get("Count", 0)),
                    },
                    "remaining_steps": payload.get("RemainingSteps"),
                    "raw_payload": payload,
                }
            )
    return decisions


def _infer_goals_from_log(log_path: str) -> Tuple[int, int]:
    meal_goal: Optional[int] = None
    coat_goal: Optional[int] = None

    with open(log_path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if coat_goal is None:
                coat_match = COAT_GOAL_RE.search(line)
                if coat_match:
                    coat_goal = int(coat_match.group("count"))
            if meal_goal is None:
                meal_match = MEAL_GOAL_RE.search(line)
                if meal_match:
                    meal_goal = int(meal_match.group("count"))
            if meal_goal is not None and coat_goal is not None:
                break

    return (meal_goal or 3, coat_goal or 3)


def _collect_world_state(world: SimWorld) -> Dict[str, Any]:
    actor_inventory: Dict[str, Dict[str, int]] = {}
    actor_tasklist: Dict[str, Dict[str, int]] = {}
    actor_cultivate: Dict[str, Dict[str, Any]] = {}
    for actor in world.environment.get("Actors", []):
        name = actor.get("ActorName", "Unknown")
        inv = actor.get("Inventory", {})
        if isinstance(inv, dict):
            actor_inventory[name] = {str(k): int(v) for k, v in inv.items() if int(v) != 0}
        else:
            actor_inventory[name] = {}

        task_list = actor.get("TaskList", {})
        if isinstance(task_list, dict):
            actor_tasklist[name] = {str(k): int(v) for k, v in task_list.items() if int(v) != 0}
        else:
            actor_tasklist[name] = {}

        cultivate_info = actor.get("CultivateInfo", {})
        if isinstance(cultivate_info, dict):
            actor_cultivate[name] = {
                "CurrentPhase": str(cultivate_info.get("CurrentPhase", "")),
                "CurrentCultivateType": str(cultivate_info.get("CurrentCultivateType", "")),
                "TargetCultivateType": str(cultivate_info.get("TargetCultivateType", "")),
                "GrowthProgress": _normalize_count(cultivate_info.get("GrowthProgress", 0)),
            }

    char_location: Dict[str, str] = {}
    char_inventory: Dict[str, Dict[str, int]] = {}
    for char in world.characters.get("Characters", []):
        name = char.get("CharacterName", "Unknown")
        char_location[name] = str(char.get("CurrentLocation", "None"))
        inv = char.get("Inventory", {})
        if isinstance(inv, dict):
            char_inventory[name] = {str(k): int(v) for k, v in inv.items() if int(v) != 0}
        else:
            char_inventory[name] = {}

    return {
        "time": world.time.formatted(),
        "actor_inventory": actor_inventory,
        "actor_tasklist": actor_tasklist,
        "actor_cultivate": actor_cultivate,
        "char_location": char_location,
        "char_inventory": char_inventory,
    }


def _diff_map(
    before: Dict[str, Dict[str, int]], after: Dict[str, Dict[str, int]]
) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    all_keys = sorted(set(before.keys()) | set(after.keys()))
    for owner in all_keys:
        b_inv = before.get(owner, {})
        a_inv = after.get(owner, {})
        item_delta: Dict[str, int] = {}
        all_items = sorted(set(b_inv.keys()) | set(a_inv.keys()))
        for item_id in all_items:
            delta = int(a_inv.get(item_id, 0)) - int(b_inv.get(item_id, 0))
            if delta != 0:
                item_delta[item_id] = delta
        if item_delta:
            result[owner] = item_delta
    return result


def _diff_locations(before: Dict[str, str], after: Dict[str, str]) -> List[Dict[str, str]]:
    changes: List[Dict[str, str]] = []
    for name in sorted(set(before.keys()) | set(after.keys())):
        b = before.get(name, "None")
        a = after.get(name, "None")
        if b != a:
            changes.append({"character": name, "from": b, "to": a})
    return changes


def _diff_cultivate(
    before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    for actor in sorted(set(before.keys()) | set(after.keys())):
        b = before.get(actor, {})
        a = after.get(actor, {})
        for field in ["CurrentPhase", "CurrentCultivateType", "GrowthProgress"]:
            b_val = b.get(field)
            a_val = a.get(field)
            if b_val != a_val:
                changes.append(
                    {
                        "actor": actor,
                        "field": field,
                        "from": b_val,
                        "to": a_val,
                    }
                )
    return changes

def _replay_world(
    log_path: str,
    meal_goal: int,
    coat_goal: int,
    agents_order: List[str],
    round_degradation: int,
    round_tick_minutes: int,
) -> Dict[str, Any]:
    decisions = _extract_decisions(log_path)
    world = SimWorld(build_default_world(meal_goal=meal_goal, coat_goal=coat_goal))

    steps: List[Dict[str, Any]] = []
    changed_steps = 0
    round_no = 0
    order_idx = 0

    def _append_event(
        event_type: str,
        payload: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> None:
        nonlocal changed_steps
        actor_inv_delta = _diff_map(before["actor_inventory"], after["actor_inventory"])
        actor_task_delta = _diff_map(before["actor_tasklist"], after["actor_tasklist"])
        char_inv_delta = _diff_map(before["char_inventory"], after["char_inventory"])
        location_changes = _diff_locations(before["char_location"], after["char_location"])
        cultivate_changes = _diff_cultivate(before["actor_cultivate"], after["actor_cultivate"])
        changed = bool(
            actor_inv_delta
            or actor_task_delta
            or char_inv_delta
            or location_changes
            or cultivate_changes
        )
        if changed:
            changed_steps += 1

        steps.append(
            {
                "event_type": event_type,
                "changed": changed,
                "time_before": before["time"],
                "time_after": after["time"],
                "location_changes": location_changes,
                "actor_inventory_delta": actor_inv_delta,
                "actor_tasklist_delta": actor_task_delta,
                "character_inventory_delta": char_inv_delta,
                "cultivate_changes": cultivate_changes,
                "snapshot_after": {
                    "char_location": copy.deepcopy(after["char_location"]),
                    "actor_inventory": copy.deepcopy(after["actor_inventory"]),
                    "char_inventory": copy.deepcopy(after["char_inventory"]),
                    "actor_tasklist": copy.deepcopy(after["actor_tasklist"]),
                },
                **payload,
            }
        )

    for idx, event in enumerate(decisions, start=1):
        if agents_order:
            expected = agents_order[order_idx]
            if event["character"] != expected and order_idx > 0:
                before_round = _collect_world_state(world)
                world.degrade_character_stats(round_degradation)
                world.tick_environment(round_tick_minutes)
                after_round = _collect_world_state(world)
                round_no += 1
                _append_event(
                    "round_end",
                    {
                        "round": round_no,
                        "reason": "order_reset",
                    },
                    before_round,
                    after_round,
                )
                order_idx = 0

        before = _collect_world_state(world)
        world.apply_command(event["character"], event["command"])
        after = _collect_world_state(world)
        _append_event(
            "decision",
            {
                "step": idx,
                "line_no": event["line_no"],
                "character": event["character"],
                "command": event["command"],
                "remaining_steps": event.get("remaining_steps"),
            },
            before,
            after,
        )

        if agents_order:
            expected = agents_order[order_idx]
            if event["character"] == expected:
                order_idx += 1
                if order_idx >= len(agents_order):
                    before_round = _collect_world_state(world)
                    world.degrade_character_stats(round_degradation)
                    world.tick_environment(round_tick_minutes)
                    after_round = _collect_world_state(world)
                    round_no += 1
                    _append_event(
                        "round_end",
                        {
                            "round": round_no,
                            "reason": "round_complete",
                        },
                        before_round,
                        after_round,
                    )
                    order_idx = 0

    final_state = _collect_world_state(world)

    return {
        "source_log": os.path.abspath(log_path),
        "initial_goals": {"meal_goal": meal_goal, "coat_goal": coat_goal},
        "stats": {
            "decision_events": len(decisions),
            "total_events": len(steps),
            "round_end_events": round_no,
            "changed_steps": changed_steps,
            "no_change_steps": len(steps) - changed_steps,
        },
        "steps": steps,
        "final_state": final_state,
    }


def _format_delta(delta: Dict[str, int]) -> str:
    parts: List[str] = []
    for item_id, value in sorted(delta.items()):
        sign = "+" if value > 0 else ""
        parts.append(f"{item_id}:{sign}{value}")
    return ", ".join(parts)


def build_markdown_report(data: Dict[str, Any], max_events: int = 0, include_no_change: bool = False) -> str:
    steps = data["steps"]
    stats = data["stats"]

    if not include_no_change:
        visible_steps = [
            s for s in steps if s.get("changed") or s.get("event_type") == "round_end"
        ]
    else:
        visible_steps = steps

    if max_events > 0:
        shown = visible_steps[:max_events]
        clipped = len(visible_steps) - len(shown)
    else:
        shown = visible_steps
        clipped = 0

    lines: List[str] = []
    lines.append("# World Replay")
    lines.append("")
    lines.append(f"- Source Log: {data['source_log']}")
    lines.append(
        f"- Initial Goals: meal={data['initial_goals']['meal_goal']}, coat={data['initial_goals']['coat_goal']}"
    )
    lines.append(f"- Decision Events: {stats['decision_events']}")
    lines.append(f"- Round-End Events: {stats.get('round_end_events', 0)}")
    lines.append(f"- Total Events: {stats.get('total_events', len(steps))}")
    lines.append(f"- Changed Steps: {stats['changed_steps']}")
    lines.append(f"- No-Change Steps: {stats['no_change_steps']}")
    lines.append("")
    lines.append("## Event Replay")

    if not shown:
        lines.append("- No world-state changes found.")
    else:
        for s in shown:
            if s.get("event_type") == "decision":
                cmd = s["command"]
                cmd_text = (
                    f"{cmd.get('CommandType', 'Wait')} target={cmd.get('TargetName', '')} "
                    f"param={cmd.get('ParamID', 0)} count={cmd.get('Count', 0)}"
                )
                lines.append(
                    f"- [Decision] Step {s['step']} (line {s['line_no']}) | {s['character']} | {cmd_text} | {s['time_before']} -> {s['time_after']}"
                )
            else:
                lines.append(
                    f"- [RoundEnd] Round {s.get('round', '?')} ({s.get('reason', '')}) | {s['time_before']} -> {s['time_after']}"
                )

            for loc in s.get("location_changes", []):
                lines.append(
                    f"  - Location: {loc['character']} {loc['from']} -> {loc['to']}"
                )

            for owner, delta in sorted(s.get("actor_inventory_delta", {}).items()):
                lines.append(f"  - ActorInv[{owner}]: {_format_delta(delta)}")

            for owner, delta in sorted(s.get("actor_tasklist_delta", {}).items()):
                lines.append(f"  - ActorTask[{owner}]: {_format_delta(delta)}")

            for owner, delta in sorted(s.get("character_inventory_delta", {}).items()):
                lines.append(f"  - CharInv[{owner}]: {_format_delta(delta)}")

            for c in s.get("cultivate_changes", []):
                lines.append(
                    f"  - Cultivate[{c['actor']}].{c['field']}: {c['from']} -> {c['to']}"
                )

            snapshot = s.get("snapshot_after", {})
            char_locs = snapshot.get("char_location", {})
            if char_locs:
                loc_text = ", ".join(f"{n}:{v}" for n, v in sorted(char_locs.items()))
                lines.append(f"  - Snapshot CharacterLocation: {loc_text}")
            actor_inv = snapshot.get("actor_inventory", {})
            if actor_inv:
                inv_text = ", ".join(
                    f"{owner}={inv if inv else '{}'}" for owner, inv in sorted(actor_inv.items())
                )
                lines.append(f"  - Snapshot ActorInventory: {inv_text}")
            char_inv = snapshot.get("char_inventory", {})
            if char_inv:
                c_inv_text = ", ".join(
                    f"{owner}={inv if inv else '{}'}" for owner, inv in sorted(char_inv.items())
                )
                lines.append(f"  - Snapshot CharacterInventory: {c_inv_text}")

            if not s.get("changed"):
                lines.append("  - No state change")

    if clipped > 0:
        lines.append("")
        lines.append(f"- ... {clipped} more step(s) hidden by --max-events")

    lines.append("")
    lines.append("## Final State")
    lines.append(f"- Time: {data['final_state']['time']}")
    lines.append("- Character Locations:")
    for name, loc in sorted(data["final_state"]["char_location"].items()):
        lines.append(f"  - {name}: {loc}")
    lines.append("- Actor Inventories:")
    for owner, inv in sorted(data["final_state"]["actor_inventory"].items()):
        lines.append(f"  - {owner}: {inv if inv else '{}'}")
    lines.append("- Actor TaskList:")
    for owner, task_list in sorted(data["final_state"]["actor_tasklist"].items()):
        lines.append(f"  - {owner}: {task_list if task_list else '{}'}")

    return "\n".join(lines) + "\n"


def default_output_paths(input_path: str) -> Tuple[str, str]:
    abs_input = os.path.abspath(input_path)
    base, _ = os.path.splitext(abs_input)
    return f"{base}_replay.json", f"{base}_replay.md"


def resolve_input_path(input_arg: str) -> str:
    candidates = [
        input_arg,
        os.path.join("..", "Log", input_arg),
        os.path.join("Log", input_arg),
    ]
    for c in candidates:
        abs_path = os.path.abspath(c)
        if os.path.exists(abs_path):
            return abs_path
    return os.path.abspath(input_arg)


def main() -> None:
    args = parse_args()
    input_path = resolve_input_path(args.input)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input log not found: {input_path}")

    inferred_meal, inferred_coat = _infer_goals_from_log(input_path)
    meal_goal = args.meal_goal if args.meal_goal is not None else inferred_meal
    coat_goal = args.coat_goal if args.coat_goal is not None else inferred_coat
    agents_order = [x.strip() for x in args.agents_order.split(",") if x.strip()]

    default_json, default_md = default_output_paths(input_path)
    output_json = os.path.abspath(args.output_json) if args.output_json else default_json
    output_md = os.path.abspath(args.output_md) if args.output_md else default_md

    data = _replay_world(
        input_path,
        meal_goal=meal_goal,
        coat_goal=coat_goal,
        agents_order=agents_order,
        round_degradation=args.round_degradation,
        round_tick_minutes=args.round_tick_minutes,
    )

    with open(output_json, "w", encoding="utf-8") as f_json:
        json.dump(data, f_json, ensure_ascii=False, indent=2)

    report = build_markdown_report(
        data,
        max_events=args.max_events,
        include_no_change=args.include_no_change,
    )
    with open(output_md, "w", encoding="utf-8") as f_md:
        f_md.write(report)

    print(f"[OK] replay json: {output_json}")
    print(f"[OK] replay markdown: {output_md}")
    print(
        "[INFO] decisions: "
        f"{data['stats']['decision_events']}, changed_steps: {data['stats']['changed_steps']}"
    )


if __name__ == "__main__":
    main()

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any

import requests

from sim_production_mission import SimWorld, build_default_world


ROOT_DIR = os.path.dirname(__file__)
RESULT_ROOT = os.path.join(ROOT_DIR, "ablation_results")


@dataclass
class EpisodeMetrics:
    mode: str
    episode: int
    success: int
    rounds: int
    total_commands: int
    wait_commands: int
    wait_rate: float
    skill_errors: int
    transport_no_item: int
    transport_no_item_wait: int
    intent_total: int
    intent_errors: int
    intent_accuracy: float


@dataclass
class SummaryMetrics:
    mode: str
    episodes: int
    completion_rate: float
    avg_rounds_success: float
    avg_wait_rate: float
    avg_intent_accuracy: float
    avg_skill_errors: float
    avg_transport_no_item: float
    avg_transport_no_item_wait: float


@dataclass
class IntentIssue:
    mode: str
    episode: int
    round: int
    agent: str
    error_type: str
    command_type: str
    high_command: str
    target_name: str
    source: str
    destination: str
    item_id: int
    count: int
    current_location: str
    detail: str


def _post_json(server_url: str, payload: Dict, timeout: float) -> Dict:
    try:
        response = requests.post(
            server_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        body = exc.response.text if exc.response is not None else ""
        body = body.strip().replace("\n", " ")
        if len(body) > 600:
            body = body[:600] + "..."
        raise RuntimeError(
            f"HTTP {status} from server (timeout={timeout}s). response={body}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"HTTP request failed (timeout={timeout}s): {type(exc).__name__}: {exc}") from exc


def _get_json(url: str, timeout: float = 2.0) -> Dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _find_char(world: SimWorld, name: str) -> Dict:
    for c in world.characters.get("Characters", []):
        if c.get("CharacterName") == name:
            return c
    return {}


def _find_actor(world: SimWorld, name: str) -> Dict:
    for a in world.environment.get("Actors", []):
        if a.get("ActorName") == name:
            return a
    return {}


def _facility_skill_required(actor_type: str) -> str:
    if "CultivateChamber" in actor_type:
        return "canfarm"
    if "Stove" in actor_type:
        return "cancook"
    if "WorkStation" in actor_type:
        return "cancraft"
    return ""


def _collect_intent_errors(
    world: SimWorld,
    agent_name: str,
    decision: Dict,
    counts: Dict[str, int],
    issues: List[Dict[str, Any]],
    mode: str,
    episode: int,
    round_idx: int,
) -> None:
    cmd_type = decision.get("CommandType", "Wait")
    counts["intent_total"] += 1

    char = _find_char(world, agent_name)
    skills = {s.lower() for s in (char.get("CharacterSkills", []) or [])}
    decision_meta = decision.get("Decision", {}) if isinstance(decision.get("Decision", {}), dict) else {}
    high_command = str(decision_meta.get("command", "")).strip().lower()

    def _push_issue(error_type: str, detail: str) -> None:
        issues.append(
            asdict(
                IntentIssue(
                    mode=mode,
                    episode=episode,
                    round=round_idx,
                    agent=agent_name,
                    error_type=error_type,
                    command_type=str(cmd_type),
                    high_command=high_command,
                    target_name=str(decision.get("TargetName", "")),
                    source=str(decision_meta.get("source", "")),
                    destination=str(decision_meta.get("destination", "")),
                    item_id=int(decision.get("ParamID", 0) or 0),
                    count=int(decision.get("Count", 0) or 0),
                    current_location=str(char.get("CurrentLocation", "")),
                    detail=detail,
                )
            )
        )

    if cmd_type == "Use":
        actor = _find_actor(world, char.get("CurrentLocation", ""))
        actor_type = actor.get("ActorType", "")
        required = _facility_skill_required(actor_type)
        if required and required not in skills:
            counts["skill_errors"] += 1
            _push_issue(
                "skill_error",
                f"required={required}; actor_type={actor_type}; skills={sorted(list(skills))}",
            )

    if cmd_type == "Take":
        actor = _find_actor(world, char.get("CurrentLocation", ""))
        inv = actor.get("Inventory", {}) if isinstance(actor, dict) else {}
        param_id = str(int(decision.get("ParamID", 0)))
        take_count = int(decision.get("Count", 1))
        if inv.get(param_id, 0) < take_count:
            counts["transport_no_item"] += 1
            _push_issue(
                "transport_no_item",
                f"location={char.get('CurrentLocation', '')}; item={param_id}; need={take_count}; have={inv.get(param_id, 0)}",
            )

    if cmd_type == "Wait":
        reasoning = (
            str(decision_meta.get("reasoning", ""))
            + " "
            + str(decision_meta.get("thought", ""))
        ).lower()
        no_item_keywords = ["no item", "could not locate", "资源", "缺", "不足", "missing"]
        if high_command == "transport" and any(k in reasoning for k in no_item_keywords):
            counts["transport_no_item_wait"] += 1
            _push_issue("transport_no_item_wait", "wait with high-level transport due to missing items")


def _run_episode(
    mode: str,
    episode_idx: int,
    server_url: str,
    agents: List[str],
    max_rounds: int,
    degradation: int,
    timeout: float,
    stall_rounds: int,
    meal_goal: int,
    coat_goal: int,
) -> EpisodeMetrics:
    world = SimWorld(build_default_world(meal_goal=meal_goal, coat_goal=coat_goal))

    rounds = 0
    total_commands = 0
    wait_commands = 0
    counts = {
        "skill_errors": 0,
        "transport_no_item": 0,
        "transport_no_item_wait": 0,
        "intent_total": 0,
    }
    issues: List[Dict[str, Any]] = []

    success = 0
    consecutive_all_wait_rounds = 0
    for _ in range(max_rounds):
        rounds += 1
        round_waits = 0
        if not world.has_pending_tasks():
            success = 1
            break

        print(f"[{mode}] ep={episode_idx} round={rounds}/{max_rounds} ...", flush=True)

        for agent in agents:
            payload = world.build_request(agent)
            try:
                decision = _post_json(server_url, payload, timeout)
            except Exception as exc:
                print(
                    f"[{mode}] ep={episode_idx} round={rounds} agent={agent} request_failed: {exc}",
                    flush=True,
                )
                intent_errors = counts["skill_errors"] + counts["transport_no_item"] + counts["transport_no_item_wait"]
                wait_rate = (wait_commands / total_commands) if total_commands > 0 else 0.0
                intent_accuracy = 1.0 - (intent_errors / counts["intent_total"]) if counts["intent_total"] > 0 else 1.0
                return EpisodeMetrics(
                    mode=mode,
                    episode=episode_idx,
                    success=0,
                    rounds=rounds,
                    total_commands=total_commands,
                    wait_commands=wait_commands,
                    wait_rate=wait_rate,
                    skill_errors=counts["skill_errors"],
                    transport_no_item=counts["transport_no_item"],
                    transport_no_item_wait=counts["transport_no_item_wait"],
                    intent_total=counts["intent_total"],
                    intent_errors=intent_errors,
                    intent_accuracy=intent_accuracy,
                )

            total_commands += 1
            if decision.get("CommandType", "Wait") == "Wait":
                wait_commands += 1
                round_waits += 1

            _collect_intent_errors(
                world,
                agent,
                decision,
                counts,
                issues,
                mode,
                episode_idx,
                rounds,
            )
            world.apply_command(agent, decision)

        world.degrade_character_stats(degradation)
        world.tick_environment(12)

        if round_waits == len(agents):
            consecutive_all_wait_rounds += 1
        else:
            consecutive_all_wait_rounds = 0

        if stall_rounds > 0 and consecutive_all_wait_rounds >= stall_rounds:
            print(
                f"[{mode}] ep={episode_idx} early-stop: all agents waited for {consecutive_all_wait_rounds} consecutive rounds",
                flush=True,
            )
            break

        if not world.has_pending_tasks():
            success = 1
            break

    if success == 0 and not world.has_pending_tasks():
        success = 1

    intent_errors = counts["skill_errors"] + counts["transport_no_item"] + counts["transport_no_item_wait"]
    wait_rate = (wait_commands / total_commands) if total_commands > 0 else 0.0
    intent_accuracy = 1.0 - (intent_errors / counts["intent_total"]) if counts["intent_total"] > 0 else 1.0

    metrics = EpisodeMetrics(
        mode=mode,
        episode=episode_idx,
        success=success,
        rounds=rounds,
        total_commands=total_commands,
        wait_commands=wait_commands,
        wait_rate=wait_rate,
        skill_errors=counts["skill_errors"],
        transport_no_item=counts["transport_no_item"],
        transport_no_item_wait=counts["transport_no_item_wait"],
        intent_total=counts["intent_total"],
        intent_errors=intent_errors,
        intent_accuracy=intent_accuracy,
    )
    setattr(metrics, "intent_issues", issues)
    return metrics


def _summarize(mode: str, episodes: List[EpisodeMetrics]) -> SummaryMetrics:
    n = len(episodes)
    success_eps = [e for e in episodes if e.success == 1]
    completion_rate = sum(e.success for e in episodes) / n if n else 0.0
    avg_rounds_success = (sum(e.rounds for e in success_eps) / len(success_eps)) if success_eps else 0.0
    avg_wait_rate = sum(e.wait_rate for e in episodes) / n if n else 0.0
    avg_intent_accuracy = sum(e.intent_accuracy for e in episodes) / n if n else 0.0
    avg_skill_errors = sum(e.skill_errors for e in episodes) / n if n else 0.0
    avg_transport_no_item = sum(e.transport_no_item for e in episodes) / n if n else 0.0
    avg_transport_no_item_wait = sum(e.transport_no_item_wait for e in episodes) / n if n else 0.0
    return SummaryMetrics(
        mode=mode,
        episodes=n,
        completion_rate=completion_rate,
        avg_rounds_success=avg_rounds_success,
        avg_wait_rate=avg_wait_rate,
        avg_intent_accuracy=avg_intent_accuracy,
        avg_skill_errors=avg_skill_errors,
        avg_transport_no_item=avg_transport_no_item,
        avg_transport_no_item_wait=avg_transport_no_item_wait,
    )


def _wait_server_ready(base_url: str, timeout_s: float = 30.0) -> None:
    health_url = base_url.replace("/GetInstruction", "/health")
    start = time.time()
    last_err = ""
    while time.time() - start < timeout_s:
        try:
            data = _get_json(health_url, timeout=2.0)
            if data.get("status") in {"running", "ok"}:
                return
        except Exception as exc:
            last_err = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"Server not ready after {timeout_s}s: {last_err}")


def _spawn_server(
    mode: str,
    full_basic_tasks: bool,
    full_disable_filter: bool,
    no_blackboard_basic_tasks: bool,
    no_blackboard_disable_filter: bool,
    server_log_path: str,
) -> subprocess.Popen:
    env = os.environ.copy()
    env["RIMSPACE_SERVER_DEBUG"] = "0"
    env["RIMSPACE_ABLATION_MODE"] = mode
    env["RIMSPACE_SERVER_LOG_PATH"] = server_log_path

    if mode == "full":
        env["RIMSPACE_BB_BASIC_TASKS"] = "1" if full_basic_tasks else "0"
        env["RIMSPACE_BB_DISABLE_FILTER"] = "1" if full_disable_filter else "0"
        env["RIMSPACE_LLM_TASK_SOURCE"] = "all"
    else:
        # no_blackboard 默认策略：仅使用 Perceiver 的基础任务，且不做过滤
        env["RIMSPACE_BB_BASIC_TASKS"] = "1"
        env["RIMSPACE_BB_DISABLE_FILTER"] = "1"
        env["RIMSPACE_LLM_TASK_SOURCE"] = "perceiver"

    return subprocess.Popen(
        [sys.executable, "llm_server.py"],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        # On Windows, sending CTRL_BREAK_EVENT may propagate to the current console group
        # and terminate this runner itself. Use terminate/kill for isolated shutdown.
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _write_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ablation runner for configurable chain goals (Meal/Coat).")
    parser.add_argument("--server", default="http://127.0.0.1:5000/GetInstruction", help="Server endpoint")
    parser.add_argument("--modes", default="full,no_blackboard", help="Comma-separated modes")
    parser.add_argument("--episodes", type=int, default=5, help="Episodes per mode")
    parser.add_argument("--max-rounds", type=int, default=40, help="Max rounds per episode")
    parser.add_argument("--agents", default="Farmer,Crafter,Chef", help="Agent order")
    parser.add_argument("--degradation", type=int, default=0, help="Hunger/Energy degradation per round")
    parser.add_argument("--meal-goal", type=int, default=1, help="Target Meal count in Stove TaskList")
    parser.add_argument("--coat-goal", type=int, default=1, help="Target Coat count in WorkStation TaskList")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout (s)")
    parser.add_argument(
        "--stall-rounds",
        type=int,
        default=6,
        help="Early-stop an episode as failure after N consecutive all-agent Wait rounds (0 to disable).",
    )
    parser.add_argument(
        "--full-basic-tasks",
        action="store_true",
        help="In full mode, use only basic perceived tasks (disable planner subtask decomposition).",
    )
    parser.add_argument(
        "--full-disable-filter",
        action="store_true",
        help="In full mode, disable blackboard task filtering.",
    )
    parser.add_argument(
        "--no-bb-basic-tasks",
        action="store_true",
        help="In no_blackboard mode, keep basic task posting switch on (mostly for debugging).",
    )
    parser.add_argument(
        "--no-bb-disable-filter",
        action="store_true",
        help="In no_blackboard mode, keep filter-disable switch on (mostly for debugging).",
    )
    args = parser.parse_args()

    modes = [m.strip().lower() for m in args.modes.split(",") if m.strip()]
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    chain_tag = f"meal{max(0, args.meal_goal)}_coat{max(0, args.coat_goal)}"
    out_dir = os.path.join(RESULT_ROOT, f"bb_ablation_{chain_tag}_{ts}")
    os.makedirs(out_dir, exist_ok=True)

    all_episode_rows: List[Dict] = []
    summary_rows: List[Dict] = []
    log_index_rows: List[Dict] = []
    all_intent_issues: List[Dict] = []
    role_issue_summary_rows: List[Dict] = []

    for mode in modes:
        print(f"\n=== Running mode: {mode} ===", flush=True)
        episode_metrics: List[EpisodeMetrics] = []
        for ep in range(1, args.episodes + 1):
            server_log_path = os.path.join(out_dir, f"server_{mode}_ep{ep:03d}.log")
            print(f"[{mode}] ep={ep} server_log={server_log_path}", flush=True)
            server_proc = _spawn_server(
                mode=mode,
                full_basic_tasks=args.full_basic_tasks,
                full_disable_filter=args.full_disable_filter,
                no_blackboard_basic_tasks=args.no_bb_basic_tasks,
                no_blackboard_disable_filter=args.no_bb_disable_filter,
                server_log_path=server_log_path,
            )
            try:
                _wait_server_ready(args.server, timeout_s=30.0)
                m = _run_episode(
                    mode=mode,
                    episode_idx=ep,
                    server_url=args.server,
                    agents=agents,
                    max_rounds=args.max_rounds,
                    degradation=args.degradation,
                    timeout=args.timeout,
                    stall_rounds=args.stall_rounds,
                    meal_goal=args.meal_goal,
                    coat_goal=args.coat_goal,
                )
                episode_metrics.append(m)
                all_episode_rows.append(asdict(m))
                episode_issues = getattr(m, "intent_issues", [])
                all_intent_issues.extend(episode_issues)

                # 每回合按角色/错误类型聚合一行，方便快速看是谁出错
                role_counter: Dict[str, Dict[str, int]] = {}
                for issue in episode_issues:
                    role = issue.get("agent", "Unknown")
                    et = issue.get("error_type", "unknown")
                    role_counter.setdefault(role, {})
                    role_counter[role][et] = role_counter[role].get(et, 0) + 1
                for role, mcount in role_counter.items():
                    role_issue_summary_rows.append(
                        {
                            "mode": mode,
                            "episode": ep,
                            "agent": role,
                            "skill_error": mcount.get("skill_error", 0),
                            "transport_no_item": mcount.get("transport_no_item", 0),
                            "transport_no_item_wait": mcount.get("transport_no_item_wait", 0),
                            "total_issues": sum(mcount.values()),
                        }
                    )
                log_index_rows.append(
                    {
                        "mode": mode,
                        "episode": ep,
                        "server_log": server_log_path,
                        "success": m.success,
                        "rounds": m.rounds,
                        "wait_rate": m.wait_rate,
                        "intent_accuracy": m.intent_accuracy,
                    }
                )
                print(
                    f"[{mode}] ep={ep} success={m.success} rounds={m.rounds} "
                    f"wait={m.wait_rate:.3f} intent_acc={m.intent_accuracy:.3f} "
                    f"skill_err={m.skill_errors} no_item={m.transport_no_item} no_item_wait={m.transport_no_item_wait}",
                    flush=True,
                )
                if episode_issues:
                    top = episode_issues[:5]
                    print(f"[{mode}] ep={ep} issue_samples={len(episode_issues)} (showing {len(top)})", flush=True)
                    for it in top:
                        print(
                            f"    - r{it['round']} {it['agent']} {it['error_type']} cmd={it['command_type']} "
                            f"src={it['source']} dst={it['destination']} detail={it['detail']}",
                            flush=True,
                        )
            finally:
                _stop_server(server_proc)

        summary = _summarize(mode, episode_metrics)
        summary_rows.append(asdict(summary))
        print(
            f"[{mode}] completion={summary.completion_rate:.3f} "
            f"avg_rounds_success={summary.avg_rounds_success:.2f} "
            f"avg_wait={summary.avg_wait_rate:.3f} avg_intent_acc={summary.avg_intent_accuracy:.3f}",
            flush=True,
        )

    _write_csv(os.path.join(out_dir, "episode_metrics.csv"), all_episode_rows)
    _write_csv(os.path.join(out_dir, "summary_metrics.csv"), summary_rows)
    _write_csv(os.path.join(out_dir, "log_index.csv"), log_index_rows)
    _write_csv(os.path.join(out_dir, "intent_issues.csv"), all_intent_issues)
    _write_csv(os.path.join(out_dir, "intent_issues_by_role.csv"), role_issue_summary_rows)

    with open(os.path.join(out_dir, "summary_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "log_index.json"), "w", encoding="utf-8") as f:
        json.dump(log_index_rows, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "intent_issues.json"), "w", encoding="utf-8") as f:
        json.dump(all_intent_issues, f, ensure_ascii=False, indent=2)

    with open(os.path.join(out_dir, "intent_issues_by_role.json"), "w", encoding="utf-8") as f:
        json.dump(role_issue_summary_rows, f, ensure_ascii=False, indent=2)

    print(f"\nSaved results to: {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

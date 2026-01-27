import json
import time
import requests
import sys
from datetime import datetime

# 模拟世界状态：Storage 只有原材料 Cotton，Crafter 需要从头生产衣服
# 生产链：
#   1. Cotton x5 -> Thread (需要生产3次得到 Thread x3)
#   2. Cotton x5 -> Cloth (需要生产2次得到 Cloth x2)
#   3. Cloth x2 + Thread x3 -> Coat

class Logger:
    """同时输出到控制台和文件的日志类"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')
        
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        self.log.close()

def build_initial_world():
    return {
        "TargetAgent": "Crafter",
        "GameTime": "08:00",
        "Environment": [
            {
                "ActorName": "Storage_A",
                "Type": "Storage",
                "Inventory": {
                    "items": [
                        {"name": "Cotton", "count": 100}  # 足够的原材料
                    ]
                }
            },
            {
                "ActorName": "WorkStation_1",
                "Type": "WorkStation",
                "Inventory": {"items": []}
            }
        ],
        "Characters": [
            {
                "Name": "Crafter",
                "State": "Idle",
                "Location": "Storage_A",
                "Skills": {"CanCook": False, "CanCraft": True, "CanFarm": False},
                "CharacterStats": {"Hunger": 60.0, "Energy": 80.0},
                "Inventory": []
            }
        ],
        "Task": "Craft Coat from raw Cotton. You need to first craft Thread and Cloth from Cotton, then combine them to make Coat."
    }


def apply_command(world, cmd):
    """将动作应用到世界状态（简化模拟），返回执行反馈"""
    c = next((c for c in world["Characters"] if c["Name"] == world["TargetAgent"]), None)
    storage = next((a for a in world["Environment"] if a["ActorName"] == "Storage_A"), None)
    workstation = next((a for a in world["Environment"] if a["ActorName"] == "WorkStation_1"), None)
    
    if not c:
        return "ERROR: Character not found"

    def inv_get(inv_list, name):
        for it in inv_list:
            if it.get("name") == name:
                return it
        return None

    def inv_count(inv_list, name):
        it = inv_get(inv_list, name)
        return it["count"] if it else 0

    def inv_add(inv_list, name, count):
        it = inv_get(inv_list, name)
        if it:
            it["count"] += count
        else:
            inv_list.append({"name": name, "count": count})

    def inv_remove(inv_list, name, count):
        it = inv_get(inv_list, name)
        if it:
            it["count"] = max(0, it["count"] - count)
            if it["count"] == 0:
                inv_list[:] = [x for x in inv_list if x.get("name") != name]

    cmd_type = cmd.get("CommandType", "")
    target = cmd.get("TargetName", "")
    param_id = cmd.get("ParamID", 0)
    count = cmd.get("Count", 0)
    item_map = {1001: "Cotton", 1002: "Corn", 2001: "Thread", 2002: "Cloth", 2003: "Meal", 3001: "Coat"}

    if cmd_type == "Take":
        # 从目标容器拿取物品到角色背包
        target_actor = next((a for a in world["Environment"] if a["ActorName"] == target), None)
        if target_actor:
            if param_id == 0:
                print(f"    [警告] Take 命令的 ParamID=0 无效，已忽略")
                return "FAILED: Take command requires a valid ParamID (ItemID)"
            item_name = item_map.get(param_id)
            if not item_name:
                print(f"    [警告] Take 命令的 ParamID={param_id} 未知物品ID，已忽略")
                return f"FAILED: Unknown ItemID {param_id}"
            actual_count = min(count, inv_count(target_actor["Inventory"]["items"], item_name))
            if actual_count > 0:
                inv_remove(target_actor["Inventory"]["items"], item_name, actual_count)
                inv_add(c["Inventory"], item_name, actual_count)
                return f"SUCCESS: Took {actual_count}x {item_name} from {target}. Your inventory now has {inv_count(c['Inventory'], item_name)}x {item_name}."
            else:
                print(f"    [警告] {target} 中没有 {item_name}，无法执行 Take")
                return f"FAILED: {target} has no {item_name} to take"
                
    elif cmd_type == "Move":
        c["Location"] = target
        return f"SUCCESS: Moved to {target}. You are now at {target}."
        
    elif cmd_type == "Put":
        # 将背包中的物品放入目标容器
        target_actor = next((a for a in world["Environment"] if a["ActorName"] == target), None)
        if target_actor:
            if param_id == 0:
                print(f"    [警告] Put 命令的 ParamID=0 无效，已忽略")
                return "FAILED: Put command requires a valid ParamID (ItemID of item in YOUR inventory)"
            item_name = item_map.get(param_id)
            if not item_name:
                print(f"    [警告] Put 命令的 ParamID={param_id} 未知物品ID，已忽略")
                return f"FAILED: Unknown ItemID {param_id}"
            actual_count = min(count, inv_count(c["Inventory"], item_name))
            if actual_count > 0:
                inv_remove(c["Inventory"], item_name, actual_count)
                inv_add(target_actor["Inventory"]["items"], item_name, actual_count)
                return f"SUCCESS: Put {actual_count}x {item_name} into {target}. {target} now has {inv_count(target_actor['Inventory']['items'], item_name)}x {item_name}."
            else:
                print(f"    [警告] 背包中没有 {item_name}，无法执行 Put")
                # 提供更有用的反馈
                inv_items = [f"{it['name']}x{it['count']}" for it in c["Inventory"]]
                inv_str = ", ".join(inv_items) if inv_items else "empty"
                facility_items = [f"{it['name']}x{it['count']}" for it in target_actor["Inventory"]["items"]]
                facility_str = ", ".join(facility_items) if facility_items else "empty"
                return f"FAILED: Your inventory has no {item_name}! Your inventory is: [{inv_str}]. {target} already has: [{facility_str}]. If {target} already has materials, you should Use a recipe instead of Put!"
        return f"FAILED: Target {target} not found"
                
    elif cmd_type == "Use":
        # 根据 TaskID (ParamID) 执行配方
        # TaskID 2001: Cotton x5 -> Thread x1
        # TaskID 2002: Cotton x5 -> Cloth x1
        # TaskID 3001: Cloth x2 + Thread x3 -> Coat x1
        if workstation and c["Location"] == workstation["ActorName"]:
            ws_inv = workstation["Inventory"]["items"]
            if param_id == 2001:  # 生产棉线
                if inv_count(ws_inv, "Cotton") >= 5:
                    inv_remove(ws_inv, "Cotton", 5)
                    inv_add(c["Inventory"], "Thread", 1)
                    print("    [配方执行] Cotton x5 -> Thread x1")
                    return f"SUCCESS: Crafted 1x Thread! WorkStation now has {inv_count(ws_inv, 'Cotton')}x Cotton remaining. Your inventory now has {inv_count(c['Inventory'], 'Thread')}x Thread."
                else:
                    return f"FAILED: Not enough Cotton in WorkStation. Need 5, have {inv_count(ws_inv, 'Cotton')}."
            elif param_id == 2002:  # 生产布料
                if inv_count(ws_inv, "Cotton") >= 5:
                    inv_remove(ws_inv, "Cotton", 5)
                    inv_add(c["Inventory"], "Cloth", 1)
                    print("    [配方执行] Cotton x5 -> Cloth x1")
                    return f"SUCCESS: Crafted 1x Cloth! WorkStation now has {inv_count(ws_inv, 'Cotton')}x Cotton remaining. Your inventory now has {inv_count(c['Inventory'], 'Cloth')}x Cloth."
                else:
                    return f"FAILED: Not enough Cotton in WorkStation. Need 5, have {inv_count(ws_inv, 'Cotton')}."
            elif param_id == 3001:  # 生产衣服
                if inv_count(ws_inv, "Cloth") >= 2 and inv_count(ws_inv, "Thread") >= 3:
                    inv_remove(ws_inv, "Cloth", 2)
                    inv_remove(ws_inv, "Thread", 3)
                    inv_add(c["Inventory"], "Coat", 1)
                    print("    [配方执行] Cloth x2 + Thread x3 -> Coat x1")
                    return f"SUCCESS: Crafted 1x Coat! Task complete!"
                else:
                    return f"FAILED: Not enough materials in WorkStation. Need 2 Cloth + 3 Thread, have {inv_count(ws_inv, 'Cloth')} Cloth + {inv_count(ws_inv, 'Thread')} Thread."
            else:
                return f"FAILED: Unknown TaskID {param_id}"
        else:
            return f"FAILED: Must be at WorkStation to use recipe. Current location: {c['Location']}"
    
    elif cmd_type == "Wait":
        return "SUCCESS: Waited."
    
    else:
        return f"FAILED: Unknown command type {cmd_type}"


def print_world_state(world, step_label=""):
    """输出当前世界状态"""
    print(f"\n{'='*50}")
    print(f"世界状态 {step_label}")
    print(f"{'='*50}")
    print(f"游戏时间: {world['GameTime']}")
    
    print("\n【环境】")
    for actor in world["Environment"]:
        items_str = ", ".join(
            f"{it['name']}x{it['count']}" for it in actor["Inventory"]["items"]
        ) or "(空)"
        print(f"  - {actor['ActorName']} ({actor['Type']}): {items_str}")
    
    print("\n【角色】")
    for char in world["Characters"]:
        inv_str = ", ".join(
            f"{it['name']}x{it['count']}" for it in char["Inventory"]
        ) or "(空)"
        print(f"  - {char['Name']}")
        print(f"      状态: {char['State']}, 位置: {char['Location']}")
        print(f"      饥饿: {char['CharacterStats']['Hunger']}, 精力: {char['CharacterStats']['Energy']}")
        print(f"      背包: {inv_str}")
    print(f"{'='*50}\n")


def run_test(base_url="http://localhost:5000", max_steps=30):
    # 设置日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"test_crafter_coat_{timestamp}.log"
    logger = Logger(log_filename)
    sys.stdout = logger
    
    print(f"日志文件: {log_filename}")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    world = build_initial_world()
    results = []
    current_belief = None
    last_feedback = None  # 上一个命令的执行反馈

    print("\n" + "="*60)
    print("测试：Crafter 从原材料生产衣服")
    print("="*60)
    print("生产链：")
    print("  1. Cotton x5 -> Thread (需要3次)")
    print("  2. Cotton x5 -> Cloth (需要2次)")
    print("  3. Cloth x2 + Thread x3 -> Coat")
    print("="*60)
    
    print_world_state(world, "(初始状态)")

    success = False
    try:
        for i in range(max_steps):
            # 将上一次的信念加入请求
            if current_belief:
                world["Belief"] = current_belief
            elif "Belief" in world:
                del world["Belief"]
            
            # 将上一个命令的执行反馈加入请求
            if last_feedback:
                world["LastActionFeedback"] = last_feedback
            elif "LastActionFeedback" in world:
                del world["LastActionFeedback"]
            
            # 打印发送给服务器的完整请求
            print(f"\n{'='*60}")
            print(f">>> Step {i+1} - 发送请求")
            print(f"{'='*60}")
            print("请求 JSON:")
            print(json.dumps(world, indent=2, ensure_ascii=False))
            
            try:
                r = requests.post(f"{base_url}/GetInstruction", json=world, timeout=120)
                r.raise_for_status()
                cmd = r.json()
            except Exception as e:
                print(f"请求失败: {e}")
                break
            
            # 打印服务器返回的完整响应
            print(f"\n响应 JSON:")
            print(json.dumps(cmd, indent=2, ensure_ascii=False))
            
            # 提取并保存新的信念
            current_belief = cmd.get("Belief", None)
            
            print(f"\n>>> Step {i+1} - 解析结果")
            print(f"    Command: {cmd.get('CommandType')} | Target: {cmd.get('TargetName')} | ParamID: {cmd.get('ParamID')} | Count: {cmd.get('Count')}")
            if current_belief:
                print(f"    Belief:")
                print(f"      Goal: {current_belief.get('Goal', 'N/A')}")
                print(f"      Completed: {current_belief.get('Completed', 'N/A')}")
                print(f"      NextSteps: {current_belief.get('NextSteps', 'N/A')}")
            
            results.append({
                "step": i + 1,
                "command": cmd.get("CommandType"),
                "target": cmd.get("TargetName"),
                "paramID": cmd.get("ParamID"),
                "count": cmd.get("Count"),
                "belief": current_belief
            })
            
            # 执行命令并获取反馈
            last_feedback = apply_command(world, cmd)
            print(f"    执行反馈: {last_feedback}")
            print_world_state(world, f"(Step {i+1} 执行后)")
            
            # 检查是否成功生产了衣服
            crafter = next((c for c in world["Characters"] if c["Name"] == "Crafter"), None)
            if crafter:
                has_coat = any(it["name"] == "Coat" for it in crafter["Inventory"])
                if has_coat:
                    print("\n" + "="*60)
                    print("✓ 成功生产衣服！")
                    print(f"✓ 总共执行了 {i+1} 步")
                    print("="*60)
                    print("\n执行步骤回顾：")
                    for r in results:
                        print(f"  Step {r['step']}: {r['command']} -> {r['target']} (ParamID: {r['paramID']}, Count: {r['count']})")
                    success = True
                    break
            
            time.sleep(0.5)

        if not success:
            print("\n" + "="*60)
            print("✗ 测试失败：未能在最大步数内生产衣服")
            print("="*60)
            print("\n执行步骤回顾：")
            for r in results:
                print(f"  Step {r['step']}: {r['command']} -> {r['target']} (ParamID: {r['paramID']}, Count: {r['count']})")
                
    finally:
        print(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"日志已保存到: {log_filename}")
        sys.stdout = logger.terminal
        logger.close()
    
    return success


if __name__ == "__main__":
    run_test()

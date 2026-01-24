import json
import time
import requests

# 模拟世界状态：Storage 资源充足，Chef 在 Storage

def build_initial_world():
    return {
        "TargetAgent": "Chef",
        "GameTime": "08:00",
        "Environment": [
            {
                "ActorName": "Storage_A",
                "Type": "Storage",
                "Inventory": {
                    "items": [
                        {"name": "Corn", "count": 100},
                        {"name": "Cotton", "count": 50}
                    ]
                }
            },
            {
                "ActorName": "Stove_1",
                "Type": "Stove",
                "Inventory": {"items": []}
            }
        ],
        "Characters": [
            {
                "Name": "Chef",
                "State": "Idle",
                "Location": "Storage_A",
                "Skills": {"CanCook": True, "CanCraft": True},
                "CharacterStats": {"Hunger": 50.0, "Energy": 80.0},
                "Inventory": []
            }
        ]
    }


def apply_command(world, cmd):
    """将动作应用到世界状态（简化模拟）"""
    c = next((c for c in world["Characters"] if c["Name"] == world["TargetAgent"]), None)
    storage = next((a for a in world["Environment"] if a["ActorName"] == "Storage_A"), None)
    stove = next((a for a in world["Environment"] if a["ActorName"] == "Stove_1"), None)
    
    if not c:
        return

    def inv_get(inv_list, name):
        for it in inv_list:
            if it.get("name") == name:
                return it
        return None

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

    # 设定本测试目标配方：制作套餐 (Corn x5 -> Meal)
    needed_name = "Corn"
    needed_count = 5

    if cmd["CommandType"] == "Take":
        if storage:
            inv_remove(storage["Inventory"]["items"], needed_name, needed_count)
            inv_add(c["Inventory"], needed_name, needed_count)
    elif cmd["CommandType"] == "Move":
        c["Location"] = cmd.get("TargetName", "Stove_1")
    elif cmd["CommandType"] == "Put":
        inv_remove(c["Inventory"], needed_name, needed_count)
        if stove:
            inv_add(stove["Inventory"]["items"], needed_name, needed_count)
    elif cmd["CommandType"] == "Use":
        # 简化：在 Kitchen 使用配方后生成 Meal 到角色背包
        inv_add(c["Inventory"], "Meal", 1)
    else:
        pass


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


def run_test(base_url="http://localhost:5000"):
    world = build_initial_world()
    expected = ["Take", "Move", "Put", "Use"]
    results = []
    current_belief = None  # 保存上一次的信念

    print_world_state(world, "(初始状态)")

    for i in range(4):
        # 将上一次的信念加入请求
        if current_belief:
            world["Belief"] = current_belief
        elif "Belief" in world:
            del world["Belief"]
        
        r = requests.post(f"{base_url}/GetInstruction", json=world, timeout=30)
        r.raise_for_status()
        cmd = r.json()
        
        # 提取并保存新的信念
        current_belief = cmd.get("Belief", None)
        
        print(f"\nStep {i+1} -> Command: {cmd.get('CommandType')} | Target: {cmd.get('TargetName')}")
        if current_belief:
            print(f"  Belief:")
            print(f"    Goal: {current_belief.get('Goal', 'N/A')}")
            print(f"    Completed: {current_belief.get('Completed', 'N/A')}")
            print(f"    NextSteps: {current_belief.get('NextSteps', 'N/A')}")
        
        results.append(cmd.get("CommandType"))
        apply_command(world, cmd)
        print_world_state(world, f"(Step {i+1} 执行后)")
        time.sleep(0.2)

    ok = results == expected
    print("Expected:", expected)
    print("Got:", results)
    if not ok:
        raise AssertionError("指令顺序不匹配！")
    print("测试通过：指令顺序为 Take -> Move -> Put -> Use")


if __name__ == "__main__":
    run_test()

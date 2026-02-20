import argparse
import os
import re
from collections import defaultdict

def parse_args():
    parser = argparse.ArgumentParser(
        description="Split a RimSpace log into per-role files based on [GetInstruction] markers."
    )
    parser.add_argument(
        "--input",
        default=os.path.join(os.path.dirname(__file__), "..", "log.log"),
        help="Path to log file. Default: ../log.log",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for role logs. Default: <input_dir>/role_split",
    )
    parser.add_argument(
        "--filters",
        default="[GetInstruction],[决策],[Blackboard]",
        help="Comma-separated tags to keep.",
    )
    return parser.parse_args()

def should_include(line, filters):
    return any(tag in line for tag in filters)

def is_blackboard_list_item(line):
    return re.match(r"^\s+\d+\.\s+", line) is not None

def main():
    args = parse_args()
    input_path = os.path.abspath(args.input)
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(input_path), "role_split")

    filters = [f.strip() for f in args.filters.split(",") if f.strip()]

    role_re = re.compile(r"\[GetInstruction\]\s*角色:\s*([^,，\s]+)")
    role_buffers = defaultdict(list)
    current_role = None
    in_blackboard_block = False

    with open(input_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            role_match = role_re.search(line)
            if role_match:
                current_role = role_match.group(1)
                in_blackboard_block = False

            if should_include(line, filters):
                if current_role is None:
                    role_buffers["Global"].append(line)
                else:
                    role_buffers[current_role].append(line)
                in_blackboard_block = "[Blackboard]" in line
                continue

            if in_blackboard_block and is_blackboard_list_item(line):
                if current_role is None:
                    role_buffers["Global"].append(line)
                else:
                    role_buffers[current_role].append(line)
            else:
                in_blackboard_block = False

    os.makedirs(output_dir, exist_ok=True)
    for role, lines in role_buffers.items():
        safe_role = re.sub(r"[^A-Za-z0-9_-]+", "_", role)
        out_path = os.path.join(output_dir, f"{safe_role}.log")
        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write("\n".join(lines))
            out_f.write("\n")

    print(f"Wrote {len(role_buffers)} role file(s) to: {output_dir}")

if __name__ == "__main__":
    main()

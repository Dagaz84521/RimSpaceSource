import argparse
import sys

import requests

from game_state_for_test import game_state


def _pick_character_name(target: str) -> str:
	if target:
		return target
	characters = game_state.get("Characters", {}).get("Characters", [])
	if not characters:
		return ""
	return characters[0].get("CharacterName", "")


def build_payload(character_name: str) -> dict:
	payload = {
		"RequestType": "GetInstruction",
		"TargetAgent": character_name,
		"GameTime": "Day 1  06:00",
		"Environment": game_state.get("Environment", {}),
		"Characters": game_state.get("Characters", {}),
	}
	return payload


def main() -> int:
	parser = argparse.ArgumentParser(description="Send game_state to llm_server")
	parser.add_argument("--name", dest="character_name", help="CharacterName to query")
	parser.add_argument("--url", default="http://127.0.0.1:5000/GetInstruction")
	args = parser.parse_args()

	character_name = _pick_character_name(args.character_name)
	if not character_name:
		print("No CharacterName found in game_state.")
		return 2

	payload = build_payload(character_name)
	resp = requests.post(args.url, json=payload, timeout=30)
	print(resp.status_code)
	print(resp.text)
	return 0


if __name__ == "__main__":
	sys.exit(main())


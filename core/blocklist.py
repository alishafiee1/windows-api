import os
from config import BLOCKLIST_PATH


def load_blocklist() -> list[str]:
    if not os.path.exists(BLOCKLIST_PATH):
        return []
    with open(BLOCKLIST_PATH, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    return [
        line.strip().lower()
        for line in lines
        if line.strip() and not line.startswith('#')
    ]


def is_dangerous(cmd: str) -> bool:
    rules = load_blocklist()
    cmd_lower = cmd.lower()
    return any(rule in cmd_lower for rule in rules)


def get_blocklist() -> list[str]:
    return load_blocklist()
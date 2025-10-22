import json
import re
from typing import Dict, List, Tuple

from .models import Rule


def load_rules_from_json(path: str) -> Tuple[List[Rule], Dict[str, Rule]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    levels = data.get("levels", [])
    rules: List[Rule] = []
    rule_map: Dict[str, Rule] = {}
    for item in levels:
        if not item.get("enabled", True):
            continue
        rule = Rule(
            id=item["id"],
            name=item.get("name", item["id"]),
            level=int(item["level"]),
            enabled=True,
            optional=bool(item.get("optional", False)),
            priority=int(item.get("priority", 0)),
            pattern=item["pattern"],
            numbering_normalize=list(item.get("numbering", {}).get("normalize", ["arabic"])),
            numbering_continuity=str(item.get("numbering", {}).get("continuity", "strict_increase")),
            children=list(item.get("children", [])),
        )
        # validate regex early
        re.compile(rule.pattern)
        rules.append(rule)
        rule_map[rule.id] = rule
    # 按 level 和 priority 排序，便于栈构建时稳定
    rules.sort(key=lambda r: (r.level, -r.priority))
    return rules, rule_map




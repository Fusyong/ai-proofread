from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Rule:
    id: str
    name: str
    level: int
    enabled: bool
    optional: bool
    priority: int
    pattern: str
    numbering_normalize: List[str]
    numbering_continuity: str  # "strict_increase" | "increase_or_restart" | "none"
    children: List[str]


@dataclass
class Token:
    start: int
    end: int
    rule_id: str
    level: int
    priority: int
    raw_text: str
    number_value: Optional[int] = None


@dataclass
class Node:
    token: Token
    children: List["Node"] = field(default_factory=list)
    parent: Optional["Node"] = None

    @property
    def level(self) -> int:
        return self.token.level

    @property
    def rule_id(self) -> str:
        return self.token.rule_id


@dataclass
class Diagnostic:
    kind: str  # e.g., "overlap_discard", "hierarchy_gap", "continuity_error", "level_mismatch"
    message: str
    position: Tuple[int, int]
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Result:
    root_nodes: List[Node]
    diagnostics: List[Diagnostic]




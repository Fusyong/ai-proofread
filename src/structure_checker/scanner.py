import re
from typing import List, Tuple

from .models import Diagnostic, Rule, Token
from .numbering import normalize_number


def scan_text(text: str, rules: List[Rule]) -> Tuple[List[Token], List[Diagnostic]]:
    tokens: List[Token] = []
    diags: List[Diagnostic] = []
    for rule in rules:
        pattern = re.compile(rule.pattern, re.MULTILINE)
        for m in pattern.finditer(text):
            groups = m.groupdict()
            num_val = normalize_number(groups, rule.numbering_normalize)
            tok = Token(
                start=m.start(),
                end=m.end(),
                rule_id=rule.id,
                level=rule.level,
                priority=rule.priority,
                raw_text=m.group(0),
                number_value=num_val,
            )
            tokens.append(tok)

    tokens.sort(key=lambda t: (t.start, -t.priority, -(t.end - t.start)))
    tokens, overlap_diags = _resolve_overlaps(tokens)
    diags.extend(overlap_diags)
    return tokens, diags


def _resolve_overlaps(tokens: List[Token]) -> Tuple[List[Token], List[Diagnostic]]:
    if not tokens:
        return tokens, []
    result: List[Token] = []
    diags: List[Diagnostic] = []
    current_group: List[Token] = []

    def commit_group(group: List[Token]):
        if not group:
            return
        # 选择保留：优先级高 -> 跨度长 -> 起点早
        best = sorted(group, key=lambda t: (-t.priority, -(t.end - t.start), t.start))[0]
        result.append(best)
        for t in group:
            if t is not best:
                diags.append(Diagnostic(
                    kind="overlap_discard",
                    message=f"重叠冲突：丢弃 {t.rule_id} 于 [{t.start},{t.end})，保留 {best.rule_id}",
                    position=(t.start, t.end),
                    extra={"kept": best.rule_id, "discarded": t.rule_id},
                ))

    # 扫描分组：有重叠的归为一组
    # group_start 保留用于将来更复杂的分组策略（当前未使用）
    _group_start = tokens[0].start
    group_end = tokens[0].end
    current_group = [tokens[0]]
    for t in tokens[1:]:
        if t.start < group_end:  # overlap
            current_group.append(t)
            if t.end > group_end:
                group_end = t.end
        else:
            commit_group(current_group)
            current_group = [t]
            _group_start = t.start
            group_end = t.end
    commit_group(current_group)

    result.sort(key=lambda t: t.start)
    return result, diags



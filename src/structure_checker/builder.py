from typing import Dict, List, Tuple

from .models import Diagnostic, Node, Rule, Token


def build_tree(tokens: List[Token], _rule_map: Dict[str, Rule]) -> Tuple[List[Node], List[Diagnostic]]:
    _ = _rule_map  # 防止未使用参数告警，后续可用于跨级合法性校验
    nodes: List[Node] = [Node(token=t) for t in tokens]
    diags: List[Diagnostic] = []
    roots: List[Node] = []
    stack: List[Node] = []

    for node in nodes:
        # 清理无效 number 的情况：不致命，后续连续性检查会处理
        while stack and node.level <= stack[-1].level:
            stack.pop()
        if not stack:
            roots.append(node)
            stack.append(node)
        else:
            parent = stack[-1]
            parent.children.append(node)
            node.parent = parent
            stack.append(node)
    return roots, diags


def validate_continuity(roots: List[Node], rule_map: Dict[str, Rule]) -> List[Diagnostic]:
    diags: List[Diagnostic] = []

    def dfs(parent: Node):
        if not parent.children:
            return
        # 在同一父节点下检查连续性
        # 将同层的子节点按 rule_id 分桶，分别检查
        buckets: Dict[str, List[Node]] = {}
        for c in parent.children:
            buckets.setdefault(c.rule_id, []).append(c)

        for rid, items in buckets.items():
            rule = rule_map[rid]
            prev = None
            seq = []
            for n in items:
                seq.append((n, n.token.number_value))
                if rule.numbering_continuity == "none":
                    continue
                if n.token.number_value is None:
                    diags.append(Diagnostic(
                        kind="number_missing",
                        message=f"{rule.name} 缺少可解析编号",
                        position=(n.token.start, n.token.end),
                        extra={"rule": rid, "text": n.token.raw_text},
                    ))
                    continue
                if prev is None:
                    prev = n.token.number_value
                else:
                    curr = n.token.number_value
                    if rule.numbering_continuity == "strict_increase":
                        if curr != prev + 1:
                            diags.append(Diagnostic(
                                kind="continuity_error",
                                message=f"{rule.name} 编号不连续：{prev} → {curr}",
                                position=(n.token.start, n.token.end),
                                extra={"rule": rid, "prev": prev, "curr": curr},
                            ))
                        prev = curr
                    elif rule.numbering_continuity == "increase_or_restart":
                        if not (curr == 1 or curr == (prev + 1)):
                            diags.append(Diagnostic(
                                kind="continuity_error",
                                message=f"{rule.name} 需递增或重启为1：{prev} → {curr}",
                                position=(n.token.start, n.token.end),
                                extra={"rule": rid, "prev": prev, "curr": curr},
                            ))
                        prev = curr

        for c in parent.children:
            dfs(c)

    # 构造一个虚拟根，便于统一处理多根情况
    virtual = Node(token=_virtual_token())
    virtual.children = roots
    for r in roots:
        r.parent = virtual
    dfs(virtual)
    return diags


def _virtual_token():
    # 简易的虚拟 token，用于校验遍历
    from .models import Token as _T
    return _T(start=-1, end=-1, rule_id="__root__", level=0, priority=0, raw_text="__root__")



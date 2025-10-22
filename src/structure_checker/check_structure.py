import argparse
from typing import List

from .rules import load_rules_from_json
from .scanner import scan_text
from .builder import build_tree, validate_continuity
from .report import render_html, render_json
from .models import Result


def check_text_with_rules(text: str, rules_path: str) -> Result:
    rules, rule_map = load_rules_from_json(rules_path)
    tokens, diags = scan_text(text, rules)
    roots, build_diags = build_tree(tokens, rule_map)
    diags.extend(build_diags)
    diags.extend(validate_continuity(roots, rule_map))
    return Result(root_nodes=roots, diagnostics=diags)


def main(argv: List[str] = None):
    parser = argparse.ArgumentParser(description="中文文本层级结构检查")
    parser.add_argument("input", help="输入文本文件")
    parser.add_argument("rules", help="规则 JSON 文件")
    parser.add_argument("--out-html", dest="out_html", default="report.structure.html", help="输出 HTML 报告路径")
    parser.add_argument("--out-json", dest="out_json", default="report.structure.json", help="输出 JSON 报告路径")
    args = parser.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    result = check_text_with_rules(text, args.rules)
    render_json(result.root_nodes, result.diagnostics, args.out_json)
    render_html(text, result.root_nodes, result.diagnostics, args.out_html)

    print(f"已输出: {args.out_html}\n已输出: {args.out_json}")


if __name__ == "__main__":
    main()




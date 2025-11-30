"""结构检查示例脚本
"""
import os

from src.structure_checker.check_structure import check_text_with_rules
from src.structure_checker.report import render_html, render_json


def main():
    """主函数 
    """
    args_out_dir = "work"
    args_rules = "src/structure_checker/rules.example.json"
    args_input = "example2/your_markdown.md"
    os.makedirs(args_out_dir, exist_ok=True)

    with open(args_input, "r", encoding="utf-8") as f:
        text = f.read()

    result = check_text_with_rules(text, args_rules)

    out_html = os.path.join(args_out_dir, "report.structure.html")
    out_json = os.path.join(args_out_dir, "report.structure.json")

    render_json(result.root_nodes, result.diagnostics, out_json)
    render_html(text, result.root_nodes, result.diagnostics, out_html)

    print(f"已输出: {out_html}")
    print(f"已输出: {out_json}")


if __name__ == "__main__":
    main()



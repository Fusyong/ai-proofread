"""
从 .mdictlist 中列出的各 mdict 词典提取所有词条词头，按词头统计出现的词典数量，输出为 CSV（词头, 出现的词典数量）。

用法:
  python -m src.extract_mdict_headwords [--list path] [--out path]
  或在项目根目录:
  python reliable-proofreading-data/extract_mdict_headwords.py --list src/resource/.mdictlist --out reliable-proofreading-data/mdict_headwords.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys


def _should_include_headword(hw: str) -> bool:
    """返回 False 表示应忽略该词条。忽略：含数字（含上标如¹）、含拉丁字母、仅一个字符。"""
    s = hw.strip()
    if len(s) < 2:
        return False
    for c in s:
        if c.isdigit():  # 含 0-9 及上标数字 ¹²³ 等
            return False
        if "a" <= c <= "z" or "A" <= c <= "Z":
            return False
    return True


def _project_root() -> str:
    """返回项目根目录（包含 src 或 pyproject.toml 的目录）。"""
    start = os.path.dirname(os.path.abspath(__file__))
    while start:
        if os.path.basename(start) == "src":
            return os.path.dirname(start)
        if os.path.exists(os.path.join(start, "pyproject.toml")):
            return start
        parent = os.path.dirname(start)
        if parent == start:
            break
        start = parent
    return os.getcwd()


def main() -> None:
    parser = argparse.ArgumentParser(description="从 mdictlist 词典列表提取词头并输出 CSV")
    parser.add_argument(
        "--list",
        "-l",
        default="src/resource/.mdictlist",
        help=".mdictlist 文件路径（默认: src/resource/.mdictlist）",
    )
    parser.add_argument(
        "--out",
        "-o",
        default="mdict_headwords.csv",
        help="输出 CSV 文件路径（默认: mdict_headwords.csv）",
    )
    parser.add_argument(
        "--encoding",
        "-e",
        default="utf-8",
        help="mdict 词典编码（默认: utf-8）",
    )
    args = parser.parse_args()

    root = _project_root()
    list_path = os.path.join(root, args.list) if not os.path.isabs(args.list) else args.list
    out_path = os.path.join(root, args.out) if not os.path.isabs(args.out) else args.out

    if not os.path.exists(list_path):
        print(f"错误：未找到词典列表文件 {list_path}", file=sys.stderr)
        sys.exit(1)

    # 读取词典路径列表，跳过空行
    with open(list_path, "r", encoding="utf-8") as f:
        mdx_paths = [line.strip() for line in f if line.strip()]

    try:
        from src.special_checker.mdict import MdictDatabase
    except ImportError:
        try:
            from special_checker.mdict import MdictDatabase
        except ImportError:
            print("错误：无法导入 MdictDatabase，请从项目根目录运行或安装包。", file=sys.stderr)
            sys.exit(1)

    # 词头 -> 出现过的词典名集合
    headword_dicts: dict[str, set[str]] = {}
    for i, mdx_path in enumerate(mdx_paths):
        if not os.path.exists(mdx_path):
            print(f"警告：跳过不存在的路径: {mdx_path}", file=sys.stderr)
            continue
        dict_name = os.path.basename(mdx_path)
        print(f"[{i + 1}/{len(mdx_paths)}] {dict_name} ...", flush=True)
        try:
            db = MdictDatabase(mdx_path, encoding=args.encoding)
            entries = db.entries()
            for hw in entries:
                if _should_include_headword(hw):
                    headword_dicts.setdefault(hw, set()).add(dict_name)
            print(f"  共 {len(entries)} 条词头", flush=True)
        except Exception as e:
            print(f"  错误: {e}", file=sys.stderr)

    rows = [(hw, len(dicts)) for hw, dicts in sorted(headword_dicts.items())]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["词头", "出现的词典数量"])
        writer.writerows(rows)

    print(f"\n已写入 {len(rows)} 个词头 -> {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
从 xh7.json 提取反查表与注释表，输出紧凑 JSON 便于集成到应用中。

提取的表：
- variant_to_standard
- variant_to_preferred_single
- variant_to_preferred_multi
- raw_notes
- usage_notes
- single_char_traditional_to_standard
- single_char_yitihuabiao_to_standard
- single_char_yiti_other_to_standard

"""

import argparse
import gzip
import json
import sys
from pathlib import Path


# 需要提取的键（与 xh7.json 中的字段名一致）
TABLE_KEYS = [
    "variant_to_standard",
    "variant_to_preferred_single",
    "variant_to_preferred_multi",
    "raw_notes",
    "usage_notes",
    "single_char_traditional_to_standard",
    "single_char_yitihuabiao_to_standard",
    "single_char_yiti_other_to_standard",
    "non_erhua_to_erhua",
]


def load_source(path: Path) -> dict:
    """加载源 JSON。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"源文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_tables(data: dict) -> dict:
    """从完整数据中提取指定表，缺失的键用空结构代替。"""
    out = {}
    for key in TABLE_KEYS:
        if key in data:
            out[key] = data[key]
        else:
            # 根据类型给空结构
            if key in ("raw_notes", "usage_notes"):
                out[key] = {}
            else:
                out[key] = {}
    return out


def write_compact_json(obj: dict, path: Path) -> None:
    """写入紧凑 JSON（无多余空白，中文不转义）。"""
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 xh7.json 提取反查表与注释表，输出紧凑 JSON。"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="xh7.json",
        help="输入 JSON 路径（默认 xh7.json）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="dict7.json",
        help="输出 JSON 路径（默认 dict7.json）",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = base_dir / input_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = base_dir / output_path

    try:
        data = load_source(input_path)
    except Exception as e:
        print(f"加载失败: {e}", file=sys.stderr)
        return 1

    tables = extract_tables(data)

    # 统计
    for key in TABLE_KEYS:
        n = len(tables[key])
        print(f"  {key}: {n} 条", file=sys.stderr)

    write_compact_json(tables, output_path)
    print(f"已写: {output_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

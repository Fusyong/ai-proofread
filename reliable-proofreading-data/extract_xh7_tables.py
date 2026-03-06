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

应用集成示例（Python）：
    import gzip, json
    path = "xh7_tables.json.gz"  # 或 xh7_tables.json
    open_fn = gzip.open if path.endswith(".gz") else open
    with open_fn(path, "rt", encoding="utf-8") as f:
        tables = json.load(f)

VS Code 扩展集成（推荐单文件 .json，简单无依赖）：
    const path = require("path");
    const fs = require("fs");
    const dataPath = path.join(context.extensionPath, "data", "xh7_tables.json");
    const tables = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
    // tables.variant_to_standard["一槌定音"] === "一锤定音"

    若使用 .json.gz 以减小扩展体积（约 50KB），用 Node 内置 zlib：
    const zlib = require("zlib");
    const raw = fs.readFileSync(path.join(context.extensionPath, "data", "xh7_tables.json.gz"));
    const tables = JSON.parse(zlib.gunzipSync(raw).toString("utf-8"));
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
]


def load_source(path: Path) -> dict:
    """加载源 JSON（支持 .json 或 .json.gz）。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"源文件不存在: {path}")
    if path.suffix == ".gz" or path.name.endswith(".json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
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


def write_compact_json(obj: dict, path: Path, gz: bool = False) -> None:
    """写入紧凑 JSON（无多余空白，中文不转义）。"""
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    path = Path(path)
    if gz:
        path = path.with_suffix(path.suffix + ".gz")
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(payload)
    else:
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
        default="xh7_tables.json",
        help="输出 JSON 路径（默认 xh7_tables.json）",
    )
    parser.add_argument(
        "--gz",
        action="store_true",
        help="同时输出 gzip 压缩文件（.json.gz）",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="按表名分别输出多个文件（xh7_<表名>.json）",
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

    if args.split:
        # 按表分文件
        for key in TABLE_KEYS:
            stem = output_path.stem
            single_path = output_path.parent / f"{stem}_{key}.json"
            write_compact_json({key: tables[key]}, single_path)
            print(f"已写: {single_path}", file=sys.stderr)
            if args.gz:
                write_compact_json({key: tables[key]}, single_path, gz=True)
                print(f"已写: {single_path}.gz", file=sys.stderr)
    else:
        # 单文件包含全部表
        write_compact_json(tables, output_path)
        print(f"已写: {output_path}", file=sys.stderr)
        if args.gz:
            write_compact_json(tables, output_path, gz=True)
            print(f"已写: {output_path}.gz", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

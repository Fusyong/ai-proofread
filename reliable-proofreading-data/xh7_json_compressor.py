#!/usr/bin/env python3
"""
!!! 擦身体啊 
    记得手动清理variant_to_preferred_multi开头的两个条目

从 xh7.json 提取反查表与注释表，输出紧凑 JSON 便于集成到应用中。

输入一般为 xh7_extractor.py 生成的完整 xh7.json（位于 reliable-proofreading-data）。

----------------------------------------------------------------------
命令行用法
----------------------------------------------------------------------

在项目根目录或本目录下执行：

  python reliable-proofreading-data/xh7_json_compressor.py

常用示例：

  # 默认：读取 reliable-proofreading-data/xh7.json，写出 xh7_compressed.json
  python reliable-proofreading-data/xh7_json_compressor.py

  # 指定输入与输出
  python reliable-proofreading-data/xh7_json_compressor.py xh72026-05-17.json -o xh7_compressed.json

  # 使用绝对路径
  python reliable-proofreading-data/xh7_json_compressor.py ^
      "D:/ah21/ai-proofread/reliable-proofreading-data/xh7.json" ^
      -o "D:/ah21/ai-proofread/reliable-proofreading-data/xh7_compressed.json"

  # 查看参数说明
  python reliable-proofreading-data/xh7_json_compressor.py --help

参数一览：

  input [PATH]
      源 JSON 路径。相对路径相对于本脚本所在目录（reliable-proofreading-data）。
      默认 xh7.json。

  -o, --output PATH
      输出紧凑 JSON 路径，默认 xh7_compressed.json（同样相对于本目录）。

运行时在 stderr 打印各表条数。

后处理：各表键、值（及列表项）末尾的阿拉伯数字会去掉；合并后键相同时，
值相同则保留一条，不同则用「；」拼接（如 拔火罐1/拔火罐2 → 拔火罐）。

----------------------------------------------------------------------
输出包含的表
----------------------------------------------------------------------

  variant_to_standard / variant_to_preferred_single / variant_to_preferred_multi
  raw_notes / usage_notes
  single_char_traditional_to_standard / single_char_yitihuabiao_to_standard
  single_char_yiti_other_to_standard
  non_erhua_to_erhua
  light_tone_headword   由 word_to_pinyin 筛出必须轻声（；拼接任一条含 · 且无调号即保留）
                        旧版 xh7.json 可回退 light_tone_required
  word_to_multi_pinyin  由 word_to_pinyin 筛出多音词（拼音含；拼接标记）；键/值经后处理

输出为单行紧凑 JSON（无缩进，中文不转义）。
"""


import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from xh7_phonetic_utils import merged_pinyin_has_required_light_tone

# 词头/字头末尾义项序号（阿拉伯数字），如 拔火罐1 → 拔火罐
_TRAILING_ARABIC_DIGITS = re.compile(r"\d+$")


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
    "light_tone_headword",
    "word_to_multi_pinyin",
]

# 值为字符串列表的表
_LIST_VALUE_TABLES = frozenset({"raw_notes", "usage_notes"})


def strip_trailing_arabic_digits(text: str) -> str:
    """去掉末尾连续阿拉伯数字（现汉7 多义项词头序号）。"""
    if not text:
        return text
    return _TRAILING_ARABIC_DIGITS.sub("", str(text).strip())


def merge_scalar_values(existing: str, new: str) -> str:
    """合并同一键下的字符串值：相同则覆盖为一条，不同则用；拼接。"""
    if existing == new:
        return existing
    parts: list[str] = []
    for val in (existing, new):
        for part in str(val).split("；"):
            part = part.strip()
            if part and part not in parts:
                parts.append(part)
    return "；".join(parts)


def normalize_str_dict(table: dict) -> dict:
    """规范化 {str: str} 反查表：去末尾数字并合并重复键。"""
    out: dict = {}
    for key, val in table.items():
        nk = strip_trailing_arabic_digits(str(key))
        if not nk:
            continue
        nv = strip_trailing_arabic_digits(str(val)) if val is not None else ""
        if nk in out:
            out[nk] = merge_scalar_values(out[nk], nv)
        else:
            out[nk] = nv
    return out


def normalize_list_dict(table: dict) -> dict:
    """规范化 {str: list[str]} 表：键与列表项去末尾数字并合并。"""
    out: dict = {}
    for key, val in table.items():
        nk = strip_trailing_arabic_digits(str(key))
        if not nk:
            continue
        items: list[str] = []
        if isinstance(val, list):
            for item in val:
                ni = strip_trailing_arabic_digits(str(item))
                if ni and ni not in items:
                    items.append(ni)
        elif val is not None:
            ni = strip_trailing_arabic_digits(str(val))
            if ni:
                items = [ni]
        if nk in out:
            for item in items:
                if item not in out[nk]:
                    out[nk].append(item)
        else:
            out[nk] = items
    return out


def normalize_all_tables(tables: dict) -> dict:
    """对所有输出表做末尾数字剥离与键合并。"""
    for key in TABLE_KEYS:
        if key not in tables or not isinstance(tables[key], dict):
            continue
        if key in _LIST_VALUE_TABLES:
            tables[key] = normalize_list_dict(tables[key])
        else:
            tables[key] = normalize_str_dict(tables[key])
    return tables


def load_source(path: Path) -> dict:
    """加载源 JSON。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"源文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_light_tone_headword(data: dict) -> dict:
    """
    生成 {词头: 拼音} 表（输出键名仍为 light_tone_headword，与既有应用兼容）。
    优先从 word_to_pinyin 筛选必须轻声（见 xh7_phonetic_utils.is_required_light_tone_pinyin）；
    若无 word_to_pinyin 则回退 light_tone_required（旧版 xh7.json）。
    """
    wtp = data.get("word_to_pinyin")
    if isinstance(wtp, dict) and wtp:
        out: dict = {}
        for hw, py in wtp.items():
            if not hw or py is None:
                continue
            py_str = str(py).strip()
            if not py_str or not merged_pinyin_has_required_light_tone(py_str):
                continue
            out[str(hw)] = py_str
        return out

    out: dict = {}
    for rec in data.get("light_tone_required") or []:
        if not isinstance(rec, dict):
            continue
        hw = rec.get("headword")
        py = rec.get("pinyin")
        if not hw or not py:
            continue
        hw = strip_trailing_arabic_digits(str(hw))
        py = strip_trailing_arabic_digits(str(py))
        if not hw or not py:
            continue
        if hw in out:
            out[hw] = merge_scalar_values(out[hw], py)
        else:
            out[hw] = py
    return out


def build_word_to_multi_pinyin(data: dict) -> dict:
    """
    从 word_to_pinyin 筛出多音词：拼音含全角；拼接（与 xh7_extractor 多音合并约定一致）。
    """
    wtp = data.get("word_to_pinyin")
    if not isinstance(wtp, dict) or not wtp:
        return {}
    out: dict = {}
    for hw, py in wtp.items():
        if not hw or py is None:
            continue
        py_str = str(py).strip()
        if not py_str or "；" not in py_str:
            continue
        out[str(hw)] = py_str
    return out


def extract_tables(data: dict) -> dict:
    """从完整数据中提取指定表，缺失的键用空结构代替。"""
    out = {}
    for key in TABLE_KEYS:
        if key == "light_tone_headword":
            out[key] = build_light_tone_headword(data)
        elif key == "word_to_multi_pinyin":
            out[key] = build_word_to_multi_pinyin(data)
        elif key in data:
            out[key] = data[key]
        else:
            out[key] = {}
    return normalize_all_tables(out)


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
        default="xh7_compressed.json",
        help="输出 JSON 路径（默认 xh7_compressed.json）",
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

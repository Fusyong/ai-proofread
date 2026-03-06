#!/usr/bin/env python3
"""
解析《第一批异形词整理表》文本，输出 TGSCC 风格的 JSON 结构。

支持三种行格式：
  其一：规范词——异形词、异形词 拼音[数字注码]
        例：掺和——搀和 chānhuo[1]、搭讪——搭赸、答讪 dāshàn
  其二：规范词（异形词、异形词） 拼音  【附录，* 表示非规范字】
        例：抵触（*牴触） dǐchù、仿佛（彷*彿、*髣*髴） fǎngfú
  其三：[数字注码] 注释内容
        例：[1] "掺""搀"实行分工："掺"表混合义，"搀"表搀扶义。

输出结构（参考 TGSCC）：
  - standard_to_variants: 规范词 -> [异形词列表]
  - variant_to_standard: 异形词 -> 规范词
  - notes: 异形词 -> 注释正文（有注码的条目）
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


# 格式一：规范词——异形词、异形词 拼音[数字]
# 拼音：字母、声调、连字符、省字符等（排除 [ 以免吃掉注码）
# 例：chānhuo、bǎifèi-jùxīng、biānzhě'àn
_PINYIN = r"[^\s\[\]]+"

# 例：掺和——搀和 chānhuo[1]、凋敝——雕敝、雕弊 diāobì[4]
RE_TYPE1 = re.compile(
    rf"^([\u4e00-\u9fff\u3007\-'儿]+)——([\u4e00-\u9fff\u3007\-'儿、]+)\s+({_PINYIN})(?:\[(\d+)\])?$"
)

# 格式二：规范词（异形词、异形词） 拼音
# 例：抵触（*牴触） dǐchù、仿佛（彷*彿、*髣*髴） fǎngfú
RE_TYPE2 = re.compile(
    rf"^([\u4e00-\u9fff\u3007\-'儿]+)（([\u4e00-\u9fff\u3007*\-'儿、]+)）\s+({_PINYIN})$"
)

# 格式三：[数字] 注释内容
RE_TYPE3 = re.compile(r"^\[(\d+)\]\s*(.+)$")


def _strip_asterisk(s: str) -> str:
    """去掉 * 号，得到实际词形。"""
    return s.replace("*", "")


def _parse_variants_type1(variants_str: str) -> List[str]:
    """解析格式一的异形词列表（顿号分隔）。"""
    return [v.strip() for v in variants_str.split("、") if v.strip()]


def _parse_variants_type2(variants_str: str) -> List[str]:
    """解析格式二的异形词列表，去掉 * 得到实际词形。"""
    raw = [v.strip() for v in variants_str.split("、") if v.strip()]
    return [_strip_asterisk(v) for v in raw]


def parse_file(path: Path) -> Dict:
    """解析文件，返回 TGSCC 风格的数据结构。"""
    standard_to_variants: Dict[str, List[str]] = {}
    variant_to_standard: Dict[str, str] = {}
    notes_content: Dict[str, str] = {}  # 注码 -> 注释正文
    variant_to_note: Dict[str, str] = {}  # 异形词 -> 注码
    notes: Dict[str, str] = {}  # 异形词 -> 注释正文（最终合并）

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 跳过附录标题行
            if "【附录】" in line or "含有非规范字的异形词" in line:
                continue

            # 格式三：注释
            m3 = RE_TYPE3.match(line)
            if m3:
                num, content = m3.group(1), m3.group(2).strip()
                notes_content[num] = content
                continue

            # 格式一：规范词——异形词 拼音[注码]
            m1 = RE_TYPE1.match(line)
            if m1:
                standard, variants_str, pinyin, note_num = m1.groups()
                variants = _parse_variants_type1(variants_str)
                if not variants:
                    continue
                standard_to_variants.setdefault(standard, []).extend(variants)
                for v in variants:
                    variant_to_standard[v] = standard
                    if note_num:
                        variant_to_note[v] = note_num
                continue

            # 格式二：规范词（异形词） 拼音
            m2 = RE_TYPE2.match(line)
            if m2:
                standard, variants_str, pinyin = m2.groups()
                variants = _parse_variants_type2(variants_str)
                if not variants:
                    continue
                standard_to_variants.setdefault(standard, []).extend(variants)
                for v in variants:
                    variant_to_standard[v] = standard
                continue

    # 合并 notes：异形词 -> 注释正文
    for variant, num in variant_to_note.items():
        if num in notes_content:
            notes[variant] = notes_content[num]

    return {
        "standard_to_variants": standard_to_variants,
        "variant_to_standard": variant_to_standard,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="解析《第一批异形词整理表》，输出 TGSCC 风格 JSON。"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=r"D:\wares\textpro\语料和替换表\第一批异形词整理表.txt",
        help="输入文本路径",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="输出 JSON 路径（默认打印到 stdout）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"文件不存在: {input_path}", file=sys.stderr)
        return 1

    try:
        data = parse_file(input_path)
    except Exception as e:
        print(f"解析失败: {e}", file=sys.stderr)
        raise

    # 统计
    n_std = len(data["standard_to_variants"])
    n_var = len(data["variant_to_standard"])
    n_notes = len(data["notes"])
    print(f"  规范词条: {n_std} 组", file=sys.stderr)
    print(f"  异形词: {n_var} 个", file=sys.stderr)
    print(f"  带注释: {n_notes} 个", file=sys.stderr)

    payload = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"已写: {out_path}", file=sys.stderr)
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())

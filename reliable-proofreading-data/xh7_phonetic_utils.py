"""
现汉7 词头与拼音中的轻声、儿化位置解析。

凡例约定：
- 轻声音节前用间隔号 ·（U+00B7）；· 后紧跟的第一音节为轻声。
- 儿化在词头中用 <small>儿</small> 标出（与词形中的普通「儿」区分）。
- 拼音切分：先按 · 分；各段内再按隔音符号 '（ASCII 单引号）分；各小段内按辅音起首
  识别音节（zh/ch/sh 优先）。' 为显式音节界，优先于辅音启发式。
- 轻声「两可」：· 后第一音节仍标有调类（āáǎà 等），如 kàn·fǎ；必须轻声则无调号，如 kàn·buqǐ、kào·zi。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

LIGHT_TONE_DOT = "\u00b7"
_SMALL_ER = re.compile(r"<small>\s*儿\s*</small>")
_HWG_START = re.compile(r"<hwg\b", re.IGNORECASE)
_HWG = re.compile(
    r"<hwg[^>]*>\s*<hw>(.+?)</hw>\s*<pinyin>([^<]+)</pinyin>\s*</hwg>",
    re.DOTALL | re.IGNORECASE,
)
# 含调号的韵母（用于判断轻声是否两可）
_TONE_CHARS = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
_TONE_VOWEL = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]")
# 隔音符号（现汉7 用 ASCII 单引号，兼容弯引号等变体）
_APOSTROPHE_SPLIT = re.compile(r"['\u2019\u02bc\u2032`´]")
# 韵母：基本元音 + 已带调号元音（现汉7 多用预组合调号，如 ān、guā）
_VOWEL_CORE = rf"(?:[aeiouüv{_TONE_CHARS}]+|n[g]?|m|ng|ê)"
# 音节切分：辅音起首（非首音节）
_SYLLABLE_ONSET = re.compile(
    r"(?:(?<=.)|^)"
    rf"((?:zh|ch|sh|[bpmfdtnlgkhjrzxcsyw])?{_VOWEL_CORE})",
    re.IGNORECASE,
)


def strip_hw_tags(raw_hw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw_hw).strip()


def headword_key(hw: str) -> str:
    if not hw:
        return hw
    m = re.match(r"^([^（(]+)", hw)
    return m.group(1).strip() if m else hw


def headword_display_from_raw(raw_hw: str) -> str:
    """显示词头：去掉 <small>儿</small> 标记（附着儿化），再去其余标签。"""
    text = _SMALL_ER.sub("", raw_hw)
    return headword_key(strip_hw_tags(text))


def headword_with_er_from_raw(raw_hw: str) -> str:
    """仅去 small 标签、保留「儿」字的词头。"""
    text = re.sub(r"</?small\s*>", "", raw_hw)
    return headword_key(strip_hw_tags(text))


def _syllables_by_consonant(chunk: str) -> List[str]:
    """对无隔音符的一段按辅音起首切分，并合并误切的韵尾 n/ng/m（如 ān）。"""
    found = [m.group(1).lower() for m in _SYLLABLE_ONSET.finditer(chunk) if m.group(1)]
    if not found:
        return [chunk.lower()]
    merged: List[str] = []
    for syl in found:
        if merged and syl in ("n", "ng", "m") and (
            _TONE_VOWEL.search(merged[-1]) or merged[-1][-1] in "aeiouüv"
        ):
            merged[-1] += syl
        else:
            merged.append(syl)
    if "".join(merged) == chunk.lower():
        return merged
    return found


def _syllables_from_dot_part(part: str) -> List[str]:
    """
    · 分段内的音节切分：先按隔音符号 '，再对各段按辅音起首。
    """
    part = part.strip()
    if not part:
        return []
    syllables: List[str] = []
    for chunk in _APOSTROPHE_SPLIT.split(part):
        chunk = chunk.strip()
        if not chunk:
            continue
        syllables.extend(_syllables_by_consonant(chunk))
    return syllables


def _syllables_and_light_tone_indices(pinyin: str) -> Tuple[List[str], List[int]]:
    """先按 · 分，段内按 ' 与辅音起首切音节；返回 (音节列表, 轻声音节下标)。"""
    pinyin = pinyin.strip()
    if not pinyin:
        return [], []
    parts = pinyin.split(LIGHT_TONE_DOT)
    syllables: List[str] = []
    lt_indices: List[int] = []
    for i, part in enumerate(parts):
        found = _syllables_from_dot_part(part)
        if i > 0 and found:
            lt_indices.append(len(syllables))
        syllables.extend(found)
    return syllables, lt_indices


def split_pinyin_syllables(pinyin: str) -> List[str]:
    """将拼音串切分为音节列表（不含 · 与 '）。"""
    return _syllables_and_light_tone_indices(pinyin)[0]


def light_tone_syllable_indices(pinyin: str) -> List[int]:
    """返回轻声音节在 split 后全音节列表中的下标（· 后各段的第一音节）。"""
    return _syllables_and_light_tone_indices(pinyin)[1]


def syllable_has_tone_mark(syllable: str) -> bool:
    return bool(_TONE_VOWEL.search(syllable))


def is_optional_light_tone(syllable: str) -> bool:
    """· 后音节仍带调号 → 轻声与读本调两可。"""
    return syllable_has_tone_mark(syllable)


def align_syllables_to_chars(headword: str, syllables: List[str]) -> List[int]:
    """
    将音节下标映射到词头汉字下标（仅统计 CJK 字符，与音节一一对应）。
    字数与音节数不一致时，按顺序对齐，多余字/音节忽略尾部。
    """
    chars = [c for c in headword if "\u4e00" <= c <= "\u9fff"]
    if not chars or not syllables:
        return [-1] * len(syllables)
    mapping: List[int] = []
    for i in range(len(syllables)):
        mapping.append(i if i < len(chars) else len(chars) - 1)
    return mapping


def _prev_han_char(raw_hw: str, pos: int) -> str:
    text = strip_hw_tags(raw_hw[:pos])
    for c in reversed(text):
        if "\u4e00" <= c <= "\u9fff":
            return c
    return ""


def extract_erhua_positions(
    raw_hw: str, headword: str, pinyin: str = ""
) -> List[Dict[str, Any]]:
    """
    从 raw <hw> 解析儿化位置（char_index 相对 headword 中的汉字，0 起）。
    - attached：儿化附在前一音节（街面<small>儿</small>上 → 街面上，位在「面」）
    - syllabic：独立儿音节（个<small>儿</small>顶 → 个儿顶）
    结合拼音：前一音节以 r 结尾（如 miànr）且显示形无独立「儿」→ attached。
    """
    chars = [c for c in headword if "\u4e00" <= c <= "\u9fff"]
    syllables = split_pinyin_syllables(pinyin) if pinyin else []
    syl_to_ci = align_syllables_to_chars(headword, syllables) if syllables else []

    positions: List[Dict[str, Any]] = []
    disp_i = 0
    pos = 0
    marker_idx = 0
    while pos < len(raw_hw):
        m = _SMALL_ER.match(raw_hw, pos)
        if m:
            prev_han = _prev_han_char(raw_hw, m.start())
            kind = "syllabic"
            char_index = disp_i
            char_val = "儿"

            if prev_han and syllables and syl_to_ci:
                try:
                    pi = chars.index(prev_han, max(0, char_index - 1))
                except ValueError:
                    pi = char_index - 1 if char_index > 0 else 0
                if 0 <= pi < len(syl_to_ci):
                    si = syl_to_ci[pi]
                    if si < len(syllables):
                        syl = syllables[si]
                        if syl.endswith("r") and len(syl) > 1:
                            if disp_i >= len(headword) or (
                                disp_i < len(headword) and headword[disp_i] != "儿"
                            ):
                                kind = "attached"
                                char_index = pi
                                char_val = prev_han

            if kind == "syllabic":
                if disp_i < len(headword) and headword[disp_i] == "儿":
                    char_index = disp_i
                    char_val = "儿"
                    disp_i += 1
                elif disp_i > 0:
                    kind = "attached"
                    char_index = disp_i - 1
                    char_val = headword[char_index]
            else:
                char_index = min(char_index, len(chars) - 1) if chars else 0
                char_val = chars[char_index] if chars else prev_han

            positions.append(
                {"char_index": char_index, "char": char_val, "kind": kind}
            )
            marker_idx += 1
            pos = m.end()
            continue
        tag = re.match(r"<[^>]+>", raw_hw[pos:])
        if tag:
            pos += tag.end()
            continue
        if disp_i < len(headword) and raw_hw[pos] == headword[disp_i]:
            disp_i += 1
        pos += 1
    return positions


def split_entry_blocks(content: str) -> List[str]:
    """按 <entry>...</entry> 切分；无 entry 时整段作为一块（兼容裸 hwg）。"""
    blocks: List[str] = []
    pos = 0
    while True:
        start = content.find("<entry", pos)
        if start == -1:
            break
        end = content.find("</entry>", start)
        if end == -1:
            break
        blocks.append(content[start : end + len("</entry>")])
        pos = end + len("</entry>")
    if not blocks and content and content.strip():
        return [content]
    return blocks


def split_hwg_blocks(block: str) -> List[str]:
    """
    将一块 HTML 按 <hwg> 起点切分为子块。
    仅一个 hwg 时返回整块，以便也作/同等规则可匹配该 hwg 后的全文。
    多个 hwg 时各子块含一个 hwg 及其后内容（至下一 hwg 前）。
    """
    starts = [m.start() for m in _HWG_START.finditer(block)]
    if len(starts) <= 1:
        return [block]
    return [block[starts[i] : starts[i + 1]] for i in range(len(starts) - 1)] + [
        block[starts[-1] :]
    ]


def iter_extraction_segments(content: str):
    """按 entry、再按 hwg 产出各提取子块（异形/用法提示等共用）。"""
    if not content:
        return
    for entry_block in split_entry_blocks(content):
        for segment in split_hwg_blocks(entry_block):
            yield segment


def iter_hwg_in_content(content: str) -> List[Tuple[str, str, str]]:
    """返回 [(raw_hw, headword, pinyin), ...]；同次查询中全部 <hwg> 均收录。"""
    if not content:
        return []
    out: List[Tuple[str, str, str]] = []
    for block in split_entry_blocks(content):
        for m in _HWG.finditer(block):
            raw_hw = m.group(1)
            pinyin = m.group(2).strip()
            hw = headword_display_from_raw(raw_hw)
            if hw and pinyin:
                out.append((raw_hw, hw, pinyin))
    return out


def build_light_tone_info(
    headword: str, pinyin: str
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    解析轻声位置列表；返回 (light_syllables, has_any_optional)。
    每项：syllable_index, syllable, char_index, char, optional。
    """
    syllables = split_pinyin_syllables(pinyin)
    lt_indices = light_tone_syllable_indices(pinyin)
    char_map = align_syllables_to_chars(headword, syllables)
    chars = [c for c in headword if "\u4e00" <= c <= "\u9fff"]
    items: List[Dict[str, Any]] = []
    has_optional = False
    for si in lt_indices:
        if si >= len(syllables):
            continue
        syl = syllables[si]
        optional = is_optional_light_tone(syl)
        if optional:
            has_optional = True
        ci = char_map[si] if si < len(char_map) else -1
        ch = chars[ci] if 0 <= ci < len(chars) else ""
        items.append(
            {
                "syllable_index": si,
                "syllable": syl,
                "char_index": ci,
                "char": ch,
                "optional": optional,
            }
        )
    return items, has_optional


def is_required_light_tone_pinyin(pinyin: str) -> bool:
    """
    是否为现汉7「必须轻声」读音（相对「轻声与本调两可」）。
    拼音含间隔号 ·，且 · 后轻声音节均无调号（如 kàn·buqǐ）；kàn·fǎ 为两可，返回 False。
    """
    py = pinyin.strip()
    if LIGHT_TONE_DOT not in py:
        return False
    light_syllables, has_optional = build_light_tone_info("", py)
    return bool(light_syllables) and not has_optional


def merged_pinyin_has_required_light_tone(pinyin: str) -> bool:
    """多条读音用；拼接时，任一条为必须轻声即返回 True。"""
    for part in str(pinyin).split("；"):
        part = part.strip()
        if part and is_required_light_tone_pinyin(part):
            return True
    return False


def build_erhua_record(raw_hw: str, headword: str, pinyin: str) -> Dict[str, Any]:
    """构建儿化词条记录（含位置）。"""
    non_erhua = headword_key(strip_hw_tags(_SMALL_ER.sub("", raw_hw)))
    with_er = headword_with_er_from_raw(raw_hw)
    positions = extract_erhua_positions(raw_hw, headword, pinyin)
    has_syllabic = any(p.get("kind") == "syllabic" for p in positions)
    primary = with_er if has_syllabic and with_er != headword else headword
    if primary != headword:
        positions = extract_erhua_positions(raw_hw, primary, pinyin)
    rec: Dict[str, Any] = {
        "headword": primary,
        "pinyin": pinyin,
        "non_erhua": non_erhua,
        "erhua_positions": positions,
    }
    if headword != primary:
        rec["headword_surface"] = headword
    if with_er and with_er != primary:
        rec["headword_with_er"] = with_er
    if with_er and with_er != non_erhua:
        rec["erhua_form"] = with_er
    return rec

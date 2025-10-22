import re
from typing import Optional


_CN_DIGITS = {
    "零": 0, "〇": 0, "○": 0, "O": 0,
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5, "陆": 6, "柒": 7, "捌": 8, "玖": 9,
}
_CN_UNITS = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000, "万": 10000, "亿": 100000000}


def chinese_numeral_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    # 纯阿拉伯数字直接返回
    if text.isdigit():
        try:
            return int(text)
        except ValueError:
            return None

    total = 0
    section = 0
    number = 0
    _last_unit = 1  # 保留变量名以便后续扩展（避免大改），当前未使用

    for ch in text:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if unit >= 10000:
                section = (section + (number if number else 1)) * unit
                total += section
                section = 0
            else:
                # 十/百/千
                if number == 0:
                    number = 1
                section += number * unit
            number = 0
            _last_unit = unit
        else:
            # 非法字符，放弃解析
            return None

    return total + section + number


_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    text = text.upper()
    if not re.fullmatch(r"[IVXLCDM]+", text or ""):
        return None
    total = 0
    prev = 0
    for ch in reversed(text):
        val = _ROMAN_VALUES.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total if total > 0 else None


def normalize_number(groups: dict, order: list) -> Optional[int]:
    for tag in order:
        if tag == "arabic":
            val = groups.get("num_ar") or groups.get("arabic")
            if val and val.isdigit():
                return int(val)
        elif tag == "cn":
            val = groups.get("num_cn") or groups.get("cn")
            n = chinese_numeral_to_int(val or "")
            if n is not None:
                return n
        elif tag == "roman":
            val = groups.get("num_rm") or groups.get("roman")
            n = roman_to_int(val or "")
            if n is not None:
                return n
    return None



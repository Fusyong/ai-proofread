"""
从 mdict 词典中提取校对可用的数据，存放到 reliable-proofreading-data 下。

当前实现：从现代汉语词典（现汉7）中提取多字词条异形与单字繁体/异体。

多字词条两类关系（互不混淆）：
1) 规范词形-不规范词形：如 枝丫（枝桠）→ 枝丫=规范词形，枝桠=不规范词形。
   → standard_to_variants（规范→不规范列表）、variant_to_standard（不规范→规范）。
2) 推荐词形-不推荐词形：也作（推荐→不推荐，如 㺀𤝽 也作忽律）与 同"X"（不推荐→推荐，如 忽律 同"㺀𤝽"）合并为一类、一个表。
   → preferred_to_variants（推荐→不推荐列表）、variant_to_preferred（不推荐→推荐）；
   输出时拆分为单字表与多字表：preferred_to_variants_single/multi、variant_to_preferred_single/multi。
3) 字（单音节）词条：繁体字、异体字加括号附列；⁎ 为《通用规范汉字表》附列异体字，⁑ 为该表以外异体字。
   → single_char_traditional、single_char_yitihuabiao、single_char_yiti_other；有符号标记时并入 raw_notes。
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional

# 多字来源标记（用于 stats）：规范词形-不规范词形（括号）；推荐词形-不推荐词形（也作 / 同）
SOURCE_GUIFAN_BUKUIFAN = "规范词形_不规范词形"
SOURCE_TUIJIAN_YEZUO = "推荐词形_也作"
SOURCE_BUTUIJIAN_TONG = "不推荐词形_同"
# 字（单音节）词条：繁体字、通用规范汉字表附列异体字（⁎）、其他异体字（⁑）
SINGLE_CHAR_FANTI = "繁体字"
SINGLE_CHAR_GUIFAN = "规范异体字"
SINGLE_CHAR_OTHER = "其他异体字"

try:
    from src.special_checker.mdict import MdictManager
except ImportError:
    try:
        from special_checker.mdict import MdictManager
    except ImportError:
        try:
            from mdict import MdictManager
        except ImportError:
            MdictManager = None  # type: ignore


# 校对数据存放目录（相对于项目根）
RELIABLE_PROOFREADING_DATA_DIR = "reliable-proofreading-data"


def get_output_dir() -> str:
    """获取 reliable-proofreading-data 的绝对路径，不存在则创建。"""
    # 以项目根为基准：向上找到包含 pyproject.toml 或 src 的目录
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = base
    if os.path.basename(base) == "src":
        root = os.path.dirname(base)
    out_dir = os.path.join(root, RELIABLE_PROOFREADING_DATA_DIR)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _strip_hw_tags(raw_hw: str) -> str:
    """去掉词头中的 HTML 标签（如 <sup>1</sup>），得到纯词形。"""
    return re.sub(r"<[^>]+>[^<]*</[^>]+>", "", raw_hw).strip()


def _headword_key(hw: str) -> str:
    """词头若含括号附列（如 吗（嗎）），只保留括号前部分作为键，避免 variant_to_preferred 等出现「吗（嗎）」异常键。"""
    if not hw:
        return hw
    m = re.match(r"^([^（(]+)", hw)
    return m.group(1).strip() if m else hw


def _strip_trailing_circle_digits(s: str) -> str:
    """去掉末尾未加标签的带圈数字（如 嘛③ -> 嘛）。U+2460-2473 ①-⑳，U+2776-277F ❶-❿。"""
    return re.sub(r"[\u2460-\u2473\u2776-\u277F]+$", "", s).strip()


def _strip_usage_note_links(text: str) -> str:
    """清理用法提示中的链接标签，如 参看\"<a href=\"entry://你\">你</a>\" → 参看\"你\"，保留链接内文字。"""
    return re.sub(r'<a\s[^>]*>(.*?)</a>', r'\1', text, flags=re.DOTALL)


def _split_and_clean_variants(raw: str) -> List[str]:
    """按顿号「、」分拆附列词形，去掉每项中的上标等标签，返回非空词形列表。"""
    parts = re.split(r"[、]", raw)
    return [_strip_hw_tags(p).strip() for p in parts if _strip_hw_tags(p).strip()]


def _has_annotation_beyond_link(text: str) -> bool:
    """是否有「注释」：含 HTML 且不仅为跳转链接 <a href="entry://...">。跳转链接不算注释，不写入 raw。"""
    if "<" not in text:
        return False
    rest = re.sub(r"<a\s[^>]*>.*?</a>", "", text, flags=re.DOTALL)
    return "<" in rest


def _classify_single_char_item(segment: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析单字括号内一项，判定为繁体字、规范异体字（*或⁎）、其他异体字（⁑或**）。
    现汉7 实际用 ⁎（U+204E）表示规范异体，如 <sup>⁎</sup>、<sup>△⁎</sup>、<sup>①⁎</sup>。
    返回 (类别, 去标签后的单字)，无法判定或非单字时返回 (None, None)。
    """
    char = _strip_hw_tags(segment).strip()
    if not char or len(char) != 1:
        return (None, None)
    # 其他异体：⁑ 或 两个*（《通用规范汉字表》以外的异体字）
    if "⁑" in segment:
        return (SINGLE_CHAR_OTHER, char)
    # 规范异体：<sup> 内带 * 或 ⁎（现汉7 用 ⁎），如 <sup>⁎</sup>擧、<sup>△⁎</sup>匄、<sup>①⁎</sup>枒
    if "<sup>" in segment and ("*" in segment or "⁎" in segment):
        return (SINGLE_CHAR_GUIFAN, char)
    # 无 * 无 ⁎ 无 ⁑ → 繁体字
    return (SINGLE_CHAR_FANTI, char)


class VariantFormsExtractor:
    """从词典中提取多字异形与单字繁体/异体等校对可用数据的提取器。"""

    def __init__(self, mdict_manager: Optional[object] = None):
        if mdict_manager is None and MdictManager is not None:
            self.mdict_manager = MdictManager()
        else:
            self.mdict_manager = mdict_manager
        self._compile_regex_patterns()

        self.extraction_rules = {
            "现汉7.mdx": self._extract_variant_forms_xianhan7,
        }

    def _compile_regex_patterns(self) -> None:
        # 现汉7：词头在 <hw>...</hw>，括号内为附列词形（规范-不规范 或 单字繁体/异体）
        # 形式1：<hw>枝丫</hw>（枝桠）或 <hw>枝丫</hw>(枝桠)，中间可有其它标签
        self._xianhan7_after_hw = re.compile(
            r"<hw>([^<]*(?:<[^>]+>[^<]*)*)</hw>\s*[（(]([^）)]+)[）)]"
        )
        # 形式2：<hw>枝丫（枝桠）</hw> 或 <hw>枝丫(枝桠)</hw>
        self._xianhan7_inside_hw = re.compile(
            r"<hw>([^<（(]+)[（(]([^）)]+)[）)]</hw>"
        )
        # 推荐词形-不推荐词形：也作"某某"。→ 词头=推荐词形，也作后=不推荐词形；最后必须是句号（。）
        self._xianhan7_yezuo = re.compile(r"也作([^。]+)(。)")
        # 不推荐词形-推荐词形：注释末「同"X"。」→ 词头=不推荐词形，引号内=推荐词形。
        # 现汉7 实际格式为弯引号 ""（U+201C/U+201D），如：同"<a href="entry://㺀𤝽">㺀𤝽</a>"。
        self._xianhan7_tong = re.compile(
            r'同[""\u201c\u201d「](?:<a\s[^>]*>)?([^<"」\u201c\u201d]+)(?:</a>)?["」\u201c\u201d]。'
        )
        # 本条词头：第一条 <hw>...</hw>
        self._xianhan7_headword = re.compile(
            r"<hw>([^<]*(?:<[^>]+>[^<]*)*)</hw>"
        )
        # 用法提示：<column><note>注意</note>...</column>
        self._xianhan7_column_note = re.compile(
            r"<column><note>注意</note>(.*?)</column>",
            re.DOTALL,
        )
        # 也作前若为引号则为单字异体说明（如「"阀"也作"伐"」），非词条异形
        self._quote_chars = ('"', '"', '"', '"', '「', '」', '『', '』')

    def _get_headword_from_content(self, content: str) -> str:
        """从一条释义内容中解析出词头（去标签）。"""
        m = self._xianhan7_headword.search(content)
        return _strip_hw_tags(m.group(1)) if m else ""

    def _split_into_entry_blocks(self, content: str) -> List[str]:
        """将查询结果按 <entry>...</entry> 分块。多音节（如乌拉两词条）、单音节（如 㖊、吗 多音多义多条）均先切分再逐条处理。"""
        blocks: List[str] = []
        pos = 0
        while True:
            start = content.find("<entry", pos)
            if start == -1:
                break
            end = content.find("</entry>", start)
            if end == -1:
                break
            end += len("</entry>")
            blocks.append(content[start:end])
            pos = end
        return blocks

    def _extract_usage_notes_from_block(self, block: str) -> List[str]:
        """从单个 <entry> 块中提取 <column><note>注意</note>...</column> 的用法提示列表；清理其中的链接标签。"""
        notes: List[str] = []
        for m in self._xianhan7_column_note.finditer(block):
            text = m.group(1).strip()
            if text:
                text = _strip_usage_note_links(text)
                if text:
                    notes.append(text)
        return notes

    def _extract_usage_notes_from_content(self, content: str) -> Dict[str, List[str]]:
        """从整段释义中按 entry 切分后提取用法提示，返回 词头键 -> 用法提示列表。"""
        out: Dict[str, List[str]] = {}
        blocks = self._split_into_entry_blocks(content)
        if not blocks:
            return out
        for block in blocks:
            headword = self._get_headword_from_content(block)
            headword_key = _headword_key(headword)
            if not headword_key:
                continue
            notes = self._extract_usage_notes_from_block(block)
            if notes:
                out.setdefault(headword_key, []).extend(notes)
        return out

    def _extract_from_one_entry(self, block: str, seen: set) -> List[Tuple[str, str, str, Optional[str]]]:
        """从单个 <entry>...</entry> 块中提取（规范/推荐词形, 不规范/不推荐词形, 来源, 原始匹配文本），用 seen 去重。有注释时保留原始匹配文本备查。"""
        result: List[Tuple[str, str, str, Optional[str]]] = []
        headword = self._get_headword_from_content(block)

        # 情形1/2：枝丫（枝桠）= 规范词形-不规范词形；单字 辉（輝、⁎煇）= 繁体/异体（见下）
        for m in self._xianhan7_after_hw.finditer(block):
            推荐词形 = _strip_hw_tags(m.group(1))
            if not 推荐词形:
                continue
            raw_bracket = m.group(2)
            raw_note = ("（" + raw_bracket + "）") if _has_annotation_beyond_link(raw_bracket) else None
            if len(推荐词形) == 1:
                # 单字词条：括号内为繁体字、规范异体（⁎）、其他异体（⁑），分类提取
                for seg in re.split(r"[、]", raw_bracket):
                    seg = seg.strip()
                    if not seg:
                        continue
                    类别, 附列字 = _classify_single_char_item(seg)
                    if not 类别 or not 附列字 or 附列字 == 推荐词形:
                        continue
                    key = (推荐词形, 附列字, 类别)
                    if key not in seen:
                        seen.add(key)
                        result.append((推荐词形, 附列字, 类别, raw_note))
            else:
                for 不推荐词形 in _split_and_clean_variants(raw_bracket):
                    if not 不推荐词形 or 不推荐词形 == 推荐词形:
                        continue
                    key = (推荐词形, 不推荐词形)
                    if key not in seen:
                        seen.add(key)
                        result.append((推荐词形, 不推荐词形, SOURCE_GUIFAN_BUKUIFAN, raw_note))  # 规范词形, 不规范词形

        for m in self._xianhan7_inside_hw.finditer(block):
            推荐词形 = _strip_hw_tags(m.group(1))
            if not 推荐词形:
                continue
            raw_bracket = m.group(2)
            raw_note = ("（" + raw_bracket + "）") if _has_annotation_beyond_link(raw_bracket) else None
            if len(推荐词形) == 1:
                for seg in re.split(r"[、]", raw_bracket):
                    seg = seg.strip()
                    if not seg:
                        continue
                    类别, 附列字 = _classify_single_char_item(seg)
                    if not 类别 or not 附列字 or 附列字 == 推荐词形:
                        continue
                    key = (推荐词形, 附列字, 类别)
                    if key not in seen:
                        seen.add(key)
                        result.append((推荐词形, 附列字, 类别, raw_note))
            else:
                for 不推荐词形 in _split_and_clean_variants(raw_bracket):
                    if not 不推荐词形 or 不推荐词形 == 推荐词形:
                        continue
                    key = (推荐词形, 不推荐词形)
                    if key not in seen:
                        seen.add(key)
                        result.append((推荐词形, 不推荐词形, SOURCE_GUIFAN_BUKUIFAN, raw_note))  # 规范词形, 不规范词形

        # 情形3：也作"某某"。或 也作某某。— 最后必须是句号（。）；同一条目可有多个「也作某某。」，finditer 逐条匹配
        headword_key = _headword_key(headword) if headword else ""
        if headword_key and len(headword_key) > 1:
            for m in self._xianhan7_yezuo.finditer(block):
                if m.lastindex and m.group(2) != "。":
                    continue
                if m.start() > 0 and block[m.start() - 1] in self._quote_chars:
                    continue
                推荐词形 = headword_key
                raw_note = m.group(0) if _has_annotation_beyond_link(m.group(1)) else None
                for 不推荐词形 in _split_and_clean_variants(m.group(1)):
                    if not 不推荐词形 or 不推荐词形 == 推荐词形:
                        continue
                    if "，" in 不推荐词形 or "指" in 不推荐词形:
                        continue
                    key = (推荐词形, 不推荐词形)
                    if key not in seen:
                        seen.add(key)
                        result.append((推荐词形, 不推荐词形, SOURCE_TUIJIAN_YEZUO, raw_note))  # 推荐词形, 不推荐词形（也作）

        # 情形4：同"X"。— 本词条词头=不推荐词形（用 headword_key 避免「吗（嗎）」），引号内=推荐词形（剥末尾带圈数字如 嘛③->嘛）；单字也可有同条（如 吗 同"嘛③"）
        if headword_key:
            for m in self._xianhan7_tong.finditer(block):
                推荐词形 = _strip_trailing_circle_digits(_strip_hw_tags(m.group(1)).strip())
                不推荐词形 = headword_key
                if not 推荐词形 or 推荐词形 == 不推荐词形:
                    continue
                key = (推荐词形, 不推荐词形)
                if key not in seen:
                    seen.add(key)
                    raw_note = m.group(0) if _has_annotation_beyond_link(m.group(0)) else None
                    result.append((推荐词形, 不推荐词形, SOURCE_BUTUIJIAN_TONG, raw_note))  # 推荐词形, 不推荐词形（同）；单字推荐词形如 嘛 也保留

        return result

    def _extract_variant_forms_xianhan7(
        self, content: str
    ) -> List[Tuple[str, str, str, Optional[str]]]:
        """
        从现汉7一条释义内容中提取（规范/推荐词形, 不规范/不推荐词形, 来源, 原始匹配文本）列表。
        单音节与多音节一样：预先按 <entry>...</entry> 切分为多条后再逐条处理（如 㖊、吗 多音多义各有多条 entry）。
        """
        if not content:
            return []
        result: List[Tuple[str, str, str, Optional[str]]] = []
        seen: set = set()
        # 单音节（㖊、吗 等）与多音节（乌拉 等）均先按 <entry> 切分为多条，再逐条提取
        blocks = self._split_into_entry_blocks(content)
        if not blocks:
            # 无 <entry> 时按整段处理（兼容）
            blocks = [content]
        for block in blocks:
            result.extend(self._extract_from_one_entry(block, seen))
        return result

    def extract_from_content(
        self, content: str, dict_name: str = "现汉7.mdx"
    ) -> List[Tuple[str, str, str, Optional[str]]]:
        """根据词典名从一条释义内容中提取（规范/推荐词形, 不规范/不推荐词形, 来源, 原始匹配文本）列表。"""
        if not content:
            return []
        rule = self.extraction_rules.get(dict_name)
        if rule:
            return rule(content)
        return []

    def get_entry_variants(
        self, entry: str, dict_name: str = "现汉7.mdx"
    ) -> List[Tuple[str, str]]:
        """查询词典中某词条的释义，并提取该条下的附列词形。（规范/推荐词形, 不规范/不推荐词形）列表。"""
        if not self.mdict_manager:
            return []
        content = self.mdict_manager.query(dict_name, entry)
        return [(p, v) for p, v, *_ in self.extract_from_content(content, dict_name)]

    def extract_all_from_dict(
        self,
        dict_name: str = "现汉7.mdx",
        limit: Optional[int] = None,
        progress_interval: int = 500,
    ) -> Tuple[
        Dict[str, List[str]], Dict[str, str], Dict[str, List[str]], Dict[str, str], Dict[str, int],
        Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]],
        Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]],
        Dict[str, str], Dict[str, str], Dict[str, str],
        Dict[str, List[str]],  # usage_notes
    ]:
        """
        从指定词典中按顺序逐一查询词条，解析多字异形与单字繁体/异体。
        多字两类关系：① 规范词形-不规范词形（枝丫（枝桠））→ standard_to_variants、variant_to_standard；
        ② 推荐词形-不推荐词形（也作 + 同"X" 合并为一表）→ preferred_to_variants、variant_to_preferred。
        有注释时保存原始匹配文本备查：*_raw。单字三表及反查见返回值。
        """
        if not self.mdict_manager:
            empty: Dict[str, List[str]] = {}
            empty_str: Dict[str, str] = {}
            return (
                {}, {}, {}, {}, {},
                {SOURCE_GUIFAN_BUKUIFAN: 0, SOURCE_TUIJIAN_YEZUO: 0, SOURCE_BUTUIJIAN_TONG: 0,
                 SINGLE_CHAR_FANTI: 0, SINGLE_CHAR_GUIFAN: 0, SINGLE_CHAR_OTHER: 0},
                empty, empty, empty,
                empty, empty, empty, empty,
                empty_str, empty_str, empty_str,
                empty,
            )
        entries = self.mdict_manager.entries(dict_name, limit)
        total = len(entries)
        # 规范词形-不规范词形（情形1/2 括号）
        standard_to_variants: Dict[str, List[str]] = {}
        variant_to_standard: Dict[str, str] = {}
        # 推荐词形-不推荐词形（情形3 也作 + 情形4 同，一个表）
        preferred_to_variants: Dict[str, List[str]] = {}
        variant_to_preferred: Dict[str, str] = {}
        # stats 统计的是「匹配到的」条数（每匹配到一条就 +1），不是合并/去重后的表内条数
        stats: Dict[str, int] = {
            SOURCE_GUIFAN_BUKUIFAN: 0,
            SOURCE_TUIJIAN_YEZUO: 0,
            SOURCE_BUTUIJIAN_TONG: 0,
            SINGLE_CHAR_FANTI: 0,
            SINGLE_CHAR_GUIFAN: 0,
            SINGLE_CHAR_OTHER: 0,
        }

        # 有注释时保存的原始匹配文本（备查）
        standard_to_variants_raw: Dict[str, List[str]] = {}
        preferred_to_variants_raw: Dict[str, List[str]] = {}
        variant_to_preferred_raw: Dict[str, List[str]] = {}

        # 单字词条：繁体字、规范异体字、其他异体字（有符号标记时保存原始匹配备查）
        single_char_traditional: Dict[str, List[str]] = {}
        single_char_yitihuabiao: Dict[str, List[str]] = {}
        single_char_yiti_other: Dict[str, List[str]] = {}
        single_char_raw: Dict[str, List[str]] = {}

        # 用法提示：<column><note>注意</note>...</column>，按 entry 切分后提取，键=词头
        usage_notes: Dict[str, List[str]] = {}

        for i, entry in enumerate(entries):
            if progress_interval and i > 0 and i % progress_interval == 0:
                print(f"已处理 {i}/{total} 条…")
            content = self.mdict_manager.query(dict_name, entry)
            # 用法提示：先按 entry 切分再逐块提取
            notes_batch = self._extract_usage_notes_from_content(content)
            for k, v in notes_batch.items():
                usage_notes.setdefault(k, []).extend(v)
            triples = self.extract_from_content(content, dict_name)
            for preferred, variant, source, raw in triples:
                preferred = preferred or entry
                stats[source] = stats.get(source, 0) + 1
                # 单字词条：繁体/规范异体/其他异体
                if source == SINGLE_CHAR_FANTI:
                    if preferred not in single_char_traditional:
                        single_char_traditional[preferred] = []
                    if variant not in single_char_traditional[preferred]:
                        single_char_traditional[preferred].append(variant)
                    if raw:
                        if preferred not in single_char_raw:
                            single_char_raw[preferred] = []
                        if raw not in single_char_raw[preferred]:
                            single_char_raw[preferred].append(raw)
                    continue
                if source == SINGLE_CHAR_GUIFAN:
                    if preferred not in single_char_yitihuabiao:
                        single_char_yitihuabiao[preferred] = []
                    if variant not in single_char_yitihuabiao[preferred]:
                        single_char_yitihuabiao[preferred].append(variant)
                    if raw:
                        if preferred not in single_char_raw:
                            single_char_raw[preferred] = []
                        if raw not in single_char_raw[preferred]:
                            single_char_raw[preferred].append(raw)
                    continue
                if source == SINGLE_CHAR_OTHER:
                    if preferred not in single_char_yiti_other:
                        single_char_yiti_other[preferred] = []
                    if variant not in single_char_yiti_other[preferred]:
                        single_char_yiti_other[preferred].append(variant)
                    if raw:
                        if preferred not in single_char_raw:
                            single_char_raw[preferred] = []
                        if raw not in single_char_raw[preferred]:
                            single_char_raw[preferred].append(raw)
                    continue
                if source == SOURCE_GUIFAN_BUKUIFAN:
                    # 情形1/2：规范词形-不规范词形
                    if preferred not in standard_to_variants:
                        standard_to_variants[preferred] = []
                    if variant not in standard_to_variants[preferred]:
                        standard_to_variants[preferred].append(variant)
                    if variant in variant_to_standard:
                        if variant_to_standard[variant] != preferred:
                            merged = variant_to_standard[variant] + "；" + preferred
                            variant_to_standard[variant] = merged
                            print(f"[反查] variant_to_standard 冲突已合并：'{variant}' -> '{merged}'")
                    else:
                        variant_to_standard[variant] = preferred
                    if raw:
                        if preferred not in standard_to_variants_raw:
                            standard_to_variants_raw[preferred] = []
                        if raw not in standard_to_variants_raw[preferred]:
                            standard_to_variants_raw[preferred].append(raw)
                    continue
                if source == SOURCE_TUIJIAN_YEZUO:
                    # 情形3：也作 → 推荐词形-不推荐词形（推荐→不推荐）
                    if preferred not in preferred_to_variants:
                        preferred_to_variants[preferred] = []
                    if variant not in preferred_to_variants[preferred]:
                        preferred_to_variants[preferred].append(variant)
                    if variant in variant_to_preferred:
                        if variant_to_preferred[variant] != preferred:
                            merged = variant_to_preferred[variant] + "；" + preferred
                            variant_to_preferred[variant] = merged
                            print(f"[反查] variant_to_preferred 冲突已合并：'{variant}' -> '{merged}'")
                    else:
                        variant_to_preferred[variant] = preferred
                    if raw:
                        if preferred not in preferred_to_variants_raw:
                            preferred_to_variants_raw[preferred] = []
                        if raw not in preferred_to_variants_raw[preferred]:
                            preferred_to_variants_raw[preferred].append(raw)
                    continue
                if source == SOURCE_BUTUIJIAN_TONG:
                    # 情形4：同"X" → 不推荐词形-推荐词形（仅不推荐→推荐，推荐→不推荐列表由也作填入）
                    if variant in variant_to_preferred:
                        if variant_to_preferred[variant] != preferred:
                            merged = variant_to_preferred[variant] + "；" + preferred
                            variant_to_preferred[variant] = merged
                            print(f"[反查] variant_to_preferred 冲突已合并：'{variant}' -> '{merged}'")
                    else:
                        variant_to_preferred[variant] = preferred
                    if raw:
                        if variant not in variant_to_preferred_raw:
                            variant_to_preferred_raw[variant] = []
                        if raw not in variant_to_preferred_raw[variant]:
                            variant_to_preferred_raw[variant].append(raw)
                    continue

        # 单字三表反查：附列字 → 正体字（繁体/规范异体/其他异体 各一份）；遇键已存在时打印提示
        def _build_reverse_with_warn(forward: Dict[str, List[str]], dict_name: str) -> Dict[str, str]:
            rev: Dict[str, str] = {}
            for 正体, 列表 in forward.items():
                for 字 in 列表:
                    if 字 in rev:
                        if rev[字] != 正体:
                            merged = rev[字] + "；" + 正体
                            rev[字] = merged
                            print(f"[反查] {dict_name} 冲突已合并：'{字}' -> '{merged}'")
                    else:
                        rev[字] = 正体
            return rev

        single_char_traditional_to_standard = _build_reverse_with_warn(single_char_traditional, "single_char_traditional_to_standard")
        single_char_yitihuabiao_to_standard = _build_reverse_with_warn(single_char_yitihuabiao, "single_char_yitihuabiao_to_standard")
        single_char_yiti_other_to_standard = _build_reverse_with_warn(single_char_yiti_other, "single_char_yiti_other_to_standard")

        return (
            standard_to_variants,
            variant_to_standard,
            preferred_to_variants,
            variant_to_preferred,
            stats,
            standard_to_variants_raw,
            preferred_to_variants_raw,
            variant_to_preferred_raw,
            single_char_traditional,
            single_char_yitihuabiao,
            single_char_yiti_other,
            single_char_raw,
            single_char_traditional_to_standard,
            single_char_yitihuabiao_to_standard,
            single_char_yiti_other_to_standard,
            usage_notes,
        )

    def save_variant_forms(
        self,
        dict_name: str = "现汉7.mdx",
        limit: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> str:
        """
        从词典中提取多字异形与单字繁体/异体并保存到 reliable-proofreading-data 目录。
        规范词形-不规范词形 与 推荐词形-不推荐词形 为两类关系，分别保存。
        推荐词形-不推荐词形 同时拆分为单字表与多字表（共四表）：
        preferred_to_variants_single/multi、variant_to_preferred_single/multi。
        返回保存的 JSON 文件路径。
        """
        (
            standard_to_variants,
            variant_to_standard,
            preferred_to_variants,
            variant_to_preferred,
            stats,
            standard_to_variants_raw,
            preferred_to_variants_raw,
            variant_to_preferred_raw,
            single_char_traditional,
            single_char_yitihuabiao,
            single_char_yiti_other,
            single_char_raw,
            single_char_traditional_to_standard,
            single_char_yitihuabiao_to_standard,
            single_char_yiti_other_to_standard,
            usage_notes,
        ) = self.extract_all_from_dict(dict_name, limit=limit)
        out_dir = get_output_dir()
        base = dict_name.replace(".mdx", "").strip()
        safe_name = re.sub(r"[^\w\u4e00-\u9fff]", "_", base)
        if not filename:
            filename = f"异形词-{safe_name}.json"
        filepath = os.path.join(out_dir, filename)
        # 推荐词形-不推荐词形：拆分为单字表与多字表
        preferred_to_variants_single = {k: v for k, v in preferred_to_variants.items() if len(k) == 1}
        preferred_to_variants_multi = {k: v for k, v in preferred_to_variants.items() if len(k) > 1}
        variant_to_preferred_single = {k: v for k, v in variant_to_preferred.items() if len(k) == 1}
        variant_to_preferred_multi = {k: v for k, v in variant_to_preferred.items() if len(k) > 1}
        data = {
            "source": dict_name,
            "stats": stats,
            "standard_to_variants": standard_to_variants,
            "variant_to_standard": variant_to_standard,
            "preferred_to_variants": preferred_to_variants,
            "variant_to_preferred": variant_to_preferred,
            "preferred_to_variants_single": preferred_to_variants_single,
            "preferred_to_variants_multi": preferred_to_variants_multi,
            "variant_to_preferred_single": variant_to_preferred_single,
            "variant_to_preferred_multi": variant_to_preferred_multi,
        }
        # 所有 raw 字典合成单层字典 raw_notes：键=词形，值=原始匹配列表（多来源累积，值不同时多条）
        raw_notes_flat: Dict[str, List[str]] = {}
        for d in (standard_to_variants_raw, preferred_to_variants_raw, variant_to_preferred_raw, single_char_raw):
            for k, v in d.items():
                raw_notes_flat.setdefault(k, []).extend(v)
        if raw_notes_flat:
            data["raw_notes"] = raw_notes_flat
        if usage_notes:
            data["usage_notes"] = usage_notes
        if single_char_traditional:
            data["single_char_traditional"] = single_char_traditional
        if single_char_yitihuabiao:
            data["single_char_yitihuabiao"] = single_char_yitihuabiao
        if single_char_yiti_other:
            data["single_char_yiti_other"] = single_char_yiti_other
        if single_char_traditional_to_standard:
            data["single_char_traditional_to_standard"] = single_char_traditional_to_standard
        if single_char_yitihuabiao_to_standard:
            data["single_char_yitihuabiao_to_standard"] = single_char_yitihuabiao_to_standard
        if single_char_yiti_other_to_standard:
            data["single_char_yiti_other_to_standard"] = single_char_yiti_other_to_standard
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        n_guifan_bukuifan = stats.get(SOURCE_GUIFAN_BUKUIFAN, 0)
        n_yezuo = stats.get(SOURCE_TUIJIAN_YEZUO, 0)
        n_tong = stats.get(SOURCE_BUTUIJIAN_TONG, 0)
        n_fanti = stats.get(SINGLE_CHAR_FANTI, 0)
        n_guifan = stats.get(SINGLE_CHAR_GUIFAN, 0)
        n_other = stats.get(SINGLE_CHAR_OTHER, 0)
        print(
            f"异形词已写入：{filepath}，规范词形-不规范词形 {len(standard_to_variants)} 条（{n_guifan_bukuifan}），"
            f"推荐词形-不推荐词形 {len(preferred_to_variants)} 条（也作 {n_yezuo}，同 {n_tong}）；"
            f"推荐-不推荐 单字 {len(preferred_to_variants_single)}/{len(variant_to_preferred_single)}，多字 {len(preferred_to_variants_multi)}/{len(variant_to_preferred_multi)}；"
            f"字 繁体 {n_fanti}、规范异体 {n_guifan}、其他异体 {n_other}。"
        )
        return filepath


if __name__ == "__main__":
    extractor = VariantFormsExtractor()
    if extractor.mdict_manager:
        # 乌拉
        # 凡例
        # 枝丫
        # 阀阅
        # 保姆
        # content = extractor.mdict_manager.query("现汉7.mdx", "为")
        # if content:
        #     print("原始数据片段:", content)
        extractor.save_variant_forms("现汉7.mdx", limit=None)
    else:
        print("未配置 MdictManager，仅运行了枝丫解析测试。")

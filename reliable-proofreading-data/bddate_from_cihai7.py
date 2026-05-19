"""
从cihai7.mdx 中提取人物生卒年，存放到 reliable-proofreading-data 下。

提取格式：
1) 无标签、正文中直接出现：人名（生卒年），如
   - 李白（701—762）、李白（1910—1949）
   - 庄子（约前369—前286）
2) 有标签：<bddate>生卒年</bddate>，人名以词条名为准，如
   - 王维 条内：<bddate>701？—761</bddate>
   - 孔子 条内：<bddate>前551—前479</bddate>

说明：生年/卒年可能缺一；“？”表示不确定；“前”表示公元前；“约”表示大约。

用法概览：
  python bddate_from_cihai7.py
      使用 .mdictlist 中找到的“cihai7.mdx”，从头开始完整提取。

  python bddate_from_cihai7.py --mdx "D:/通用资料/工具书/通用电子词典/1古汉语/cihai7/离线版/cihai7.mdx"
      直接指定 mdx 路径（推荐），从头开始完整提取。

  python bddate_from_cihai7.py --debug
  python bddate_from_cihai7.py --mdx "D:/通用资料/工具书/通用电子词典/1古汉语/cihai7/离线版/cihai7.mdx" --debug
      调试模式：不做提取，只把若干词条原文写入 cihai7_bddate_debug.txt。

增量/断点续跑：
  # 第一次：从头开始，只处理前 5000 条
  python bddate_from_cihai7.py --mdx "D:/通用资料/工具书/通用电子词典/1古汉语/cihai7/离线版/cihai7.mdx" --start-index 0 --limit 5000

  # 后续：不指定 --start-index，则自动从 hai7.json 中的 last_index 继续；
  # 仍然限制每次最多处理 5000 条
  python bddate_from_cihai7.py --mdx "D:/通用资料/工具书/通用电子词典/1古汉语/cihai7/离线版/cihai7.mdx" --limit 5000

说明（输出文件 hai7.json）：
  - 每处理完一个词条，都会立即重写 hai7.json；
  - 结构中包含：
      {
        "source": "cihai7.mdx",
        "stats": {"bddate": ..., "inline": ...},
        "person_birth_death": { ... },
        "last_index": N
      }
    其中 last_index 表示“已经处理完的最后一条词条索引 + 1”，
    下次不带 --start-index 运行时，会自动从该位置继续。
"""

import os
import re
import json
import sys
from typing import Dict, List, Tuple, Optional, Any

try:
    from src.special_checker.mdict import MdictManager, create_mdict_backend
    from src.special_checker.chinese import is_chinese_character
except ImportError:
    try:
        from special_checker.mdict import MdictManager, create_mdict_backend
        from special_checker.chinese import is_chinese_character
    except ImportError:
        try:
            from mdict import MdictManager, create_mdict_backend
            from chinese import is_chinese_character
        except ImportError:
            MdictManager = None  # type: ignore
            create_mdict_backend = None  # type: ignore
            def is_chinese_character(char: str) -> bool:  # type: ignore
                return "\u4e00" <= char <= "\u9fff"

RELIABLE_PROOFREADING_DATA_DIR = "reliable-proofreading-data"
DICT_NAME_CIHAI7 = "cihai7.mdx"

SOURCE_BDDATE = "bddate"
SOURCE_INLINE = "inline"


def _project_root() -> str:
    """项目根目录（与 get_output_dir 一致）。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(base) == "src":
        return os.path.dirname(base)
    return base


def get_output_dir() -> str:
    """获取 reliable-proofreading-data 的绝对路径，不存在则创建。"""
    root = _project_root()
    out_dir = os.path.join(root, RELIABLE_PROOFREADING_DATA_DIR)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _strip_html(s: str) -> str:
    """去掉 HTML 标签，保留纯文本。"""
    return re.sub(r"<[^>]+>", "", s).strip()


def _default_mdictlist_path() -> str:
    """默认 .mdictlist 路径（基于项目根），便于从任意目录运行脚本。"""
    return os.path.join(_project_root(), "src", "resource", ".mdictlist")


class BirthDeathExtractor:
    """从cihai7中提取人物生卒年的提取器。"""

    def __init__(
        self,
        mdict_manager: Optional[object] = None,
        mdictlist_path: Optional[str] = None,
        mdx_path: Optional[str] = None,
    ):
        if mdx_path and create_mdict_backend is not None:
            self.mdict_manager = create_mdict_backend(mdx_path)
        elif mdict_manager is None and MdictManager is not None:
            path = mdictlist_path or _default_mdictlist_path()
            self.mdict_manager = MdictManager(mdictlist_path=path)
        else:
            self.mdict_manager = mdict_manager
        self._compile_regex()

    def _compile_regex(self) -> None:
        # <bddate>...</bddate>，内容保留原样（约、前、？、— 等）
        self._re_bddate = re.compile(r"<bddate>\s*([^<]+?)\s*</bddate>", re.IGNORECASE)

        # 人名（生卒年）：人名 2~15 字，括号内为生卒年。
        # 为避免把“(2)(3)”这类编号当作生卒年，这里要求：
        #   - 年份至少三位数字（约 100 年以上），
        #   - 或包含“前”+三位数字，
        #   - 可带“约”“前”“？”以及“—/-”连接卒年。
        self._re_inline = re.compile(
            r"([^\s<（(]{2,15})"  # 人名（不含空格、<、括号）
            r"[（(]"
            r"((?:约)?(?:前)?\d{3,4}[？?]?(?:\s*[—\-]\s*(?:前)?\d{0,4}[？?]?)?)"  # 生卒年（至少三位数字）
            r"[）)]"
        )

        # 年号：某某年号（年代），用于单独存储，如：
        # “西燕慕容永年号（386—394）”。仅用“年号”作为锚点，前缀部分在代码中用
        # is_chinese_character 逐字符向前扩展，直到遇到第一个非汉字为止。
        self._re_nianhao = re.compile(
            r"(年号)\s*[（(]"
            r"((?:前)?\d{3,4}[？?]?(?:\s*[—\-]\s*(?:前)?\d{0,4}[？?]?)?)"
            r"[）)]"
        )

    def _extract_bddate_tags(self, content: str) -> List[str]:
        """从正文中提取所有 <bddate>...</bddate> 内的生卒年字符串（保留原样）。"""
        return self._re_bddate.findall(content)

    def _extract_inline_birth_death(self, content: str) -> List[Tuple[str, str]]:
        """从正文中提取所有人名（生卒年）形式，返回 [(人名, 生卒年原始字符串), ...]。"""
        # 先去标签再匹配，避免 HTML 把人名或括号内容拆开
        text = _strip_html(content)
        pairs: List[Tuple[str, str]] = []
        for m in self._re_inline.finditer(text):
            name = m.group(1).strip()
            date_str = m.group(2).strip()
            if not name or not date_str:
                continue
            # 排除明显非人名的：纯数字、过长、包含句读/分号等
            if name.isdigit() or len(name) > 10:
                continue
            if re.search(r"[；;，,。！？!?：:、]", name):
                continue
            # 再次防御：若括号内不含“前”/“—/-”，且数字总长度不足 3，则视为非生卒年（多为编号 1/2/3）
            digits = re.sub(r"\D", "", date_str)
            if "前" not in date_str and "—" not in date_str and "-" not in date_str and len(digits) < 3:
                continue
            pairs.append((name, date_str))
        return pairs

    def extract_from_content(
        self, content: str, entry_headword: str
    ) -> List[Tuple[str, str, str]]:
        """
        从一条词条内容中提取 (人名, 生卒年原始字符串, 来源)。
        来源：SOURCE_BDDATE | SOURCE_INLINE。
        """
        if not content:
            return []
        result: List[Tuple[str, str, str]] = []

        # 1) <bddate>...</bddate>：人名为词条名
        for date_str in self._extract_bddate_tags(content):
            date_str = date_str.strip()
            if date_str and entry_headword:
                result.append((entry_headword.strip(), date_str, SOURCE_BDDATE))

        # 2) 人名（生卒年）：要求括号前名称与词条名严格一致，
        #    避免把拼音、释义短语等当作“人名”。
        plain_hw = entry_headword.strip() if entry_headword else ""
        for name, date_str in self._extract_inline_birth_death(content):
            if plain_hw and name != plain_hw:
                continue
            result.append((name, date_str, SOURCE_INLINE))

        return result

    def _extract_era_years(
        self, content: str, entry_headword: str
    ) -> List[Dict[str, str]]:
        """
        从正文中提取“某某年号（年代）”形式的年号数据，仅用于单独存储，不计入人物。
        例如“西燕慕容永年号（386—394）”。
        """
        text = _strip_html(content)
        out: List[Dict[str, str]] = []
        for m in self._re_nianhao.finditer(text):
            years = m.group(2).strip()
            if not years:
                continue
            # 从“年号”二字向前回溯，收集连续汉字作为“某某”
            start_idx = m.start(1)
            i = start_idx - 1
            prefix_chars: List[str] = []
            while i >= 0:
                ch = text[i]
                if is_chinese_character(ch):
                    prefix_chars.append(ch)
                    i -= 1
                    continue
                break
            prefix = "".join(reversed(prefix_chars)).strip()
            if not prefix:
                continue
            label = prefix + "年号"
            out.append({"label": label, "raw": years})
        return out

    def save_birth_death(
        self,
        dict_name: str = DICT_NAME_CIHAI7,
        start_index: Optional[int] = None,
        limit: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> str:
        """
        提取人物生卒年并保存为 JSON。支持分段、多次运行增量写入：
        - 每处理完一个词条，就立刻把合并后的结果整体写回 JSON；
        - JSON 中记录 last_index，便于下一次从该位置继续。
        """
        if not self.mdict_manager:
            raise RuntimeError("mdict_manager 未配置，无法读取词典")

        out_dir = get_output_dir()
        base = dict_name.replace(".mdx", "").strip()
        safe_name = re.sub(r"[^\w\u4e00-\u9fff]", "_", base)
        if not filename:
            filename = f"birth_death_{safe_name}.json"
        filepath = os.path.join(out_dir, filename)

        # 读取已有结果（若存在），合并 person_birth_death / stats / era_years，并确定起始位置
        existing_persons: Dict[str, List[str]] = {}
        existing_eras: Dict[str, List[Dict[str, Any]]] = {}
        stats: Dict[str, int] = {SOURCE_BDDATE: 0, SOURCE_INLINE: 0}
        last_index: int = 0
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    old = json.load(f)
                raw_persons = old.get("person_birth_death", {}) or {}
                # 兼容旧格式 [{"raw": "..."}]，统一为 ["..."]
                for k, lst in raw_persons.items():
                    existing_persons[k] = [
                        (x.get("raw") if isinstance(x, dict) else x)
                        for x in lst
                        if (x.get("raw") if isinstance(x, dict) else x)
                    ]
                existing_eras = old.get("era_years", {}) or {}
                old_stats = old.get("stats", {})
                for k in (SOURCE_BDDATE, SOURCE_INLINE):
                    if isinstance(old_stats, dict) and k in old_stats:
                        stats[k] = int(old_stats.get(k, 0))
                if isinstance(old.get("last_index"), int):
                    last_index = int(old["last_index"])
            except Exception as e:
                print(f"读取已有文件失败，将从空结果开始：{e}")

        # 未传 --start-index 时用 JSON 中的 last_index 续跑；显式传 0 则从头开始
        if start_index is None or start_index < 0:
            start_index = last_index
        else:
            start_index = int(start_index)

        entries = self.mdict_manager.entries(dict_name, None)
        total = len(entries)
        if total == 0:
            print(
                "警告：未获取到任何词条。可尝试：1) 用 --mdx \"完整路径/cihai7.mdx\" 直接指定词典；"
                "2) 若曾解包失败，删除同目录下的 .db 文件后重跑以强制重新解包；"
                "3) 用 --debug 查看 cihai7_bddate_debug.txt。"
            )
            return filepath

        if start_index >= total:
            print(f"start_index={start_index} 已不小于总词条数 {total}，无需继续。")
            return filepath

        if limit is not None and limit > 0:
            end_index = min(total, start_index + limit)
        else:
            end_index = total

        print(f"本次处理范围：[{start_index}, {end_index}) / 总 {total} 条。")

        # 主循环：边处理边写回 JSON
        for i in range(start_index, end_index):
            entry = entries[i]
            content = self.mdict_manager.query(dict_name, entry)
            if not content:
                continue
            headword = _strip_html(entry).strip() or entry.strip()
            triples = self.extract_from_content(content, headword)
            era_items = self._extract_era_years(content, headword)

            # 先处理年号：仅根据“某某年号（年代）”模式，不计入人物列表
            if era_items:
                bucket_era = existing_eras.setdefault(headword, [])
                for item in era_items:
                    if not any(
                        e["label"] == item["label"] and e["raw"] == item["raw"]
                        for e in bucket_era
                    ):
                        bucket_era.append(item)

            if not triples:
                # 即使本条没数据，仍更新 last_index 并写回（保证可从任何位置断点续跑）
                last_index = i + 1
                data = {
                    "source": dict_name,
                    "stats": stats,
                    "person_birth_death": existing_persons,
                    "era_years": existing_eras,
                    "last_index": last_index,
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                continue

            for name, date_str, source in triples:
                stats[source] = stats.get(source, 0) + 1
                bucket = existing_persons.setdefault(name, [])
                if date_str not in bucket:
                    bucket.append(date_str)

            last_index = i + 1
            data = {
                "source": dict_name,
                "stats": stats,
                "person_birth_death": existing_persons,
                "era_years": existing_eras,
                "last_index": last_index,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if (i + 1 - start_index) % 100 == 0:
                print(f"已处理 {i + 1 - start_index} 条（全局 {i + 1}/{total}）…")

        n_bd = stats.get(SOURCE_BDDATE, 0)
        n_in = stats.get(SOURCE_INLINE, 0)
        print(
            f"人物生卒年已写入：{filepath}，"
            f"当前共 {len(existing_persons)} 人，"
            f"<bddate> {n_bd} 条、正文括号 {n_in} 条。"
        )
        return filepath


def _debug_print_content(
    dict_name: str = DICT_NAME_CIHAI7, mdx_path: Optional[str] = None
) -> None:
    """查询若干词条并将原始内容写入 debug 文件（UTF-8），用于确认cihai条目的实际格式。"""
    if mdx_path and create_mdict_backend is not None:
        adapter = create_mdict_backend(mdx_path)
        if adapter is None:
            return
        lines: List[str] = ["使用 mdx 路径: " + mdx_path]
    elif MdictManager is not None:
        adapter = MdictManager(mdictlist_path=_default_mdictlist_path())
        lines = []
    else:
        print("未配置 MdictManager / create_mdict_backend")
        return
    out_path = os.path.join(get_output_dir(), "cihai7_bddate_debug.txt")
    entries = adapter.entries(dict_name, limit=30)
    lines.append("前30个词条键: " + repr(entries))
    lines.append("词条总数: " + str(adapter.count(dict_name)))
    test_entries = ["李白", "王维", "孔子", "庄子"] + (entries[:3] if entries else [])
    for word in test_entries:
        content = adapter.query(dict_name, word)
        lines.append(f"\n{'='*60}\nentry: {word!r}\n{'='*60}")
        if content is None:
            lines.append("(未查到)")
        else:
            snippet = content[:3000] if len(content) > 3000 else content
            lines.append(snippet)
            if len(content) > 3000:
                lines.append("...(截断)")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("调试内容已写入:", out_path)


def _parse_args() -> Tuple[Optional[str], bool, Optional[int], Optional[int]]:
    """
    解析命令行：
    --mdx 路径、--debug、--start-index N、--limit N。
    返回 (mdx_path 或 None, 是否 debug, start_index, limit)。
    """
    mdx_path: Optional[str] = None
    debug = False
    start_index: Optional[int] = None
    limit: Optional[int] = None
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        if argv[i] == "--mdx" and i + 1 < len(argv):
            mdx_path = argv[i + 1].strip().strip('"')
            i += 2
            continue
        if argv[i] == "--debug":
            debug = True
            i += 1
            continue
        if argv[i] == "--start-index" and i + 1 < len(argv):
            try:
                start_index = int(argv[i + 1])
            except ValueError:
                start_index = None
            i += 2
            continue
        if argv[i] == "--limit" and i + 1 < len(argv):
            try:
                limit = int(argv[i + 1])
            except ValueError:
                limit = None
            i += 2
            continue
        i += 1
    return mdx_path, debug, start_index, limit


if __name__ == "__main__":
    mdx_path_arg, do_debug, start_index_arg, limit_arg = _parse_args()
    if do_debug:
        _debug_print_content(mdx_path=mdx_path_arg)
        sys.exit(0)
    extractor = BirthDeathExtractor(mdx_path=mdx_path_arg) if mdx_path_arg else BirthDeathExtractor()
    if extractor.mdict_manager:
        extractor.save_birth_death(
            DICT_NAME_CIHAI7,
            start_index=start_index_arg,
            limit=limit_arg,
            filename="hai7.json",
        )
    else:
        print("未配置 MdictManager，无法读取cihai7.mdx。")

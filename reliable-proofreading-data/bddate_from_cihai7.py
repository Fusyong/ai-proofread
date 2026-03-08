"""
从辞海第七版.mdx 中提取人物生卒年，存放到 reliable-proofreading-data 下。

提取格式：
1) 无标签、正文中直接出现：人名（生卒年），如
   - 李白（701—762）、李白（1910—1949）
   - 庄子（约前369—前286）
2) 有标签：<bddate>生卒年</bddate>，人名以词条名为准，如
   - 王维 条内：<bddate>701？—761</bddate>
   - 孔子 条内：<bddate>前551—前479</bddate>

说明：生年/卒年可能缺一；“？”表示不确定；“前”表示公元前；“约”表示大约。

用法：
  python bddate_from_cihai7.py                    # 使用 .mdictlist 中的辞海第七版
  python bddate_from_cihai7.py --mdx "D:/.../辞海第七版.mdx"   # 直接指定 mdx 路径
  python bddate_from_cihai7.py --debug            # 调试：写入 cihai7_bddate_debug.txt
  python bddate_from_cihai7.py --mdx "D:/.../辞海第七版.mdx" --debug
"""

import os
import re
import json
import sys
from typing import Dict, List, Tuple, Optional, Any

try:
    from mdict_utils.reader import query as mdict_query, MDX as MdictMDX
except ImportError:
    mdict_query = None  # type: ignore
    MdictMDX = None  # type: ignore

try:
    from src.special_checker.mdict import MdictManager, MdictDatabase
except ImportError:
    try:
        from special_checker.mdict import MdictManager, MdictDatabase
    except ImportError:
        try:
            from mdict import MdictManager, MdictDatabase
        except ImportError:
            MdictManager = None  # type: ignore
            MdictDatabase = None  # type: ignore

RELIABLE_PROOFREADING_DATA_DIR = "reliable-proofreading-data"
DICT_NAME_CIHAI7 = "辞海第七版.mdx"

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


class _DirectMdictAdapter:
    """对单个 MdictDatabase 的适配，接口与 MdictManager 的 entries/query 用法一致。"""

    def __init__(self, db: "MdictDatabase", dict_name: str):
        self._db = db
        self._dict_name = dict_name

    def entries(self, dict_name: str, limit: Optional[int] = None) -> List[str]:
        return self._db.entries(limit)

    def query(self, dict_name: str, word: str) -> Optional[str]:
        return self._db.query(word)

    def count(self, dict_name: str) -> int:
        return self._db.count()


class _RawMdictAdapter:
    """直接用 mdict_utils.reader 读 mdx 文件，不经过 SQLite。query(path, word) + MDX(path).keys()。"""

    def __init__(self, mdx_path: str):
        self._path = mdx_path
        self._mdx = MdictMDX(mdx_path) if MdictMDX else None
        self._keys_cache: Optional[List[str]] = None

    def _ensure_keys(self) -> List[str]:
        """首次调用时遍历 MDX.keys() 并缓存；之后直接返回缓存。"""
        if self._keys_cache is not None:
            return self._keys_cache
        if self._mdx is None or mdict_query is None:
            self._keys_cache = []
            return self._keys_cache
        out: List[str] = []
        for k in self._mdx.keys():
            out.append(k.decode("utf-8") if isinstance(k, bytes) else k)
        self._keys_cache = out
        return self._keys_cache

    def entries(self, dict_name: str, limit: Optional[int] = None) -> List[str]:
        keys = self._ensure_keys()
        return keys[:limit] if limit else keys

    def query(self, dict_name: str, word: str) -> Optional[str]:
        if mdict_query is None:
            return None
        try:
            return mdict_query(self._path, word)
        except Exception:
            return None

    def count(self, dict_name: str) -> int:
        return len(self._ensure_keys())


class BirthDeathExtractor:
    """从辞海第七版中提取人物生卒年的提取器。"""

    def __init__(
        self,
        mdict_manager: Optional[object] = None,
        mdictlist_path: Optional[str] = None,
        mdx_path: Optional[str] = None,
    ):
        if mdx_path and (MdictMDX is not None and mdict_query is not None):
            self.mdict_manager = _RawMdictAdapter(mdx_path)
        elif mdx_path and MdictDatabase is not None:
            self.mdict_manager = _DirectMdictAdapter(
                MdictDatabase(mdx_path), dict_name=DICT_NAME_CIHAI7
            )
        elif mdict_manager is None and MdictManager is not None:
            path = mdictlist_path or _default_mdictlist_path()
            self.mdict_manager = MdictManager(mdictlist_path=path)
        else:
            self.mdict_manager = mdict_manager
        self._compile_regex()

    def _compile_regex(self) -> None:
        # <bddate>...</bddate>，内容保留原样（约、前、？、— 等）
        self._re_bddate = re.compile(r"<bddate>\s*([^<]+?)\s*</bddate>", re.IGNORECASE)

        # 人名（生卒年）：人名 2~15 字，括号内为生卒年
        # 生卒年格式：约? 前? 数字 ？? [—\-] 前? 数字 ？?  或仅生年
        # 避免匹配到非日期的括号内容，要求括号内至少含数字和连接符或仅数字
        self._re_inline = re.compile(
            r"([^\s<（(]{2,15})"  # 人名（不含空格、<、括号）
            r"[（(]"
            r"((?:约)?(?:前)?\d+[？?]?(?:\s*[—\-]\s*(?:前)?\d+[？?]?)?)"  # 生卒年
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
            # 排除明显非人名的：纯数字、过长等
            if name.isdigit() or len(name) > 10:
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

        # 2) 人名（生卒年）
        for name, date_str in self._extract_inline_birth_death(content):
            result.append((name, date_str, SOURCE_INLINE))

        return result

    def extract_all_from_dict(
        self,
        dict_name: str = DICT_NAME_CIHAI7,
        limit: Optional[int] = None,
        progress_interval: int = 500,
    ) -> Tuple[
        Dict[str, List[Dict[str, Any]]],
        Dict[str, int],
    ]:
        """
        遍历词典所有词条，提取人物生卒年。
        返回：
        - person_birth_death: 人名 -> [ {"raw": "701—762", "entry": "李白", "source": "inline"}, ... ]
        - stats: 统计 bddate / inline 条数
        """
        if not self.mdict_manager:
            return {}, {SOURCE_BDDATE: 0, SOURCE_INLINE: 0}

        entries = self.mdict_manager.entries(dict_name, limit)
        total = len(entries)
        if total == 0:
            print(
                "警告：未获取到任何词条。可尝试：1) 用 --mdx \"完整路径/辞海第七版.mdx\" 直接指定词典；"
                "2) 若曾解包失败，删除同目录下的 .db 文件后重跑以强制重新解包；"
                "3) 用 --debug 查看 cihai7_bddate_debug.txt。"
            )
        person_birth_death: Dict[str, List[Dict[str, Any]]] = {}
        stats: Dict[str, int] = {SOURCE_BDDATE: 0, SOURCE_INLINE: 0}

        for i, entry in enumerate(entries):
            if progress_interval and i > 0 and i % progress_interval == 0:
                print(f"已处理 {i}/{total} 条…")
            content = self.mdict_manager.query(dict_name, entry)
            if not content:
                continue
            # 词条名作为 headword（若含 HTML 则取纯文本）
            headword = _strip_html(entry).strip() or entry.strip()
            for name, date_str, source in self.extract_from_content(content, headword):
                stats[source] = stats.get(source, 0) + 1
                record = {"raw": date_str, "entry": headword, "source": source}
                if name not in person_birth_death:
                    person_birth_death[name] = []
                # 去重：同一人名、同一 raw、同一 entry 只保留一条
                if not any(
                    r["raw"] == date_str and r["entry"] == headword
                    for r in person_birth_death[name]
                ):
                    person_birth_death[name].append(record)

        return person_birth_death, stats

    def save_birth_death(
        self,
        dict_name: str = DICT_NAME_CIHAI7,
        limit: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> str:
        """提取人物生卒年并保存为 JSON。返回保存路径。"""
        person_birth_death, stats = self.extract_all_from_dict(
            dict_name, limit=limit, progress_interval=500
        )
        out_dir = get_output_dir()
        base = dict_name.replace(".mdx", "").strip()
        safe_name = re.sub(r"[^\w\u4e00-\u9fff]", "_", base)
        if not filename:
            filename = f"birth_death_{safe_name}.json"
        filepath = os.path.join(out_dir, filename)

        data = {
            "source": dict_name,
            "stats": stats,
            "person_birth_death": person_birth_death,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        n_bd = stats.get(SOURCE_BDDATE, 0)
        n_in = stats.get(SOURCE_INLINE, 0)
        print(
            f"人物生卒年已写入：{filepath}，"
            f"共 {len(person_birth_death)} 人，"
            f"<bddate> {n_bd} 条、正文括号 {n_in} 条。"
        )
        return filepath


def _debug_print_content(
    dict_name: str = DICT_NAME_CIHAI7, mdx_path: Optional[str] = None
) -> None:
    """查询若干词条并将原始内容写入 debug 文件（UTF-8），用于确认辞海条目的实际格式。"""
    if mdx_path and MdictMDX is not None and mdict_query is not None:
        adapter = _RawMdictAdapter(mdx_path)
        lines: List[str] = ["使用原始 mdict_utils.reader + 路径: " + mdx_path]
    elif mdx_path and MdictDatabase is not None:
        adapter = _DirectMdictAdapter(MdictDatabase(mdx_path), dict_name)
        lines = ["使用 MdictDatabase + 路径: " + mdx_path]
    elif MdictManager is not None:
        adapter = MdictManager(mdictlist_path=_default_mdictlist_path())
        lines = []
    else:
        print("未配置 MdictManager / MdictDatabase / mdict_utils.reader")
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


def _parse_args() -> Tuple[Optional[str], bool]:
    """解析命令行：--mdx 路径、--debug。返回 (mdx_path 或 None, 是否 debug)。"""
    mdx_path: Optional[str] = None
    debug = False
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
        i += 1
    return mdx_path, debug


if __name__ == "__main__":
    mdx_path_arg, do_debug = _parse_args()
    if do_debug:
        _debug_print_content(mdx_path=mdx_path_arg)
        sys.exit(0)
    extractor = BirthDeathExtractor(mdx_path=mdx_path_arg) if mdx_path_arg else BirthDeathExtractor()
    if extractor.mdict_manager:
        extractor.save_birth_death(
            DICT_NAME_CIHAI7,
            limit=None,
            filename="hai7.json",
        )
    else:
        print("未配置 MdictManager，无法读取辞海第七版.mdx。")

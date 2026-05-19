"""
解析多个mdict词典数据文件，萃取词条信息，以备综合查询
"""
import os
import zlib
import sqlite3
import time
from typing import List, Optional

from mdict_utils.reader import unpack_to_db, MDX


def companion_db_path(mdx_path: str) -> str:
    """与 mdx 同目录、同主文件名的 .db 路径。"""
    path = os.path.normpath(mdx_path)
    db_name = os.path.basename(path).replace(".mdx", ".db")
    return os.path.join(os.path.dirname(path), db_name)


class MdictDatabase:
    """词典数据库管理类，每次实例化只管理一个词典数据库"""
    def __init__(self, mdx_path: str, encoding: str = 'utf-8'):
        if not mdx_path:
            raise ValueError("mdx_path 参数是必需的")

        self.mdx_path = mdx_path
        self.encoding = encoding
        self.mdx = MDX(mdx_path, encoding=encoding)
        self.db_dir = os.path.dirname(mdx_path)
        self.db_path = companion_db_path(mdx_path)

    def info(self):
        """获取词典信息（从数据库）"""
        if not self._ensure_database_exists():
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取词典信息表
                c = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mdx_info'")
                if c.fetchone():
                    # 如果存在信息表，从中读取
                    c = conn.execute('SELECT * FROM mdx_info')
                    info = {}
                    for row in c.fetchall():
                        if len(row) >= 2:
                            info[str(row[0])] = str(row[1])
                    return info
                else:
                    # 如果不存在信息表，尝试从MDX文件获取并保存到数据库
                    if self.mdx:
                        info = {}
                        for key, value in self.mdx.header.items():
                            info[key.decode('utf-8')] = value.decode('utf-8')

                        # 创建信息表并保存
                        conn.execute('CREATE TABLE IF NOT EXISTS mdx_info (key TEXT, value TEXT)')
                        for key, value in info.items():
                            conn.execute('INSERT INTO mdx_info (key, value) VALUES (?, ?)', (key, value))
                        conn.commit()
                        return info
                    return {}
        except Exception as e:
            print(f"获取词典信息失败: {e}")
            return {}

    def count(self):
        """获取词条总数（从数据库）"""
        if not self._ensure_database_exists():
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.execute('SELECT COUNT(*) FROM mdx')
                result = c.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"获取词条总数失败: {e}")
            return 0

    def entries(self, limit: int = None):
        """获取词条列表（从数据库）"""
        if not self._ensure_database_exists():
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                if limit:
                    c = conn.execute('SELECT entry FROM mdx LIMIT ?', (limit,))
                else:
                    c = conn.execute('SELECT entry FROM mdx')

                entries = []
                for row in c.fetchall():
                    entries.append(str(row[0]))
                return entries
        except Exception as e:
            print(f"获取词条列表失败: {e}")
            return []

    def _ensure_database_exists(self):
        """确保数据库存在，如果不存在则创建"""
        if not os.path.exists(self.db_path):
            print("首次运行，正在解包词典到数据库...")
            start_time = time.time()
            try:
                # 确保目录存在
                os.makedirs(self.db_dir, exist_ok=True)
                unpack_to_db(self.db_dir, self.mdx_path)
                print(f"解包完成，耗时: {time.time() - start_time:.2f}秒")
                return True
            except Exception as e:
                print(f"解包失败: {e}")
                return False
        return True

    def query(self, word: str):
        """从数据库查询词条"""
        if not self._ensure_database_exists():
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.execute('SELECT paraphrase FROM mdx WHERE entry = ?', (word,))
                result = c.fetchone()
                if result:
                    # 解压缩数据
                    return zlib.decompress(result[0]).decode('utf-8')
                return None
        except sqlite3.OperationalError as e:
            print(f"数据库错误: {e}")
            return None

class MdictPathManager:
    """词典路径管理类"""
    def __init__(self, mdictlist_path: str = 'src/resource/.mdictlist'):
        self.mdictlist_path = mdictlist_path

    def get_mdict_path_list(self):
        """读取 mdictlist 文件"""
        try:
            with open(self.mdictlist_path, 'r', encoding='utf-8') as file:
                mdx_paths = file.readlines()
            return [path.strip() for path in mdx_paths]
        except FileNotFoundError:
            print(f"未找到词典列表文件: {self.mdictlist_path}")
            return []

    def get_mdict_path_by_name(self, name: str):
        """根据名称获取词典路径"""
        # 名称必须以.mdx结尾
        if not name.endswith('.mdx'):
            name += '.mdx'
        mdx_paths = self.get_mdict_path_list()
        return [path.strip() for path in mdx_paths if name in path]


class MdictManager:
    """词典管理器类，用于管理多个词典"""
    def __init__(self, mdictlist_path: str = 'src/resource/.mdictlist'):
        self.path_manager = MdictPathManager(mdictlist_path)
        self._mdicts = {}  # 缓存已加载的词典

    def load_mdict(self, name: str, encoding: str = 'utf-8'):
        """加载指定词典"""
        if name not in self._mdicts:
            paths = self.path_manager.get_mdict_path_by_name(name)
            if paths:
                mdx_path = paths[0]
                self._mdicts[name] = MdictDatabase(mdx_path, encoding)
            else:
                raise ValueError(f"未找到词典: {name}")
        return self._mdicts[name]

    def info(self, name: str):
        """获取词典信息"""
        mdict = self.load_mdict(name)
        return mdict.info()

    def count(self, name: str):
        """获取指定名称词典的词条总数"""
        mdict = self.load_mdict(name)
        return mdict.count()

    def entries(self, name: str, limit: int = None):
        """获取指定名称词典的词条列表"""
        mdict = self.load_mdict(name)
        return mdict.entries(limit)

    def query(self, name: str, word: str):
        """查询指定名称词典中的词条"""
        mdict = self.load_mdict(name)
        return mdict.query(word)

    def is_word_in(self, name: str, word: str) -> bool:
        """检查词语是否在指定词典中"""
        result = self.query(name, word)
        return result is not None


class SingleMdictBackend:
    """对单个 MdictDatabase 的适配，接口与 MdictManager 的 entries/query 一致。"""

    def __init__(self, db: MdictDatabase):
        self._db = db

    def entries(self, dict_name: str, limit: Optional[int] = None) -> List[str]:
        return self._db.entries(limit)

    def query(self, dict_name: str, word: str) -> Optional[str]:
        return self._db.query(word)

    def count(self, dict_name: str) -> int:
        return self._db.count()


def create_mdict_backend(
    mdx_path: str,
    encoding: str = "utf-8",
    *,
    verbose: bool = True,
) -> Optional[object]:
    """
    为单个 mdx 文件创建查询后端，统一走 MdictDatabase（SQLite）。
    若同目录尚无配套 .db，首次访问时会从 MDX 解包建库。
    """
    path = mdx_path.strip().strip('"').strip("'")
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        if verbose:
            print(f"错误：MDX 文件不存在: {path}")
        return None

    db_path = companion_db_path(path)
    if verbose:
        if os.path.isfile(db_path):
            print(f"使用 MdictDatabase（已有 .db）: {path}")
        else:
            print(f"使用 MdictDatabase（将解包建库）: {path}")
    return SingleMdictBackend(MdictDatabase(path, encoding))


def query_mdx(mdx_path: str, word: str, encoding: str = "utf-8") -> Optional[str]:
    """查询单个词条，统一走 MdictDatabase（无 .db 时先解包建库）。"""
    path = os.path.normpath(mdx_path)
    return MdictDatabase(path, encoding).query(word)


def info(mdx: MDX):
    """获取词典信息（向后兼容）"""
    # 创建一个临时的 MdictDatabase 实例来获取信息
    # 注意：这里需要提供一个有效的路径，所以创建一个临时文件路径
    import tempfile
    temp_path = tempfile.mktemp(suffix='.mdx')
    try:
        db_manager = MdictDatabase(temp_path, "utf-8")
        db_manager.mdx = mdx
        return db_manager.info()
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    # 使用新的类结构
    manager = MdictManager()

    # mdx = manager.load_mdict("xh7.mdx")

    # # 词典信息
    # print(manager.info("xh7.mdx"))

    # # 条目
    # print(f"\nxh7.mdx 词条总数：{manager.count('xh7.mdx')}")
    # print(f"\nxhgf2.mdx 词条总数：{manager.count('xhgf2.mdx')}")
    # print(f"\nzhywdcd.mdx 词条总数：{manager.count('zhywdcd.mdx')}")
    # print(f"\nzhywdcd.mdx 词条总数：{manager.count('zhywdcd.mdx')}")
    # print(f"\nlycd.mdx 词条总数：{manager.count('lycd.mdx')}")
    # print(f"\nhyfydcd.mdx 词条总数：{manager.count('hyfydcd.mdx')}")
    # print(f"\ncy3wzb2021.mdx 词条总数：{manager.count('cy3wzb2021.mdx')}")
    # print(f"\ndacihai.mdx 词条总数：{manager.count('dacihai.mdx')}")
    # print(f"\nhydcdh2020.5.1.mdx 词条总数：{manager.count('hydcdh2020.5.1.mdx')}")

    # # 获取所有词条
    # print("\n词条列表：")
    # entries = manager.entries("xh7.mdx", 100)
    # for i, entry in enumerate(entries):
    #     print(f"{i} {entry}")

    # # 检查是否在现代汉语词典中
    # print(f"\n'多少'是否在现代汉语词典中: {manager.is_word_in('xh7.mdx', '多少')}")

    # # 从mdx查询特定词条
    # content = manager.query("xh7.mdx", '多少')
    # print(f"\n从MDX查询'多少': {content}")

    # # 从db查询特定词条
    # content = manager.query("xh7.mdx", '多少')
    # print(f"\n从数据库查询'多少': {content}")

    print(manager.query("zhywdcd.mdx", '薄'))


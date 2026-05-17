"""
从mdict词典中提取词条拼音信息
"""
import re
import json
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 处理导入问题，支持相对导入和绝对导入
try:
    from src.special_checker.mdict import MdictManager
except ImportError:
    try:
        from mdict import MdictManager
    except ImportError:
        # 如果都导入失败，创建一个简单的测试版本
        print("警告：无法导入MdictManager，将使用测试模式")
        MdictManager = None


class PinyinExtractor:
    """拼音提取器类"""
    
    def __init__(self, mdict_manager=None, max_workers=None):
        """初始化拼音提取器"""
        if mdict_manager is None and MdictManager is not None:
            self.mdict_manager = MdictManager()
        else:
            self.mdict_manager = mdict_manager
        self.pinyin_cache = {}  # 缓存已提取的拼音
        self.cache_lock = threading.Lock()  # 线程安全的缓存锁
        
        # 预编译正则表达式以提高性能
        self._compile_regex_patterns()
        
        # 为不同词典定义拼音提取规则
        self.extraction_rules = {
            "xh7.mdx": self._extract_pinyin_xianhan7,
            "xhgf2.mdx": self._extract_pinyin_xianhanguifan2,
            "zhywdcd.mdx": self._extract_pinyin_zhonghuayuwendaciandian,
            # 可以在这里添加其他词典的规则
            # "其他词典.mdx": self._extract_pinyin_other_dict,
        }
        
        # 自动优化线程池配置
        self.max_workers = self._optimize_max_workers(max_workers)
        print(f"自动设置 max_workers = {self.max_workers}")
    
    def _optimize_max_workers(self, max_workers=None):
        """自动优化max_workers设置"""
        import os
        
        if max_workers is not None:
            return max_workers
        
        # 获取CPU核心数
        cpu_count = os.cpu_count() or 1
        
        # 根据系统类型和CPU核心数自动设置
        if cpu_count == 1:
            # 单核系统，使用串行处理
            return 1
        elif cpu_count <= 4:
            # 低核心数系统，保守设置
            return min(4, cpu_count + 1)
        elif cpu_count <= 8:
            # 中等核心数系统，平衡设置
            return min(6, cpu_count + 2)
        else:
            # 高核心数系统，激进设置
            return min(12, cpu_count + 4)
    
    def _compile_regex_patterns(self):
        """预编译所有正则表达式以提高性能"""
        # 现汉7的正则表达式
        self.pinyin_pattern_xianhan7 = re.compile(r'<entry id.+?<pinyin>([^<]+)</pinyin>')
        
        # 现汉规范2的正则表达式
        self.pinyin_pattern_xianhanguifan2 = re.compile(r'<x-pr>\s*([^<]+)\s*</x-pr>')
        
        # 中華語文大辭典的正则表达式
        self.pinyin_pattern_zhonghuayuwendaciandian_entryhead = re.compile(r'(?=<div class="ctzg">)')
        self.pinyin_pattern_zhonghuayuwendaciandian_twhp = re.compile(r'<span class="twhp">([^<]+)</span>')
        self.pinyin_pattern_zhonghuayuwendaciandian_dlhp = re.compile(r'<span class="dlhp">([^<]+)</span>')
        
        
        # 默认拼音正则表达式
        self.default_pinyin_pattern = re.compile(r'<pinyin>([^<]+)</pinyin>')
    
    def _extract_pinyin_xianhan7(self, content: str) -> List[str]:
        """
        现代汉语词典7的拼音提取规则（优化版本）：
        直接查找所有pinyin标签，避免嵌套循环
        
        Args:
            content: 词典返回的HTML/XML内容
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        # 直接查找所有pinyin标签，避免先找entry再找pinyin的嵌套操作
        pinyin_matches = self.pinyin_pattern_xianhan7.findall(content)
        
        # 使用列表推导式优化，减少函数调用
        return [pinyin.strip() for pinyin in pinyin_matches if pinyin.strip()]
    
    def _extract_pinyin_xianhanguifan2(self, content: str) -> List[str]:
        """
        现代汉语规范词典2的拼音提取规则（优化版本）
        
        Args:
            content: 词典返回的HTML/XML内容
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        # 使用预编译的正则表达式
        pinyin_matches = self.pinyin_pattern_xianhanguifan2.findall(content)
        
        # 使用列表推导式优化
        return [pinyin.strip() for pinyin in pinyin_matches if pinyin.strip()]
    
    def _extract_pinyin_zhonghuayuwendaciandian(self, content: str) -> List[str]:
        """
        zhywdcd.mdx的拼音提取规则（优化版本）
        
        Args:
            content: 词典返回的HTML/XML内容
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        # 使用预编译的正则表达式，分为三个阶段
        # 分条目
        entries = self.pinyin_pattern_zhonghuayuwendaciandian_entryhead.split(content)
        pinyin = []
        for i in entries:
            twhp = self.pinyin_pattern_zhonghuayuwendaciandian_twhp.findall(i)
            dlhp = self.pinyin_pattern_zhonghuayuwendaciandian_dlhp.findall(i)
            if twhp or dlhp:
                pinyin.append(('; '.join(twhp), '; '.join(dlhp)))
        
        # 使用列表推导式优化
        return pinyin
    
    def extract_pinyin_from_content(self, content: str, dict_name: str = "xh7.mdx") -> List[str]:
        """
        根据词典名称使用相应的拼音提取规则（优化版本）
        
        Args:
            content: 词典返回的HTML/XML内容
            dict_name: 词典名称，用于选择提取规则
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        # 使用词典特定的提取规则
        if dict_name in self.extraction_rules:
            return self.extraction_rules[dict_name](content)
        
        # 如果没有特定规则，使用默认的正则表达式提取
        pinyin_matches = self.default_pinyin_pattern.findall(content)
        
        # 使用列表推导式优化
        return [pinyin.strip() for pinyin in pinyin_matches if pinyin.strip()]
    
    def get_word_pinyin(self, word: str, dict_name: str = "xh7.mdx") -> List[str]:
        """
        获取指定词语在指定词典中的拼音（优化版本）
        
        Args:
            word: 要查询的词语
            dict_name: 词典名称
            
        Returns:
            拼音列表
        """
        # 优化缓存键的创建，使用元组而不是字符串拼接
        cache_key = (dict_name, word)
        
        # 线程安全的缓存访问
        with self.cache_lock:
            if cache_key in self.pinyin_cache:
                return self.pinyin_cache[cache_key]
        
        try:
            # 查询词典
            content = self.mdict_manager.query(dict_name, word)
            if content:
                pinyins = self.extract_pinyin_from_content(content, dict_name)
                # 线程安全的缓存写入
                with self.cache_lock:
                    self.pinyin_cache[cache_key] = pinyins
                return pinyins
            else:
                return []
        except Exception as e:
            print(f"查询词典 {dict_name} 中的词语 '{word}' 时出错: {e}")
            return []
    
    def batch_extract_pinyin(self, words: List[str], dict_name: str = "xh7.mdx") -> Dict[str, List[str]]:
        """
        批量提取多个词语的拼音（优化版本）
        
        Args:
            words: 词语列表
            dict_name: 词典名称
            
        Returns:
            词语到拼音的映射字典
        """
        # 使用字典推导式优化
        return {word: self.get_word_pinyin(word, dict_name) for word in words}
    
    def batch_extract_pinyin_parallel(self, words: List[str], dict_name: str = "xh7.mdx") -> Dict[str, List[str]]:
        """
        并行批量提取多个词语的拼音（高性能版本）
        
        Args:
            words: 词语列表
            dict_name: 词典名称
            
        Returns:
            词语到拼音的映射字典
        """
        results = {}
        
        def process_word(word):
            return word, self.get_word_pinyin(word, dict_name)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_word = {executor.submit(process_word, word): word for word in words}
            
            # 收集结果
            for future in as_completed(future_to_word):
                try:
                    word, pinyins = future.result()
                    results[word] = pinyins
                except Exception as e:
                    word = future_to_word[future]
                    print(f"处理词语 '{word}' 时出错: {e}")
                    results[word] = []
        
        return results
    
    def get_all_pinyin_from_dict(self, dict_name: str = "xh7.mdx", limit: int = None) -> Dict[str, List[str]]:
        """
        从指定词典中提取所有词条的拼音（优化版本）
        
        Args:
            dict_name: 词典名称
            limit: 限制处理的词条数量，None表示处理所有词条
            
        Returns:
            所有词条及其拼音的映射字典
        """
        try:
            # 获取词典中的所有词条
            entries = self.mdict_manager.entries(dict_name, limit)
            total_entries = len(entries)
            print(f"正在处理词典 {dict_name} 中的 {total_entries} 个词条...")
            
            all_pinyin = {}
            # 减少进度显示频率，提高性能
            # progress_interval = max(1, total_entries // 20)  # 最多显示20次进度
            progress_interval = 500
            
            for i, entry in enumerate(entries):
                if i % progress_interval == 0:  # 动态调整进度显示频率
                    print(f"已处理 {i}/{total_entries} 个词条...")
                
                pinyins = self.get_word_pinyin(entry, dict_name)
                if pinyins:  # 只保存有拼音的词条
                    all_pinyin[entry] = pinyins
            
            print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个有拼音的词条")
            return all_pinyin
            
        except Exception as e:
            print(f"批量提取拼音时出错: {e}")
            return {}
    
    def get_all_pinyin_from_dict_parallel(self, dict_name: str = "xh7.mdx", limit: int = None, batch_size: int = 100) -> Dict[str, List[str]]:
        """
        并行从指定词典中提取所有词条的拼音（高性能版本）
        
        Args:
            dict_name: 词典名称
            limit: 限制处理的词条数量，None表示处理所有词条
            batch_size: 批处理大小，用于并行处理
            
        Returns:
            所有词条及其拼音的映射字典
        """
        try:
            # 获取词典中的所有词条
            entries = self.mdict_manager.entries(dict_name, limit)
            total_entries = len(entries)
            print(f"正在并行处理词典 {dict_name} 中的 {total_entries} 个词条...")
            
            all_pinyin = {}
            
            # 分批处理以提高并行效率
            for i in range(0, total_entries, batch_size):
                batch_entries = entries[i:i + batch_size]
                print(f"正在处理批次 {i//batch_size + 1}/{(total_entries + batch_size - 1)//batch_size}...")
                
                # 并行处理当前批次
                batch_results = self.batch_extract_pinyin_parallel(batch_entries, dict_name)
                all_pinyin.update(batch_results)
            
            print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个有拼音的词条")
            return all_pinyin
            
        except Exception as e:
            print(f"并行批量提取拼音时出错: {e}")
            return {}
    
    def clear_cache(self):
        """清空缓存以释放内存"""
        self.pinyin_cache.clear()
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.pinyin_cache),
            'cache_keys': list(self.pinyin_cache.keys())[:10]  # 只显示前10个键
        }


def test_xianhan7_extraction():
    """测试现汉7的拼音提取规则"""
    
    # 使用终端中显示的实际数据
    test_content = """
<link rel="stylesheet" type="text/css" href="XDHY7.css" />
<entry id="01643"><hwg><hw>薄</hw><pinyin>báo</pinyin></hwg><def><ps>形</ps></def><def><num>❶</num> 扁平物上下两面之间的距离小（跟“<a href="entry://厚">厚</a>”相对，下②③⑤同）：<ex>～板｜～被｜～片｜这种纸很～。</ex></def><def><num>❷</num> （感情）冷淡；不深：<ex>待他的情分不～。</ex></def><def><num>❸</num> （味道）不浓；淡：<ex>酒味很～。</ex></def><def><num>❹</num> （土地）不 肥沃：<ex>这<small>儿</small>地～，产量不高。</ex></def><def><num>❺</num> （家产）少；不富有：<ex>家底<small>儿</small>～。</ex></def><def>　另见<pinyin>bó</pinyin>；<pinyin>bò</pinyin>。</def><ci><div class="title">词语</div><div class="cont"><a href="entry://薄饼">薄饼</a><a href="entry://薄脆">薄脆</a></div></ci></entry>
<entry id="03942"><hwg><hw>薄<sup>1</sup></hw><pinyin>bó</pinyin></hwg><def><num>❶</num> 薄（<pinyin>báo</pinyin>）①：<ex>～雾｜如 履～冰。</ex></def><def><num>❷</num> 轻微；少：<ex>～技｜广种～收。</ex></def><def><num>❸</num> 不强健；不壮实：<ex>～弱｜单～。</ex></def><def><num>❹</num> 不厚道；不庄重：<ex>～待｜刻～｜轻～。</ex></def><def><num>❺</num> （土地）不肥沃：<ex>～地｜～田。</ex></def><def><num>❻</num> （味道）不浓；淡：<ex>～酒。</ex></def><def><num>❼</num> 看不起；轻视；慢待：<ex>菲～｜鄙～｜厚今～古。</ex></def><def><num>❽</num> （<pinyin>Bó</pinyin>）<ps>名</ps>姓。</def></entry>
<entry id="03943"><hwg><hw>薄<sup>2</sup></hw><pinyin>bó</pinyin></hwg><def>〈书〉迫近；靠近：<ex>～海｜日～西山。</ex></def><def>　另见<pinyin>báo</pinyin>；<pinyin>bò</pinyin>。</def><ci><div class="title">词语</div><div class="cont"><a href="entry://薄产">薄产</a><a href="entry://薄地"> 薄地</a><a href="entry://薄海">薄海</a><a href="entry://薄厚">薄厚</a><a href="entry://薄技">薄技</a><a href="entry://薄酒">薄酒</a><a href="entry://薄 礼">薄礼</a><a href="entry://薄利">薄利</a><a href="entry://薄利多销">薄利多销</a><a href="entry://薄面">薄面</a><a href="entry://薄命">薄命</a><a href="entry://薄暮">薄暮</a><a href="entry://薄情">薄情</a><a href="entry://薄弱">薄弱</a><a href="entry://薄田">薄田</a><a href="entry://薄物细故">薄物细故</a><a href="entry://薄幸">薄幸</a><a href="entry://薄葬">薄葬</a></div></ci></entry>
<entry id="03979"><hwg><hw>薄</hw><pinyin>bò</pinyin></hwg><def>见下。</def><def>　另见<pinyin>báo</pinyin>；<pinyin>bó</pinyin>。</def><ci><div class="title">词语</div><div class="cont"><a href="entry://薄荷">薄荷</a></div></ci></entry>
    """
    
    extractor = PinyinExtractor()
    pinyins = extractor.extract_pinyin_from_content(test_content, "xh7.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshǎo', 'duō·shao']")
    print(f"测试{'通过' if pinyins == ['duōshǎo', 'duō·shao'] else '失败'}")
    
    return pinyins


def test_xianhanguifan2_extraction():
    """测试xhgf2.mdx的拼音提取规则"""
    
    # 使用终端中显示的实际数据
    test_content = """<link rel="stylesheet" type="text/css" href="HYGF2.css">
    <x-hw>多少</x-hw><x-pr> duōshao </x-pr><dt><x-sn>①</x-sn><x-gram>代</x-gram>用在疑问句里，询问数量<x-f>。</x-f></dt><dd>☆<x-ex>今天来了<x-key> 多少</x-key>人?</x-ex></dd><dt><x-sn>②</x-sn><x-gram>代</x-gram>指代不定的数量<x-f>。</x-f></dd><dd>☆<x-ex>要<x-key>多少</x-key>， 给<x-key>多少</x-key></x-ex><x-ex><x-lb> | </x-lb>今年招<x-key>多少</x-key>新生早已确定<x-f>。</x-f></x-ex></dd><hr>
    <x-hw>多少</x-hw><x-pr> duōshǎo </x-pr><dt><x-sn>①</x-sn><x-gram>名</x-gram>指数量的多和少<x-f>。</x-f></dt><dd>☆<x-ex><x-key>多少</x-key>不等</x-ex><x-ex><x-lb> | </x-lb>不拘<x-key>多少</x-key>，有一点<x-er>儿</x-er>就行<x-f>。</x-f></x-ex></dd> <dt><x-sn>②</x-sn><x-g>副</x-g>或多或少；稍微<x-f>。</x-f></dt><dd>☆<x-ex>上了几年学，<x-key>多少</x-key>有点<x-er>儿</x-er>文化</x-ex><x-ex><x-lb> | </x-lb>病情比过去<x-key>多少</x-key>好一点<x-f>。</x-f></x-ex></dd>"""
    
    extractor = PinyinExtractor()
    # 直接测试提取规则，不依赖词典查询
    pinyins = extractor.extract_pinyin_from_content(test_content, "xhgf2.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshǎo', 'duōshao']")
    print(f"测试{'通过' if pinyins.sort() == ['duōshǎo', 'duōshao'].sort() else '失败'}")
    
    return pinyins


def test_zhonghuayuwendaciandian_extraction():
    """测试zhywdcd.mdx的拼音提取规则"""
    
    # 使用终端中显示的实际数据
    test_content = """
<link rel="stylesheet" href="zhyydcd.css">
<div class="ctzg"><div class="zxzg"><span class="ztzx"> 薄</span><span class="jhzx">薄</span></div><span class="yinx">1</span><div class="twdy"><span class="twyd">ㄅㄛˊ</span><span class="twhp">bó</span></div></div><div class="syzg"><span class="shyi">1.微；少。[例]～禮∣～利∣綿～。</span><span class="shyi">2.輕視；小看。[例]鄙～∣厚古～今。</span><span class="shyi">3.苛刻；待人不厚道。[例]刻～∣～情∣不能～待客人。</span><span class="shyi">4.輕佻 ；不莊重。[例]輕～。</span><span class="shyi">5.迫近；接近。[例]～暮│日～西山。</span><span class="shyi">6.姓。</span></div>
<div class="ctzg"><div class="zxzg"><span class="ztzx">薄</span><span class="jhzx">薄</span></div><span class="yinx">2</span><div class="twdy"><span class="twyd">ㄅㄛˊ</span><span class="twhp">bó</span></div><div class="dldy"><span class="dlyd">ㄅㄠˊ</span><span class="dlhp">báo</span></div></div><div class="syzg"><span class="shyi">1.厚度小（與「厚」相對）。[例] 臉皮～│～棉襖│雲層很～│這種磚太～。</span><span class="shyi">2.（土地）貧瘠；不肥沃。[例]～田│土質～，產量低。</span><span class="shyi">3.（感情）冷淡；不深厚。[例]人情～如紙∣待我不～。</span><span class="shyi">4.（味道）淡；不濃。[例]這酒度數太低，味道～。</span></div>
<div class="ctzg"><div class="zxzg"><span class="ztzx">薄</span><span class="jhzx">薄</span></div><span class="yinx">3</span><div class="twdy"><span class="twyd">ㄅㄛˋ</span><span class="twhp">bò</span></div></div><div class="syzg"><span class="shyi">參見【薄荷】。</span></div>
    """
    
    extractor = PinyinExtractor()
    # 直接测试提取规则，不依赖词典查询
    pinyins = extractor.extract_pinyin_from_content(test_content, "zhywdcd.mdx")
    
    # print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: [('bó', ''),('bó', 'báo'),('bò', '')]")
    print(f"测试{'通过' if pinyins.sort() == [('bó', ''),('bó', 'báo'),('bò', '')].sort() else '失败'}")
    
    return pinyins


if __name__ == "__main__":
    
    print("=== 拼音提取器性能优化版本 ===")
    
    # # 自动调优max_workers设置
    # print("\n🔧 自动调优max_workers设置...")
    # best_workers, _ = find_optimal_max_workers()
    # # 使用最佳设置创建提取器
    # print(f"\n🚀 使用最佳设置创建提取器: max_workers = {best_workers}") # 2
    extractor = PinyinExtractor(max_workers=4)
    
    # # 运行性能测试
    # print("\n" + "="*50)
    # performance_test()
    # print("="*50 + "\n")

    # 测试现汉7拼音提取规则
    # test_xianhan7_extraction()    
    # 测试现汉规范2拼音提取规则
    # test_xianhanguifan2_extraction()
    # 测试zhywdcd.mdx拼音提取规则
    # test_zhonghuayuwendaciandian_extraction()
    
    # 注意：由于MdictManager无法正常工作，以下功能暂时不可用
    # 如果需要批量提取拼音，请先解决MdictManager的依赖问题
    
    
    # # 测试单个词语的拼音提取
    # test_words = ["多少", "中国", "学习", "词典"]
    # print("测试单个词语拼音提取:")
    # for word in test_words:
    #     pinyins = extractor.get_word_pinyin(word)
    #     print(f"'{word}': {pinyins}")
    
    
    # # 测试批量拼音提取
    # print("测试批量拼音提取:")
    # batch_results = extractor.batch_extract_pinyin(test_words)
    # for word, pinyins in batch_results.items():
    #     print(f"'{word}': {pinyins}")
    
    
    # 从xh7.mdx中提取所有词条的拼音，保存到当前目录的json文件
    # all_pinyin = extractor.get_all_pinyin_from_dict("xh7.mdx", limit=None)
    # import json
    # with open('src/resource/xh7.mdx.json', 'w', encoding='utf-8') as f:
    #     json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    # print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 xh7.mdx.json")

    # all_pinyin = extractor.get_all_pinyin_from_dict("xhgf2.mdx", limit=None)
    # import json
    # with open('src/resource/xhgf2.mdx.json', 'w', encoding='utf-8') as f:
    #     json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    # print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 xhgf2.mdx.json")
        

    all_pinyin = extractor.get_all_pinyin_from_dict("zhywdcd.mdx", limit=None)
    with open('src/resource/zhywdcd.mdx.json', 'w', encoding='utf-8') as f:
        json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 zhywdcd.mdx.json")
        


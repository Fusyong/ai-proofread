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
            "现汉7.mdx": self._extract_pinyin_xianhan7,
            "现汉规范2.mdx": self._extract_pinyin_xianhanguifan2,
            "中華語文大辭典.mdx": self._extract_pinyin_zhonghuayuwendaciandian,
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
        self.entry_pattern = re.compile(r'<entry[^>]*>.*?</entry>', re.DOTALL)
        self.pinyin_pattern_xianhan7 = re.compile(r'<pinyin>([^<]+)</pinyin>')
        
        # 现汉规范2的正则表达式
        self.pinyin_pattern_xianhanguifan2 = re.compile(r'<x-pr>\s*([^<]+)\s*</x-pr>')
        
        # 中華語文大辭典的正则表达式
        self.pinyin_pattern_zhonghuayuwendaciandian = re.compile(r'<span class="twhp">([^<]+)</span>')
        
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
        中華語文大辭典.mdx的拼音提取规则（优化版本）
        
        Args:
            content: 词典返回的HTML/XML内容
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        # 使用预编译的正则表达式
        pinyin_matches = self.pinyin_pattern_zhonghuayuwendaciandian.findall(content)
        
        # 使用列表推导式优化
        return [pinyin.strip() for pinyin in pinyin_matches if pinyin.strip()]
    
    def extract_pinyin_from_content(self, content: str, dict_name: str = "现汉7.mdx") -> List[str]:
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
    
    def get_word_pinyin(self, word: str, dict_name: str = "现汉7.mdx") -> List[str]:
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
    
    def batch_extract_pinyin(self, words: List[str], dict_name: str = "现汉7.mdx") -> Dict[str, List[str]]:
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
    
    def batch_extract_pinyin_parallel(self, words: List[str], dict_name: str = "现汉7.mdx") -> Dict[str, List[str]]:
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
    
    def get_all_pinyin_from_dict(self, dict_name: str = "现汉7.mdx", limit: int = None) -> Dict[str, List[str]]:
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
    
    def get_all_pinyin_from_dict_parallel(self, dict_name: str = "现汉7.mdx", limit: int = None, batch_size: int = 100) -> Dict[str, List[str]]:
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
    <entry id="13250"><hwg><hw>多少</hw><pinyin>duōshǎo</pinyin></hwg><def><num>❶</num> <ps>名</ps>指数量的大小：<ex>～不等，长短不齐。</ex></def><def><num>❷</num> <ps>副</ps>或多或少：<ex>这句话～有点<small>儿</small>道理。</ex></def><def><num>❸</num> <ps>副</ps>稍微：<ex>一立秋，天气～有点<small>儿</small>凉意了。</ex></def></entry>
    <entry id="13251"><hwg><hw>多少</hw><pinyin>duō·shao</pinyin></hwg><def><ps>代</ps>疑问代词。</def><def><num>❶</num> 问数量：<ex>这个村子有～人家？｜今年收了～粮食？</ex></def><def><num>❷</num> 表示不定的数量：<ex>我知道～说～｜有～人，准备～工具。</ex></def></entry>"""
    
    extractor = PinyinExtractor()
    pinyins = extractor.extract_pinyin_from_content(test_content, "现汉7.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshǎo', 'duō·shao']")
    print(f"测试{'通过' if pinyins == ['duōshǎo', 'duō·shao'] else '失败'}")
    
    return pinyins


def test_xianhanguifan2_extraction():
    """测试现汉规范2.mdx的拼音提取规则"""
    
    # 使用终端中显示的实际数据
    test_content = """<link rel="stylesheet" type="text/css" href="HYGF2.css">
    <x-hw>多少</x-hw><x-pr> duōshao </x-pr><dt><x-sn>①</x-sn><x-gram>代</x-gram>用在疑问句里，询问数量<x-f>。</x-f></dt><dd>☆<x-ex>今天来了<x-key> 多少</x-key>人?</x-ex></dd><dt><x-sn>②</x-sn><x-gram>代</x-gram>指代不定的数量<x-f>。</x-f></dd><dd>☆<x-ex>要<x-key>多少</x-key>， 给<x-key>多少</x-key></x-ex><x-ex><x-lb> | </x-lb>今年招<x-key>多少</x-key>新生早已确定<x-f>。</x-f></x-ex></dd><hr>
    <x-hw>多少</x-hw><x-pr> duōshǎo </x-pr><dt><x-sn>①</x-sn><x-gram>名</x-gram>指数量的多和少<x-f>。</x-f></dt><dd>☆<x-ex><x-key>多少</x-key>不等</x-ex><x-ex><x-lb> | </x-lb>不拘<x-key>多少</x-key>，有一点<x-er>儿</x-er>就行<x-f>。</x-f></x-ex></dd> <dt><x-sn>②</x-sn><x-g>副</x-g>或多或少；稍微<x-f>。</x-f></dt><dd>☆<x-ex>上了几年学，<x-key>多少</x-key>有点<x-er>儿</x-er>文化</x-ex><x-ex><x-lb> | </x-lb>病情比过去<x-key>多少</x-key>好一点<x-f>。</x-f></x-ex></dd>"""
    
    extractor = PinyinExtractor()
    # 直接测试提取规则，不依赖词典查询
    pinyins = extractor.extract_pinyin_from_content(test_content, "现汉规范2.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshǎo', 'duōshao']")
    print(f"测试{'通过' if pinyins.sort() == ['duōshǎo', 'duōshao'].sort() else '失败'}")
    
    return pinyins


def test_zhonghuayuwendaciandian_extraction():
    """测试中華語文大辭典.mdx的拼音提取规则"""
    
    # 使用终端中显示的实际数据
    test_content = """<link rel="stylesheet" href="zhyydcd.css">
    <div class="ctzg"><div class="zxzg"><span class="ztzx">多少</span></div><span class="yinx">1</span><div class="twdy"><span class="twyd">ㄉㄨㄛ　ㄕㄠˇ</span><span class="twhp">duōshǎo</span></div></div><div class="syzg"><span class="shyi">1.數量的多和少。[例]社團的人數～不等。</span><span class="shyi">2.程度上或多或少。[例]讀過中文系，～會寫點文言文。</span></div>
    <div class="ctzg"><div class="zxzg"><span class="ztzx">多少</span></div><span class="yinx">2</span><div class="twdy"><span class="twyd">ㄉㄨㄛ　˙ㄕㄠ</span><span class="twhp">duōshɑo</span></div></div><div class="syzg"><span class="shyi">1.詢問數量。[例]你們買了～書？</span><span class="shyi">2.表示不確定的數量。[例]你 給～我就要～｜有～證據就說～話。</span></div>"""
    
    extractor = PinyinExtractor()
    # 直接测试提取规则，不依赖词典查询
    pinyins = extractor.extract_pinyin_from_content(test_content, "中華語文大辭典.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshɑo', 'duōshǎo']")
    print(f"测试{'通过' if pinyins.sort() == ['duōshɑo', 'duōshǎo'].sort() else '失败'}")
    
    return pinyins


def performance_test():
    """性能测试：比较串行和并行处理的性能"""
    import time
    
    # 创建测试数据
    test_words = [f"测试词语{i}" for i in range(100)]
    
    # 创建提取器
    extractor = PinyinExtractor(max_workers=4)
    
    print("=== 性能测试开始 ===")
    
    # 测试串行处理
    start_time = time.time()
    serial_results = extractor.batch_extract_pinyin(test_words, "中華語文大辭典.mdx")
    serial_time = time.time() - start_time
    
    print(f"串行处理 {len(test_words)} 个词语耗时: {serial_time:.4f} 秒")
    
    # 测试并行处理
    start_time = time.time()
    parallel_results = extractor.batch_extract_pinyin_parallel(test_words, "中華語文大辭典.mdx")
    parallel_time = time.time() - start_time
    
    print(f"并行处理 {len(test_words)} 个词语耗时: {parallel_time:.4f} 秒")
    
    # 计算性能提升
    if serial_time > 0:
        speedup = serial_time / parallel_time
        print(f"性能提升: {speedup:.2f}x")
    
    # 验证结果一致性
    if serial_results == parallel_results:
        print("✓ 串行和并行处理结果一致")
    else:
        print("✗ 串行和并行处理结果不一致")
    
    print("=== 性能测试结束 ===")
    
    return serial_time, parallel_time


def find_optimal_max_workers(test_words=None, max_test_workers=8):
    """找到最佳的max_workers设置"""
    import time
    import os
    
    if test_words is None:
        test_words = [f"测试词语{i}" for i in range(50)]
    
    print("=== 寻找最佳max_workers设置 ===")
    print(f"CPU核心数: {os.cpu_count()}")
    print(f"测试词语数量: {len(test_words)}")
    
    results = {}
    
    # 测试串行处理
    extractor_serial = PinyinExtractor(max_workers=1)
    start_time = time.time()
    extractor_serial.batch_extract_pinyin(test_words, "中華語文大辭典.mdx")
    serial_time = time.time() - start_time
    results[1] = serial_time
    print(f"串行处理 (workers=1): {serial_time:.4f} 秒")
    
    # 测试不同worker数量的并行处理
    for workers in range(2, max_test_workers + 1):
        try:
            extractor = PinyinExtractor(max_workers=workers)
            start_time = time.time()
            extractor.batch_extract_pinyin_parallel(test_words, "中華語文大辭典.mdx")
            parallel_time = time.time() - start_time
            results[workers] = parallel_time
            
            speedup = serial_time / parallel_time
            print(f"并行处理 (workers={workers}): {parallel_time:.4f} 秒, 性能提升: {speedup:.2f}x")
            
        except Exception as e:
            print(f"并行处理 (workers={workers}) 失败: {e}")
            results[workers] = float('inf')
    
    # 找到最佳设置
    best_workers = min(results.items(), key=lambda x: x[1])
    print(f"\n🎯 最佳设置: max_workers = {best_workers[0]}")
    print(f"最佳性能: {best_workers[1]:.4f} 秒")
    
    if best_workers[0] > 1:
        speedup = serial_time / best_workers[1]
        print(f"相比串行处理提升: {speedup:.2f}x")
    
    print("=== 测试结束 ===")
    
    return best_workers[0], results





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
    # 测试中華語文大辭典.mdx拼音提取规则
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
    
    
    # 从现汉7.mdx中提取所有词条的拼音，保存到当前目录的json文件
    # all_pinyin = extractor.get_all_pinyin_from_dict("现汉7.mdx", limit=None)
    # import json
    # with open('src/resource/现汉7.mdx.json', 'w', encoding='utf-8') as f:
    #     json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    # print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 现汉7.mdx.json")

    # all_pinyin = extractor.get_all_pinyin_from_dict("现汉规范2.mdx", limit=None)
    # import json
    # with open('src/resource/现汉规范2.mdx.json', 'w', encoding='utf-8') as f:
    #     json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    # print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 现汉规范2.mdx.json")
        

    all_pinyin = extractor.get_all_pinyin_from_dict("中華語文大辭典.mdx", limit=None)
    with open('src/resource/中華語文大辭典.mdx.json', 'w', encoding='utf-8') as f:
        json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 中華語文大辭典.mdx.json")
        


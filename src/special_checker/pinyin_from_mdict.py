"""
从mdict词典中提取词条拼音信息
"""
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

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
    
    def __init__(self, mdict_manager=None):
        """初始化拼音提取器"""
        if mdict_manager is None and MdictManager is not None:
            self.mdict_manager = MdictManager()
        else:
            self.mdict_manager = mdict_manager
        self.pinyin_cache = {}  # 缓存已提取的拼音
        
        # 为不同词典定义拼音提取规则
        self.extraction_rules = {
            "现汉7.mdx": self._extract_pinyin_xianhan7,
            # 可以在这里添加其他词典的规则
            # "其他词典.mdx": self._extract_pinyin_other_dict,
        }
    
    def _extract_pinyin_xianhan7(self, content: str) -> List[str]:
        """
        现代汉语词典7的拼音提取规则：
        每个entry id标签后的第一个pinyin标签中的内容（忽略其余pinyin）
        
        Args:
            content: 词典返回的HTML/XML内容
            
        Returns:
            拼音列表
        """
        if not content:
            return []
        
        pinyins = []
        
        # 使用正则表达式找到所有的entry标签
        entry_pattern = r'<entry[^>]*>.*?</entry>'
        entries = re.findall(entry_pattern, content, re.DOTALL)
        
        for entry in entries:
            # 在每个entry中查找第一个pinyin标签
            pinyin_match = re.search(r'<pinyin>([^<]+)</pinyin>', entry)
            if pinyin_match:
                pinyin = pinyin_match.group(1).strip()
                if pinyin:
                    pinyins.append(pinyin)
        
        return pinyins
    
    def extract_pinyin_from_content(self, content: str, dict_name: str = "现汉7.mdx") -> List[str]:
        """
        根据词典名称使用相应的拼音提取规则
        
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
        pinyin_pattern = r'<pinyin>([^<]+)</pinyin>'
        pinyins = re.findall(pinyin_pattern, content)
        
        # 清理拼音数据，去除多余的空格和特殊字符
        cleaned_pinyins = []
        for pinyin in pinyins:
            cleaned = pinyin.strip()
            if cleaned:
                cleaned_pinyins.append(cleaned)
        
        return cleaned_pinyins
    
    def get_word_pinyin(self, word: str, dict_name: str = "现汉7.mdx") -> List[str]:
        """
        获取指定词语在指定词典中的拼音
        
        Args:
            word: 要查询的词语
            dict_name: 词典名称
            
        Returns:
            拼音列表
        """
        # 检查缓存
        cache_key = f"{dict_name}:{word}"
        if cache_key in self.pinyin_cache:
            return self.pinyin_cache[cache_key]
        
        try:
            # 查询词典
            content = self.mdict_manager.query(dict_name, word)
            if content:
                pinyins = self.extract_pinyin_from_content(content, dict_name)
                # 缓存结果
                self.pinyin_cache[cache_key] = pinyins
                return pinyins
            else:
                return []
        except Exception as e:
            print(f"查询词典 {dict_name} 中的词语 '{word}' 时出错: {e}")
            return []
    
    def batch_extract_pinyin(self, words: List[str], dict_name: str = "现汉7.mdx") -> Dict[str, List[str]]:
        """
        批量提取多个词语的拼音
        
        Args:
            words: 词语列表
            dict_name: 词典名称
            
        Returns:
            词语到拼音的映射字典
        """
        results = {}
        for word in words:
            pinyins = self.get_word_pinyin(word, dict_name)
            results[word] = pinyins
        return results
    
    def get_all_pinyin_from_dict(self, dict_name: str = "现汉7.mdx", limit: int = None) -> Dict[str, List[str]]:
        """
        从指定词典中提取所有词条的拼音
        
        Args:
            dict_name: 词典名称
            limit: 限制处理的词条数量，None表示处理所有词条
            
        Returns:
            所有词条及其拼音的映射字典
        """
        try:
            # 获取词典中的所有词条
            entries = self.mdict_manager.entries(dict_name, limit)
            print(f"正在处理词典 {dict_name} 中的 {len(entries)} 个词条...")
            
            all_pinyin = {}
            for i, entry in enumerate(entries):
                if i % 100 == 0:  # 每处理100个词条显示进度
                    print(f"已处理 {i}/{len(entries)} 个词条...")
                
                pinyins = self.get_word_pinyin(entry, dict_name)
                if pinyins:  # 只保存有拼音的词条
                    all_pinyin[entry] = pinyins
            
            print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个有拼音的词条")
            return all_pinyin
            
        except Exception as e:
            print(f"批量提取拼音时出错: {e}")
            return {}


def test_xianhan7_extraction():
    """测试现汉7的拼音提取规则"""
    print("测试现汉7拼音提取规则...")
    
    # 使用终端中显示的实际数据
    test_content = """<entry id="13250"><hwg><hw>多少</hw><pinyin>duōshǎo</pinyin></hwg><def><num>❶</num> <ps>名</ps>指数量的大小：<ex>～不等，长短不齐。</ex></def><def><num>❷</num> <ps>副</ps>或多或少：<ex>这句话～有点<small>儿</small>道理。</ex></def><def><num>❸</num> <ps>副</ps>稍微：<ex>一立秋，天气～有点<small>儿</small>凉意了。</ex></def></entry><entry id="13251"><hwg><hw>多少</hw><pinyin>duō·shao</pinyin></hwg><def><ps>代</ps>疑问代词。</def><def><num>❶</num> 问数量：<ex>这个村子有～人家？｜今年收了～粮食？</ex></def><def><num>❷</num> 表示不定的数量：<ex>我知道～说～｜有～人，准备～工具。</ex></def></entry>"""
    
    extractor = PinyinExtractor()
    pinyins = extractor.extract_pinyin_from_content(test_content, "现汉7.mdx")
    
    print(f"测试内容: {test_content[:100]}...")
    print(f"提取的拼音: {pinyins}")
    print(f"期望结果: ['duōshǎo', 'duō·shao']")
    print(f"测试{'通过' if pinyins == ['duōshǎo', 'duō·shao'] else '失败'}")
    
    return pinyins



if __name__ == "__main__":
    
    # 测试现汉7拼音提取规则
    # test_xianhan7_extraction()
    
    # 创建拼音提取器
    extractor = PinyinExtractor()
    
    
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
    all_pinyin = extractor.get_all_pinyin_from_dict("现汉7.mdx", limit=None)
    import json
    with open('src/resource/现汉7.mdx.json', 'w', encoding='utf-8') as f:
        json.dump(all_pinyin, f, ensure_ascii=False, indent=2)
    print(f"拼音提取完成，共提取了 {len(all_pinyin)} 个词条的拼音，已保存到 现汉7.mdx.json")
        


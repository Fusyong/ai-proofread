"""
基于词表、模式、N-gram模型和机器学习的轻量级文本检查器
"""
import os
import zlib
import re
import sqlite3
import time
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict
import jieba
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from mdict_utils.reader import MDX
from mdict_utils import unpack_to_db

@dataclass
class CheckResult:
    """
    检查结果类
    """
    error_type: str
    location: tuple[int, int]
    original_text: str
    suggestion: str
    confidence: float

def is_chinese_character(char: str) -> bool:
    """判断是否是中文字符 TODO 有待于扩展字符集

    """
    return '\u4e00' <= char <= '\u9fff'

def check_to_general_standard_kanji_list(text: str) -> List[CheckResult]:
    """通用规范汉字(GSK)表检查

    Args:
        text: 要检查的文本

    Returns:
        List[CheckResult]: 检查结果列表，包含发现的非规范字及其建议
    """

    gsk_list_path = "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表（维基百科）.csv"
    gsk_to_traditional_kanji_list_path = "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表繁简对照表-增强（2025-03-04）.csv"
    gsk_to_traditional_kanji_list_notes_path = "D:/语文出版社/语文社工具书/通用规范汉字表/通用规范汉字表规范字与繁体字、异体字对照表注释.md"

    gsk_data_path = "src/gsk_data.json"

    # 预编译正则表达式
    pinzi_pattern = re.compile(r'〖([^〗]+)〗(\d*)')
    variant_pattern = re.compile(r'(\D)(\d*)')
    ignore_pattern = re.compile(r"""[0-9a-zA-Z，。！？；：“”‘’（）《》,.!?;:"'~\s\(\)\[\]]+""")

    # 列表和映射字典
    gsk_list = []
    simplified_to_traditional = {}  # 简繁映射
    simplified_to_variants = {}    # 简异映射
    traditional_to_simplified = {} # 繁简映射
    variant_to_simplified = {}     # 异简映射
    notes = {}         # 注释号码
    notes_content = []# 注释表正文

    # 检查gsk_data.json是否存在
    if not os.path.exists(gsk_data_path):

        last_simplified = None
        # 读取规范字表
        with open(gsk_list_path, 'r', encoding='utf-8') as f:
            # 跳过标题行
            next(f)
            for line in f:
                parts = line.strip().split(',')
                gsk_list.append(parts[1])

        # 读取注释表
        with open(gsk_to_traditional_kanji_list_notes_path, 'r', encoding='utf-8') as f:
            for line in f:
                notes_content.append(line)

        # 读取并解析繁简异对照表
        with open(gsk_to_traditional_kanji_list_path, 'r', encoding='utf-8') as f:
            # 跳过标题行
            next(f)
            for line in f:
                parts = line.strip().split(',')
                # 获取规范字（简体字）
                simplified = parts[2].strip()
                if not simplified:  # 没有规范字的行表示跟上一行的规范字相同从而省略
                    simplified = last_simplified
                last_simplified = simplified

                # 获取繁体字（去掉括号）和注释号码
                traditional = parts[3].strip()
                if not traditional or traditional == '~': # 空白和'~'表示繁体字与简体字相同
                    traditional = simplified
                else:
                    traditional = traditional.strip('()')
                # 抽取注释号码
                note_match = re.search(r'(\d+)$', str(traditional))
                note = note_match.group(1) if note_match else None
                traditional = str(traditional).rstrip('0123456789')

                # 建立映射，可能一对多
                simplified_to_traditional.setdefault(simplified, []).append(traditional)
                traditional_to_simplified.setdefault(traditional, []).append(simplified)
                if note:
                    notes[traditional] = note

                # 获取异体字，去掉括号，保留注释号码，把拼字作为一个异体字，如`[靭11靱〖⿰韋刄〗12]`
                variants = parts[4].strip()
                if variants:
                    # 移除括号
                    variants = variants.strip('[]')
                    # 查找拼字及其注释号码
                    pinzi_matches = pinzi_pattern.findall(variants)
                    for pinzi, note in pinzi_matches:
                        # 将拼字作为异体字处理
                        simplified_to_variants.setdefault(simplified, []).append(pinzi)
                        variant_to_simplified.setdefault(pinzi, []).append(simplified)
                        if note:
                            notes[pinzi] = note

                    # 移除拼字部分，处理剩余异体字
                    variants = re.sub(pinzi_pattern, '', variants)

                    # 处理多个异体字及其注释号码
                    matches = variant_pattern.findall(variants)
                    for variant, note in matches:
                        if variant:
                            simplified_to_variants.setdefault(simplified, []).append(variant)
                            variant_to_simplified.setdefault(variant, []).append(simplified)
                            if note:
                                notes[variant] = note
        # 保存映射字典以便检查
        with open(gsk_data_path, 'w', encoding='utf-8') as f:
            json.dump({'simplified_to_traditional': simplified_to_traditional,
                       'traditional_to_simplified': traditional_to_simplified,
                       'simplified_to_variants': simplified_to_variants,
                       'variant_to_simplified': variant_to_simplified,
                       'gsk_list': gsk_list,
                       'notes': notes,
                       'notes_content': notes_content
                       },
                      f,
                      ensure_ascii=False)
    else:
        with open(gsk_data_path, 'r', encoding='utf-8') as f:
            gsk_data = json.load(f)
            simplified_to_traditional = gsk_data['simplified_to_traditional']
            traditional_to_simplified = gsk_data['traditional_to_simplified']
            simplified_to_variants = gsk_data['simplified_to_variants']
            variant_to_simplified = gsk_data['variant_to_simplified']
            gsk_list = gsk_data['gsk_list']
            notes = gsk_data['notes']
            notes_content = gsk_data['notes_content']

    # 存储检查结果
    results = []
    # 检查文本中的每个字符
    for i, char in enumerate(text):
        # 忽略指定的字符集（数字、字母、标点符号、空白字符等）
        if ignore_pattern.match(char):
            continue

        # 是通用规范汉字表附录提及的繁字体或异体字
        is_in_gsk_appendix = False

        # 检查是否是繁体字
        if char in traditional_to_simplified and traditional_to_simplified[char] != [char]:
            is_in_gsk_appendix = True
            note = notes.get(char, '')
            suggestion = ''.join(traditional_to_simplified[char])  # 取对应的规范字
            if note and int(note) <= len(notes_content):
                note_text = notes_content[int(note)-1].strip()
            else:
                note_text = ''
            results.append(CheckResult(
                error_type='traditional_character',
                location=(i, i + 1),
                original_text=char,
                suggestion=f"{suggestion}{f'({note_text})' if note_text else ''}",
                confidence=1
            ))

        # 检查是否是异体字
        if char in variant_to_simplified and variant_to_simplified[char] != [char]:
            is_in_gsk_appendix = True
            note = notes.get(char, '')
            suggestion = ''.join(variant_to_simplified[char])  # 取对应的规范字
            if note and int(note) <= len(notes_content):
                note_text = notes_content[int(note)-1].strip()
            else:
                note_text = ''
            results.append(CheckResult(
                error_type='variant_character',
                location=(i, i + 1),
                original_text=char,
                suggestion=f"{suggestion}{f'({note_text})' if note_text else ''}",
                confidence=1
            ))

        # 检查是否是规范字
        if not is_in_gsk_appendix and char not in gsk_list:
            results.append(CheckResult(
                error_type='not_general_standard_kanji',
                location=(i, i + 1),
                original_text=char,
                suggestion="不在通用规范汉字表及其附录中",
                confidence=1
            ))

    return results

class NGramModel:
    """
    N-gram 模型类
    """
    def __init__(self, n: int = 2):
        self.n = n
        self.ngram_counts = defaultdict(int)
        self.total_ngrams = 0
        self.bigram_data = self._load_bigram_data()

    def _load_bigram_data(self) -> Dict[str, float]:
        """从 bigram_full.txt 加载数据"""
        bigram_data = defaultdict(float)
        try:
            with open('data/bigram_full.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        bigram, freq = parts[0], float(parts[1])
                        # 将 D 和 L 转换为正则表达式模式
                        pattern = bigram.replace('D', r'\d').replace('L', r'[a-zA-Z]')
                        bigram_data[pattern] = freq
        except FileNotFoundError:
            print("Warning: bigram_full.txt not found, using default data")
        return bigram_data

    def train(self, corpus: List[str]):
        """训练 N-gram 模型"""
        for text in corpus:
            words = list(jieba.cut(text))
            for i in range(len(words) - self.n + 1):
                ngram = tuple(words[i:i+self.n])
                self.ngram_counts[ngram] += 1
                self.total_ngrams += 1

    def get_probability(self, ngram: Tuple[str, ...]) -> float:
        """获取 N-gram 的概率"""
        # 首先检查预加载的 bigram 数据
        if self.n == 2 and len(ngram) == 2:
            # 将词语转换为对应的模式
            pattern = []
            for word in ngram:
                if word.isdigit():
                    pattern.append(r'\d')
                elif word.isalpha() and not ('\u4e00' <= word <= '\u9fff'):
                    pattern.append(r'[a-zA-Z]')
                else:
                    pattern.append(re.escape(word))
            pattern = ' '.join(pattern)

            # 检查是否匹配任何预定义的模式
            for bigram_pattern, freq in self.bigram_data.items():
                if re.match(bigram_pattern, pattern):
                    return freq

        # 如果预加载数据中没有，使用训练数据
        count = self.ngram_counts[ngram]
        return count / self.total_ngrams if self.total_ngrams > 0 else 0.0

    def get_suggestions(self, words: List[str], threshold: float = 0.0001) -> List[Tuple[int, str, float]]:
        """获取可能的错误位置和建议"""
        suggestions = []
        for i in range(len(words) - self.n + 1):
            ngram = tuple(words[i:i+self.n])
            prob = self.get_probability(ngram)
            if prob < threshold:
                # 如果概率太低，可能是错误
                suggestions.append((i, ' '.join(ngram), prob))
        return suggestions

class FeatureExtractor(BaseEstimator, TransformerMixin):
    """
    特征提取器类
    """
    def __init__(self):
        self.feature_functions = [
            self._get_char_type_features,
            self._get_punctuation_features,
            self._get_length_features,
            self._get_digit_features
        ]

    def _get_char_type_features(self, text: str) -> Dict[str, float]:
        """获取字符类型特征"""
        features = {
            'chinese_chars': sum(1 for c in text if '\u4e00' <= c <= '\u9fff'),
            'english_chars': sum(1 for c in text if c.isalpha() and not ('\u4e00' <= c <= '\u9fff')),
            'digit_chars': sum(1 for c in text if c.isdigit()),
            'space_chars': sum(1 for c in text if c.isspace())
        }
        total = sum(features.values())
        return {k: float(v/total) if total > 0 else 0.0 for k, v in features.items()}

    def _get_punctuation_features(self, text: str) -> Dict[str, float]:
        """获取标点符号特征"""
        chinese_punct = sum(1 for c in text if c in '，。！？；：""''（）【】《》')
        english_punct = sum(1 for c in text if c in ',.!?;:"\'()[]{}<>')
        total = len(text)
        return {
            'chinese_punct_ratio': float(chinese_punct/total) if total > 0 else 0.0,
            'english_punct_ratio': float(english_punct/total) if total > 0 else 0.0
        }

    def _get_length_features(self, text: str) -> Dict[str, float]:
        """获取长度特征"""
        return {
            'text_length': float(len(text)),
            'word_count': float(len(list(jieba.cut(text))))
        }

    def _get_digit_features(self, text: str) -> Dict[str, float]:
        """获取数字相关特征"""
        digits = re.findall(r'\d+', text)
        return {
            'digit_count': float(len(digits)),
            'avg_digit_length': float(np.mean([len(d) for d in digits])) if digits else 0.0
        }

    def extract_features(self, text: str) -> Dict[str, float]:
        """提取所有特征"""
        features = {}
        for func in self.feature_functions:
            features.update(func(text))
        return features

    def fit(self, X, y=None):
        """训练特征提取器"""
        return self

    def transform(self, X):
        """将文本转换为特征矩阵"""
        features = [self.extract_features(text) for text in X]
        feature_names = sorted(features[0].keys())
        return np.array([[f[name] for name in feature_names] for f in features])

class LightweightMLModel:
    """
    轻量级机器学习模型类
    """
    def __init__(self):
        # 初始化特征提取器和分类器
        self.model = Pipeline([
            ('feature_extractor', FeatureExtractor()),
            ('classifier', DecisionTreeClassifier(
                max_depth=5,  # 限制树深度
                min_samples_leaf=5  # 限制叶子节点最小样本数
            ))
        ])

    def train(self, texts: List[str], labels: List[int]):
        """训练模型"""
        self.model.fit(texts, labels)

    def predict(self, text: str) -> Tuple[float, float]:
        """预测文本是否有错误"""
        prob = self.model.predict_proba([text])[0]
        return float(prob[1]), float(prob[1])  # 返回错误概率和置信度



def query_from_db(word,mdx_path):
    """从数据库查询词条"""
    # 数据库将保存在与mdx文件同名的目录下
    db_dir = os.path.dirname(mdx_path)
    db_name = os.path.basename(mdx_path).replace('.mdx', '.db')
    db_path = os.path.join(db_dir, db_name)

    if not os.path.exists(db_path):
        print("首次运行，正在解包词典到数据库...")
        start_time = time.time()
        try:
            # 确保目录存在
            os.makedirs(db_dir, exist_ok=True)
            unpack_to_db(db_dir, mdx_path)
            print(f"解包完成，耗时: {time.time() - start_time:.2f}秒")
        except Exception as e:
            print(f"解包失败: {e}")

    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.execute('SELECT paraphrase FROM mdx WHERE entry = ?', (word,))
            result = c.fetchone()
            if result:
                # 解压缩数据
                return zlib.decompress(result[0]).decode('utf-8')
            return None
    except sqlite3.OperationalError as e:
        print(f"数据库错误: {e}")
        return None

def is_in_xdhycd(word: str) -> bool:
    """
    词语见于现代汉语词典中
    """
    mdx_path = 'D:/通用资料/工具书/通用电子词典/2现代汉语/现代汉语词典7/现汉7.mdx'
    result = query_from_db(word,mdx_path)
    print(result)
    return result is not None

class LightweightTextChecker:
    """
    轻量级文本检查器类
    """
    def __init__(self):
        # 常见错误模式 TODO 及误正映射
        self.patterns = {
            'punctuation': r'[，。！？]',  # 检查中文标点
            'number_unit': r'\d+\s*[a-zA-Z]+',  # 检查数字和单位之间是否有空格
            'mixed_language': r'[a-zA-Z]+[，。！？]',  # 检查英文后是否错误使用中文标点
        }

        # 常见错误词语映射 TODO 与例外语境('出奇',['去齐了','没有出齐'])
        self.common_errors = {
            '護彤': '胡同',
            '龙晴鱼': '龙睛鱼',
            '出齐': '出奇',
        }

        # 正确词表
        self.correct_words = {
            '胡同',
            '龙睛鱼',
            '出齐',
        }

        # 初始化 N-gram 模型
        self.ngram_model = NGramModel(n=2)

        # 初始化机器学习模型
        self.ml_model = LightweightMLModel()

        # 示例训练数据
        self.training_data = [
            ("正确的文本示例", 0),
            ("错误的文本示例", 1),
            ("我的爷爷住在北京的一条胡同里。", 0),
            ("我的爷爷住在北京的一条護彤裡。", 1),
            ("他养过一种叫龙睛鱼的金鱼。", 0),
            ("他养过一种叫龙晴鱼的金鱼。", 1),
        ]

        # 训练模型
        texts, labels = zip(*self.training_data)
        self.ml_model.train(list(texts), list(labels))

    def check_text(self, text: str) -> List[CheckResult]:
        results = []

        # 检查常见错误词语
        for error, correction in self.common_errors.items():
            if error in text:
                start = text.find(error)
                results.append(CheckResult(
                    error_type='word_error',
                    location=(start, start + len(error)),
                    original_text=error,
                    suggestion=correction,
                    confidence=0.9
                ))

        # 使用 N-gram 模型检查
        words = list(jieba.cut(text))
        suggestions = self.ngram_model.get_suggestions(words)

        for pos, ngram, prob in suggestions:
            # 计算在原文中的位置
            start = sum(len(w) for w in words[:pos])
            end = start + sum(len(w) for w in words[pos:pos+self.ngram_model.n])

            results.append(CheckResult(
                error_type='ngram_error',
                location=(start, end),
                original_text=ngram,
                suggestion=f"可能的错误搭配 (概率: {prob:.6f})",
                confidence=1 - prob
            ))

        # 检查标点符号
        for match in re.finditer(self.patterns['punctuation'], text):
            if match.group() in ['，', '。', '！', '？']:
                results.append(CheckResult(
                    error_type='punctuation',
                    location=match.span(),
                    original_text=match.group(),
                    suggestion=match.group(),
                    confidence=0.7
                ))

        # 检查数字和单位格式
        for match in re.finditer(self.patterns['number_unit'], text):
            if not match.group().endswith(' '):
                results.append(CheckResult(
                    error_type='number_unit',
                    location=match.span(),
                    original_text=match.group(),
                    suggestion=match.group().replace(' ', ''),
                    confidence=0.8
                ))

        # 使用机器学习模型检查
        prob, confidence = self.ml_model.predict(text)
        if prob > 0.5:  # 如果错误概率大于0.5
            results.append(CheckResult(
                error_type='ml_error',
                location=(0, len(text)),
                original_text=text,
                suggestion="机器学习模型检测到可能的错误",
                confidence=confidence
            ))

        return results

    def apply_corrections(self, text: str, corrections: List[CheckResult]) -> str:
        result = text
        # 从后向前替换，避免位置变化影响后续替换
        for correction in sorted(corrections, key=lambda x: x.location[0], reverse=True):
            start, end = correction.location

            # 根据错误类型选择不同的处理方式
            if correction.error_type == 'word_error':
                # 对于词语错误，直接替换为建议的词语
                result = result[:start] + correction.suggestion + result[end:]
            elif correction.error_type == 'ngram_error':
                # 对于 N-gram 错误，保留原文，添加注释
                result = result[:start] + f"[{result[start:end]}]" + result[end:]
            elif correction.error_type == 'punctuation':
                # 对于标点错误，使用建议的标点
                result = result[:start] + correction.suggestion + result[end:]
            elif correction.error_type == 'number_unit':
                # 对于数字单位错误，使用建议的格式
                result = result[:start] + correction.suggestion + result[end:]
            elif correction.error_type == 'ml_error':
                # 对于机器学习检测到的错误，保留原文，添加注释
                result = f"[{result}]"

        return result

if __name__ == "__main__":
    # 测试通用规范汉字表检查
    results = check_to_general_standard_kanji_list("""升,,[昇8陞9]
    夭,,[殀]
    长,(長),
    仆,~,
    ,(僕),
    仇,,[讐讎10]
    币,(幣),
    仅,(僅),
    斤,,[觔]
    从,(從),
    仑,(侖),[崘崙]
    凶,,[兇]
    㺯兲干乾
    """)
    for result in results:
        print(f"错误类型: {result.error_type}")
        print(f"位置: {result.location}")
        print(f"原文: {result.original_text}")
        print(f"建议: {result.suggestion}")
        print(f"置信度: {result.confidence}")
        print("---")

    # 检查是否在现代汉语词典中
    # print(is_in_xdhycd('信口开合'))

    # checker = LightweightTextChecker()
    # # 可以添加更多训练数据
    # # checker.ml_model.train(["更多训练文本..."], [0, 1, ...])  # 0表示正确，1表示错误
    # test_text = "床笫置换爱。"

    # # 检查文本
    # results = checker.check_text(test_text)

    # # 打印检查结果
    # for result in results:
    #     print(f"错误类型: {result.error_type}")
    #     print(f"位置: {result.location}")
    #     print(f"原文: {result.original_text}")
    #     print(f"建议: {result.suggestion}")
    #     print(f"置信度: {result.confidence}")
    #     print("---")

    # # 应用修正
    # corrected_text = checker.apply_corrections(test_text, results)
    # print("\n修正后的文本:")
    # print(corrected_text)
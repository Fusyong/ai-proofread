import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import jieba
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline

@dataclass
class CheckResult:
    error_type: str
    location: tuple[int, int]
    original_text: str
    suggestion: str
    confidence: float

class NGramModel:
    def __init__(self, n: int = 2):
        self.n = n
        self.ngram_counts = defaultdict(int)
        self.total_ngrams = 0

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
        return self

    def transform(self, X):
        """将文本转换为特征矩阵"""
        features = [self.extract_features(text) for text in X]
        feature_names = sorted(features[0].keys())
        return np.array([[f[name] for name in feature_names] for f in features])

class LightweightMLModel:
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

class LightweightTextChecker:
    def __init__(self):
        # 常见错误模式
        self.patterns = {
            'punctuation': r'[，。！？]',  # 检查中文标点
            'number_unit': r'\d+\s*[a-zA-Z]+',  # 检查数字和单位之间是否有空格
            'mixed_language': r'[a-zA-Z]+[，。！？]',  # 检查英文后是否错误使用中文标点
        }

        # 常见错误词语映射
        self.common_errors = {
            '護彤': '胡同',
            '龙晴鱼': '龙睛鱼',
            '出齐': '出奇',
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
            result = result[:start] + correction.suggestion + result[end:]
        return result

def main():
    checker = LightweightTextChecker()
    # 可以添加更多训练数据
    # checker.ml_model.train(["更多训练文本..."], [0, 1, ...])  # 0表示正确，1表示错误
    test_text = "我的爷爷那时候住在北京，一条很宽大的小護彤裡。她很喜欢种花养鱼。至今我还记得，他养过一种叫龙晴鱼的金鱼，眼睛大得出齐，好看极了。"

    # 检查文本
    results = checker.check_text(test_text)

    # 打印检查结果
    for result in results:
        print(f"错误类型: {result.error_type}")
        print(f"位置: {result.location}")
        print(f"原文: {result.original_text}")
        print(f"建议: {result.suggestion}")
        print(f"置信度: {result.confidence}")
        print("---")

    # 应用修正
    corrected_text = checker.apply_corrections(test_text, results)
    print("\n修正后的文本:")
    print(corrected_text)

if __name__ == "__main__":
    main()
"""
测试新对齐算法的基础功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sentence_aligner_v2 import (
    normalize_for_comparison,
    prepare_sentences,
    validate_dual_chain,
    align_texts_dual_chain
)


def test_normalize():
    """测试规范化函数"""
    print("=" * 60)
    print("测试规范化函数")
    print("=" * 60)

    test_cases = [
        ("以 《评战犯求和》 为例", "以《评战犯求和》为例"),
        ("'和平'", "'和平'"),
        ('"和平"', '"和平"'),
        ("以 《评战犯求和》 为例。 这是", "以《评战犯求和》为例。这是"),
    ]

    for original, expected in test_cases:
        normalized = normalize_for_comparison(original)
        print(f"原文: {original}")
        print(f"规范化: {normalized}")
        print(f"预期: {expected}")
        print(f"匹配: {normalized == expected}")
        print()


def test_prepare_sentences():
    """测试句子准备函数"""
    print("=" * 60)
    print("测试句子准备函数")
    print("=" * 60)

    text = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。"""

    sentences = prepare_sentences(text, preserve_formatting=True)
    print(f"切分得到 {len(sentences)} 个句子：")
    for i, sent in enumerate(sentences):
        print(f"\n句子 {i}:")
        print(f"  原始文本: {sent.text[:50]}...")
        print(f"  规范化: {sent.normalized[:50]}...")
        print(f"  索引: {sent.index}")
        print(f"  行号: {sent.line_number}")
        print(f"  已匹配: {sent.matched}")


def test_align_files():
    """测试对齐两个文件"""
    print("=" * 60)
    print("测试对齐两个文件")
    print("=" * 60)

    # 读取测试文件
    file_a = Path("demo/example/a.md")
    file_b = Path("demo/example/b.md")

    if not file_a.exists() or not file_b.exists():
        print(f"测试文件不存在: {file_a} 或 {file_b}")
        return

    with open(file_a, 'r', encoding='utf-8') as f:
        text_a = f.read()
    with open(file_b, 'r', encoding='utf-8') as f:
        text_b = f.read()

    print(f"原文长度: {len(text_a)} 字符")
    print(f"校对后长度: {len(text_b)} 字符")
    print()

    # 对齐（目前只测试基础框架，实际对齐功能还未实现）
    try:
        alignment = align_texts_dual_chain(
            text_a, text_b,
            preserve_formatting=True,
            similarity_threshold=0.6,
            ngram_size=2
        )
        print(f"对齐结果: {len(alignment)} 项")
        print("\n前10项：")
        for i, item in enumerate(alignment[:10]):
            print(f"{i+1}. {item}")
    except Exception as e:
        print(f"对齐失败（预期，因为功能还未完全实现）: {e}")


if __name__ == '__main__':
    test_normalize()
    print("\n")
    test_prepare_sentences()
    print("\n")
    test_align_files()


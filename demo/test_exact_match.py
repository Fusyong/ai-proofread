"""
测试全等匹配功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sentence_aligner_v2 import (
    prepare_sentences,
    align_sentences_exact_match,
    validate_dual_chain,
    get_alignment_statistics_v2
)


def test_exact_match_simple():
    """测试简单的全等匹配"""
    print("=" * 60)
    print("测试简单全等匹配")
    print("=" * 60)

    text_a = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。"""

    text_b = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。"""

    sentences_a = prepare_sentences(text_a, preserve_formatting=True)
    sentences_b = prepare_sentences(text_b, preserve_formatting=True)

    print(f"A侧句子数: {len(sentences_a)}")
    print(f"B侧句子数: {len(sentences_b)}")
    print()

    alignment = align_sentences_exact_match(sentences_a, sentences_b)

    print(f"对齐结果: {len(alignment)} 项")
    print()

    stats = get_alignment_statistics_v2(alignment)
    print("统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # 验证双链
    is_valid, errors = validate_dual_chain(alignment, sentences_a, sentences_b)
    print(f"双链验证: {'通过' if is_valid else '失败'}")
    if errors:
        print("错误信息:")
        for error in errors[:5]:  # 只显示前5个错误
            print(f"  - {error}")
    print()

    # 显示前5项
    print("前5项对齐结果:")
    for i, item in enumerate(alignment[:5]):
        print(f"\n{i+1}. 类型: {item.type.value}")
        if item.a:
            print(f"   A: {item.a[:50]}...")
        if item.b:
            print(f"   B: {item.b[:50]}...")
        print(f"   A索引: {item.a_indices}, B索引: {item.b_indices}")
        print(f"   相似度: {item.similarity}")


def test_exact_match_with_differences():
    """测试有差异的文本"""
    print("\n" + "=" * 60)
    print("测试有差异的文本")
    print("=" * 60)

    text_a = """以 《评战犯求和》 为例。 这是毛泽东主席于 1949 年 1 月 5 日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。"""

    text_b = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。"""

    sentences_a = prepare_sentences(text_a, preserve_formatting=True)
    sentences_b = prepare_sentences(text_b, preserve_formatting=True)

    print(f"A侧句子数: {len(sentences_a)}")
    print(f"B侧句子数: {len(sentences_b)}")
    print()

    # 显示规范化后的文本
    print("规范化后的文本对比:")
    for i, (sent_a, sent_b) in enumerate(zip(sentences_a[:2], sentences_b[:2])):
        print(f"\n句子 {i}:")
        print(f"  A原始: {sent_a.text[:60]}...")
        print(f"  A规范: {sent_a.normalized[:60]}...")
        print(f"  B原始: {sent_b.text[:60]}...")
        print(f"  B规范: {sent_b.normalized[:60]}...")
        print(f"  是否全等: {sent_a.normalized == sent_b.normalized}")
    print()

    alignment = align_sentences_exact_match(sentences_a, sentences_b)

    print(f"对齐结果: {len(alignment)} 项")
    print()

    stats = get_alignment_statistics_v2(alignment)
    print("统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # 验证双链
    is_valid, errors = validate_dual_chain(alignment, sentences_a, sentences_b)
    print(f"双链验证: {'通过' if is_valid else '失败'}")
    if errors:
        print("错误信息（前5个）:")
        for error in errors[:5]:
            print(f"  - {error}")


def test_exact_match_files():
    """测试实际文件"""
    print("\n" + "=" * 60)
    print("测试实际文件")
    print("=" * 60)

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

    sentences_a = prepare_sentences(text_a, preserve_formatting=True)
    sentences_b = prepare_sentences(text_b, preserve_formatting=True)

    print(f"A侧句子数: {len(sentences_a)}")
    print(f"B侧句子数: {len(sentences_b)}")
    print()

    print("正在进行全等匹配...")
    alignment = align_sentences_exact_match(sentences_a, sentences_b)

    print(f"对齐结果: {len(alignment)} 项")
    print()

    stats = get_alignment_statistics_v2(alignment)
    print("统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # 验证双链
    is_valid, errors = validate_dual_chain(alignment, sentences_a, sentences_b)
    print(f"双链验证: {'通过' if is_valid else '失败'}")
    if errors:
        print(f"错误数量: {len(errors)}")
        print("错误信息（前10个）:")
        for error in errors[:10]:
            print(f"  - {error}")
    print()

    # 显示匹配率
    if len(sentences_a) > 0:
        match_rate = stats['match'] / len(sentences_a) * 100
        print(f"全等匹配率: {match_rate:.2f}% ({stats['match']}/{len(sentences_a)})")


if __name__ == '__main__':
    test_exact_match_simple()
    test_exact_match_with_differences()
    test_exact_match_files()


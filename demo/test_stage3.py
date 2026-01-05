"""
测试阶段3（相似度匹配基础）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sentence_aligner_v2 import (
    prepare_sentences,
    align_sentences_dual_chain,
    get_alignment_statistics_v2,
    validate_dual_chain
)


def test_stage3_simple():
    """测试简单的相似度匹配"""
    print("=" * 60)
    print("测试阶段3：相似度匹配")
    print("=" * 60)

    # 创建测试数据：有一些相似但不完全相同的句子
    text_a = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。本文一开头便揭露敌人的求和阴谋。"""

    text_b = """以《评战犯求和》为例。这是毛泽东主席于1949年1月5日为
新华社写的揭露国民党利用和平谈判来保存反革命势力的一系列评论
的第一篇。本文一开头便揭露敌人的求和阴谋：为了保存中国反动势
力和美国在华侵略势力。"""

    sentences_a = prepare_sentences(text_a, preserve_formatting=True)
    sentences_b = prepare_sentences(text_b, preserve_formatting=True)

    print(f"A侧句子数: {len(sentences_a)}")
    print(f"B侧句子数: {len(sentences_b)}")
    print()

    # 对齐（包含阶段一和阶段二）
    alignment = align_sentences_dual_chain(
        sentences_a, sentences_b,
        similarity_threshold=0.6,
        ngram_size=2
    )

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
    print()

    # 显示匹配项
    print("匹配项:")
    for i, item in enumerate(alignment):
        if item.type.value == 'match':
            print(f"\n{i+1}. 相似度: {item.similarity:.2f}")
            if item.a:
                print(f"   A: {item.a[:60]}...")
            if item.b:
                print(f"   B: {item.b[:60]}...")
            print(f"   A索引: {item.a_indices}, B索引: {item.b_indices}")


def test_stage3_files():
    """测试实际文件"""
    print("\n" + "=" * 60)
    print("测试实际文件（阶段3）")
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

    print("正在进行对齐（阶段一+阶段二）...")
    alignment = align_sentences_dual_chain(
        sentences_a, sentences_b,
        similarity_threshold=0.6,
        ngram_size=2
    )

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
        match_count = stats['match']
        total_count = stats['total']
        match_rate = match_count / total_count * 100 if total_count > 0 else 0
        print(f"总匹配率: {match_rate:.2f}% ({match_count}/{total_count})")

        # 阶段一匹配数（全等匹配）
        # 可以通过统计similarity=1.0的项来估算
        exact_matches = sum(1 for item in alignment
                           if item.type.value == 'match' and
                           hasattr(item, 'similarity') and
                           item.similarity == 1.0)
        print(f"全等匹配: {exact_matches}")
        print(f"相似度匹配: {match_count - exact_matches}")


if __name__ == '__main__':
    test_stage3_simple()
    test_stage3_files()


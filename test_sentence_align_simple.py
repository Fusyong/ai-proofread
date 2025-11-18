"""
测试简单锚点对齐算法
"""

from src.sentence_aligner_simple import (
    align_sentences_anchor,
    align_texts_anchor,
    get_alignment_statistics,
    jaccard_similarity
)


def test_jaccard_similarity():
    """测试Jaccard相似度计算"""
    print("=" * 60)
    print("测试Jaccard相似度计算")
    print("=" * 60)

    test_cases = [
        ("这是第一句话。", "这是第一句话。", 1.0),
        ("这是第一句话。", "这是第一句话！", 0.8),  # 标点不同
        ("这是第一句话。", "这是第二句话。", 0.6),  # 内容不同
    ]

    for sent_a, sent_b, expected in test_cases:
        similarity = jaccard_similarity(sent_a, sent_b, n=2)
        print(f"A: {sent_a}")
        print(f"B: {sent_b}")
        print(f"相似度: {similarity:.2%} (期望约: {expected:.2%})")
        print()


def test_simple_alignment():
    """测试简单对齐"""
    print("=" * 60)
    print("测试简单对齐（锚点算法）")
    print("=" * 60)

    sentences_a = [
        "这是第一句话。",
        "这是第二句话！",
        "这是第三句话？",
        "这是第四句话。",
        "这是第五句话。"
    ]

    sentences_b = [
        "这是第一句话。",
        "这是第二句话！",
        "这是第三句话？",
        "这是第四句话。",
        "这是第五句话。",
        "这是新增的第六句话。"
    ]

    alignment = align_sentences_anchor(
        sentences_a, sentences_b,
        window_size=5,
        similarity_threshold=0.6
    )
    stats = get_alignment_statistics(alignment)

    print(f"原文句子数: {len(sentences_a)}")
    print(f"校对后句子数: {len(sentences_b)}")
    print(f"\n对齐结果统计:")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']}")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")

    print(f"\n详细对齐结果:")
    for i, item in enumerate(alignment, 1):
        print(f"\n#{i} [{item['type']}]")
        if item['a']:
            print(f"  A: {item['a']}")
        if item['b']:
            print(f"  B: {item['b']}")
        if item.get('similarity'):
            print(f"  相似度: {item['similarity']:.2%}")


def test_with_changes():
    """测试有修改的情况"""
    print("=" * 60)
    print("测试有修改的情况（锚点算法）")
    print("=" * 60)

    text_a = """在中国古代经学史上，南宋无疑是个至为关键的时期。
本书通过文献梳理、考据实证、归纳分析，对南宋经学诸派的渊源、传承、经学诠释方式及历史影响等进行分析和总结。"""

    text_b = """在中国古代经学史上，南宋无疑是个至为关键的时期。
本书通过文献梳理、考据实证、归纳分析，对南宋经学诸派的渊源、传承、经学诠释方式及历史影响等进行分析和总结，探究了南宋经学与政治的内在关联。"""

    alignment = align_texts_anchor(
        text_a, text_b,
        preserve_formatting=False,
        window_size=5,
        similarity_threshold=0.6
    )
    stats = get_alignment_statistics(alignment)

    print(f"\n对齐结果统计:")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']}")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")

    print(f"\n详细对齐结果:")
    for i, item in enumerate(alignment, 1):
        print(f"\n#{i} [{item['type']}]")
        if item['a']:
            print(f"  A: {item['a'][:60]}...")
        if item['b']:
            print(f"  B: {item['b'][:60]}...")
        if item.get('similarity'):
            print(f"  相似度: {item['similarity']:.2%}")


if __name__ == '__main__':
    test_jaccard_similarity()
    print("\n")
    test_simple_alignment()
    print("\n")
    test_with_changes()


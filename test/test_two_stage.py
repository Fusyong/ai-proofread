"""
测试两阶段对齐算法，并与现有算法对比
"""

import argparse
from pathlib import Path
from src.sentence_aligner_simple import align_texts_anchor, get_alignment_statistics
from src.sentence_aligner_two_stage import align_texts_two_stage


def compare_algorithms(text_a_path: str, text_b_path: str):
    """对比两种算法的效果"""

    # 读取文件
    print(f"读取原文: {text_a_path}")
    with open(text_a_path, 'r', encoding='utf-8') as f:
        text_a = f.read()

    print(f"读取校对后文本: {text_b_path}")
    with open(text_b_path, 'r', encoding='utf-8') as f:
        text_b = f.read()

    # 使用现有算法
    print("\n" + "="*60)
    print("现有算法（单阶段锚点算法）")
    print("="*60)
    alignment_simple = align_texts_anchor(
        text_a,
        text_b,
        preserve_formatting=True,
        window_size=10,
        similarity_threshold=0.6,
        ngram_size=2,
        offset=1,
        max_window_expansion=3,
        consecutive_fail_threshold=3
    )
    stats_simple = get_alignment_statistics(alignment_simple)
    print(f"  总计: {stats_simple['total']}")
    print(f"  匹配: {stats_simple['match']} ({stats_simple['match']/stats_simple['total']*100:.1f}%)")
    print(f"  删除: {stats_simple['delete']}")
    print(f"  新增: {stats_simple['insert']}")

    # 使用两阶段算法
    print("\n" + "="*60)
    print("两阶段算法（长度LCS + 锚点算法）")
    print("="*60)

    # 先计算锚点数量（用于调试）
    from src.splitter import split_chinese_sentences
    from src.sentence_aligner_two_stage import (
        compute_sentence_lengths,
        lcs_length_sequence
    )
    sentences_a = [s.strip() for s in split_chinese_sentences(text_a, True) if s.strip()]
    sentences_b = [s.strip() for s in split_chinese_sentences(text_b, True) if s.strip()]
    lengths_a = compute_sentence_lengths(sentences_a, ignore_whitespace=True)
    lengths_b = compute_sentence_lengths(sentences_b, ignore_whitespace=True)
    anchors = lcs_length_sequence(lengths_a, lengths_b, strict_match=True)
    print(f"  锚点数量: {len(anchors)}")
    if anchors:
        print(f"  锚点示例: {anchors[:5]}...")

    alignment_two_stage = align_texts_two_stage(
        text_a,
        text_b,
        preserve_formatting=True,
        length_window_size=3,
        length_similarity_threshold=0.8,
        window_size=10,
        similarity_threshold=0.6,
        ngram_size=2,
        offset=1,
        max_window_expansion=3,
        consecutive_fail_threshold=3,
        enable_many_to_many=True,
        max_merge_size=3
    )
    stats_two_stage = get_alignment_statistics(alignment_two_stage)
    print(f"  总计: {stats_two_stage['total']}")
    print(f"  匹配: {stats_two_stage['match']} ({stats_two_stage['match']/stats_two_stage['total']*100:.1f}%)")
    print(f"  删除: {stats_two_stage['delete']}")
    print(f"  新增: {stats_two_stage['insert']}")

    # 对比结果
    print("\n" + "="*60)
    print("对比结果")
    print("="*60)
    match_diff = stats_two_stage['match'] - stats_simple['match']
    delete_diff = stats_two_stage['delete'] - stats_simple['delete']
    insert_diff = stats_two_stage['insert'] - stats_simple['insert']

    print(f"匹配差异: {match_diff:+d} ({match_diff/stats_simple['total']*100:+.1f}%)")
    print(f"删除差异: {delete_diff:+d}")
    print(f"新增差异: {insert_diff:+d}")

    if match_diff > 0:
        print(f"\n[+] 两阶段算法匹配率提升了 {match_diff/stats_simple['total']*100:.1f}%")
    elif match_diff < 0:
        print(f"\n[-] 两阶段算法匹配率下降了 {abs(match_diff)/stats_simple['total']*100:.1f}%")
    else:
        print(f"\n[=] 两种算法匹配率相同")

    # 检查多对多匹配
    many_to_many_count = 0
    for item in alignment_two_stage:
        if item.get('type') == 'match':
            a_count = len(item.get('a_indices', []))
            b_count = len(item.get('b_indices', []))
            if a_count > 1 or b_count > 1:
                many_to_many_count += 1

    print(f"\n多对多匹配数量: {many_to_many_count}")

    return alignment_simple, alignment_two_stage, stats_simple, stats_two_stage


def main():
    parser = argparse.ArgumentParser(
        description='对比单阶段和两阶段对齐算法'
    )
    parser.add_argument(
        '-a', '--text-a',
        required=True,
        help='原文文件路径'
    )
    parser.add_argument(
        '-b', '--text-b',
        required=True,
        help='校对后文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        default='comparison',
        help='输出文件前缀'
    )

    args = parser.parse_args()

    # 对比算法
    alignment_simple, alignment_two_stage, stats_simple, stats_two_stage = compare_algorithms(
        args.text_a,
        args.text_b
    )

    # 保存结果
    import json

    simple_path = f"{args.output}_simple.json"
    print(f"\n保存现有算法结果: {simple_path}")
    with open(simple_path, 'w', encoding='utf-8') as f:
        json.dump(alignment_simple, f, ensure_ascii=False, indent=2)

    two_stage_path = f"{args.output}_two_stage.json"
    print(f"保存两阶段算法结果: {two_stage_path}")
    with open(two_stage_path, 'w', encoding='utf-8') as f:
        json.dump(alignment_two_stage, f, ensure_ascii=False, indent=2)

    print(f"\n对比完成！")


if __name__ == '__main__':
    main()


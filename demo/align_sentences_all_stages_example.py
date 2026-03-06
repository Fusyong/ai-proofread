"""
输出所有对齐阶段的HTML报告 - 完整示例

这个示例展示了如何在对齐过程中获取各个阶段的中间结果并输出HTML。

用法:
    python demo/align_sentences_all_stages_example.py -a demo/example/a.md -b demo/example/b.md --threshold 0.6
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import time

from src.sentence_aligner import (
    align_sentences_anchor,
    align_sentences_anchor_initial,
    rematch_adjacent_delete_insert,
    rematch_non_adjacent_delete_insert,
    merge_delete_into_match,
    merge_insert_into_match,
    detect_and_handle_movements,
    get_alignment_statistics,
    normalize_sentence,
    jaccard_similarity
)
from src.splitter import split_chinese_sentences, split_chinese_sentences_with_line_numbers
from src.html_report_v2 import save_html_report_stage1




def main():
    parser = argparse.ArgumentParser(
        description='对齐两个文本的句子，并输出所有阶段的HTML报告'
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
        default='alignment_all_stages',
        help='输出文件前缀（不含扩展名），默认: alignment_all_stages'
    )
    parser.add_argument(
        '--window-size',
        type=int,
        default=10,
        help='搜索窗口大小，默认: 10'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.6,
        help='相似度阈值（0-1），默认: 0.6'
    )
    parser.add_argument(
        '--ngram',
        type=int,
        default=2,
        help='n-gram大小，默认: 2'
    )

    args = parser.parse_args()

    start_time = time.time()

    # 读取文件
    print(f"读取原文: {args.text_a}")
    with open(args.text_a, 'r', encoding='utf-8') as f:
        text_a = f.read()

    print(f"读取校对后文本: {args.text_b}")
    with open(args.text_b, 'r', encoding='utf-8') as f:
        text_b = f.read()

    title_a = Path(args.text_a).name
    title_b = Path(args.text_b).name
    output_base = args.output

    # 切分句子并获取行号
    print("\n切分句子...")
    sentences_a_with_lines = split_chinese_sentences_with_line_numbers(text_a)
    sentences_b_with_lines = split_chinese_sentences_with_line_numbers(text_b)

    # 提取句子列表（保留原始数据，不清理空白字符）
    # 原则：始终保留原始数据，只在需要比较时临时清理（通过normalize_sentence）
    # 只过滤完全为空的句子（None或空字符串），但保留只包含空白字符的句子
    sentences_a = [s for s, _, _ in sentences_a_with_lines if s]  # 保留原始数据
    sentences_b = [s for s, _, _ in sentences_b_with_lines if s]  # 保留原始数据

    # 创建行号映射（使用start_line作为行号）
    line_numbers_a = [start_line for _, start_line, _ in sentences_a_with_lines]
    line_numbers_b = [start_line for _, start_line, _ in sentences_b_with_lines]

    print(f"原文句子数: {len(sentences_a)}")
    print(f"校对后句子数: {len(sentences_b)}")

    def add_line_numbers_to_alignment(alignment):
        """为对齐结果添加行号信息"""
        for item in alignment:
            # 处理原文行号
            if 'a_indices' in item:
                a_indices = item['a_indices']
                if a_indices:
                    item['a_line_numbers'] = [line_numbers_a[i] for i in a_indices if i < len(line_numbers_a)]
                    if item['a_line_numbers']:
                        item['a_line_number'] = item['a_line_numbers'][0]  # 首行
            elif 'a_index' in item and item['a_index'] is not None:
                a_idx = item['a_index']
                if a_idx < len(line_numbers_a):
                    item['a_line_number'] = line_numbers_a[a_idx]
                    item['a_line_numbers'] = [line_numbers_a[a_idx]]

            # 处理校对后行号
            if 'b_indices' in item:
                b_indices = item['b_indices']
                if b_indices:
                    item['b_line_numbers'] = [line_numbers_b[i] for i in b_indices if i < len(line_numbers_b)]
                    if item['b_line_numbers']:
                        item['b_line_number'] = item['b_line_numbers'][0]  # 首行
            elif 'b_index' in item and item['b_index'] is not None:
                b_idx = item['b_index']
                if b_idx < len(line_numbers_b):
                    item['b_line_number'] = line_numbers_b[b_idx]
                    item['b_line_numbers'] = [line_numbers_b[b_idx]]
        return alignment

    # 阶段0: 初始对齐（不包含后处理）
    print("\n" + "="*60)
    print("阶段0: 初始对齐（锚点算法，不包含后处理）")
    print("="*60)

    alignment_stage0 = align_sentences_anchor_initial(
        sentences_a,
        sentences_b,
        window_size=args.window_size,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram
    )

    # 为阶段0添加行号信息
    alignment_stage0 = add_line_numbers_to_alignment(alignment_stage0)

    html_path_stage0 = f"{output_base}_stage0_initial.html"
    print(f"保存HTML: {html_path_stage0}")
    stats_stage0 = get_alignment_statistics(alignment_stage0)
    save_html_report_stage1(
        alignment_stage0,
        html_path_stage0,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_stage0
    )
    print(f"统计: 总计={stats_stage0['total']}, 匹配={stats_stage0['match']}, "
          f"删除={stats_stage0['delete']}, 新增={stats_stage0['insert']}")

    # 阶段1: 相邻DELETE和INSERT重新匹配
    print("\n" + "="*60)
    print("阶段1: 相邻DELETE和INSERT重新匹配")
    print("="*60)

    html_path_stage1 = f"{output_base}_stage1_adjacent.html"
    alignment_stage1 = rematch_adjacent_delete_insert(
        alignment_stage0,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram,
        html_output_path=html_path_stage1,
        title_a=title_a,
        title_b=title_b
    )
    # 确保行号信息保留（rematch可能会创建新项，需要重新添加行号）
    alignment_stage1 = add_line_numbers_to_alignment(alignment_stage1)
    stats_stage1 = get_alignment_statistics(alignment_stage1)
    print(f"统计: 总计={stats_stage1['total']}, 匹配={stats_stage1['match']}, "
          f"删除={stats_stage1['delete']}, 新增={stats_stage1['insert']}")

    # 阶段2: 不相邻DELETE和INSERT重新匹配
    print("\n" + "="*60)
    print("阶段2: 不相邻DELETE和INSERT重新匹配")
    print("="*60)

    html_path_stage2 = f"{output_base}_stage2_non_adjacent.html"
    alignment_stage2 = rematch_non_adjacent_delete_insert(
        alignment_stage1,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram,
        index_range=args.window_size,
        html_output_path=html_path_stage2,
        title_a=title_a,
        title_b=title_b
    )
    # 确保行号信息保留
    alignment_stage2 = add_line_numbers_to_alignment(alignment_stage2)
    stats_stage2 = get_alignment_statistics(alignment_stage2)
    print(f"统计: 总计={stats_stage2['total']}, 匹配={stats_stage2['match']}, "
          f"删除={stats_stage2['delete']}, 新增={stats_stage2['insert']}")

    # 阶段3: 合并DELETE到MATCH，再合并INSERT到MATCH
    print("\n" + "="*60)
    print("阶段3: 合并DELETE到相邻MATCH、合并INSERT到相邻MATCH")
    print("="*60)

    alignment_stage3 = merge_delete_into_match(
        alignment_stage2,
        ngram_size=args.ngram
    )
    alignment_stage3 = merge_insert_into_match(
        alignment_stage3,
        ngram_size=args.ngram
    )

    # 确保行号信息保留
    alignment_stage3 = add_line_numbers_to_alignment(alignment_stage3)

    html_path_stage3 = f"{output_base}_stage3_merge_delete.html"
    print(f"保存HTML: {html_path_stage3}")
    stats_stage3 = get_alignment_statistics(alignment_stage3)
    save_html_report_stage1(
        alignment_stage3,
        html_path_stage3,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_stage3
    )
    print(f"统计: 总计={stats_stage3['total']}, 匹配={stats_stage3['match']}, "
          f"删除={stats_stage3['delete']}, 新增={stats_stage3['insert']}")

    # 阶段4: 检测和处理移动
    print("\n" + "="*60)
    print("阶段4: 检测和处理句子移动")
    print("="*60)

    alignment_final = detect_and_handle_movements(
        alignment_stage3,
        movement_threshold=2
    )

    # 确保行号信息保留（detect_and_handle_movements已经保留了行号，但为了保险再添加一次）
    alignment_final = add_line_numbers_to_alignment(alignment_final)

    html_path_final = f"{output_base}_stage4_final.html"
    print(f"保存HTML: {html_path_final}")
    stats_final = get_alignment_statistics(alignment_final)
    save_html_report_stage1(
        alignment_final,
        html_path_final,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_final
    )
    print(f"统计: 总计={stats_final['total']}, 匹配={stats_final['match']}, "
          f"删除={stats_final['delete']}, 新增={stats_final['insert']}, "
          f"移入={stats_final.get('movein', 0)}, 移出={stats_final.get('moveout', 0)}")

    # 保存最终结果JSON
    json_path_final = f"{output_base}_final.json"
    print(f"\n保存最终结果JSON: {json_path_final}")
    with open(json_path_final, 'w', encoding='utf-8') as f:
        json.dump(alignment_final, f, ensure_ascii=False, indent=2)

    # 保存各阶段JSON（可选）
    stages_data = {
        "stage0_initial": alignment_stage0,
        "stage1_adjacent": alignment_stage1,
        "stage2_non_adjacent": alignment_stage2,
        "stage3_merge_delete": alignment_stage3,
        "stage4_final": alignment_final
    }

    json_path_all = f"{output_base}_all_stages.json"
    print(f"保存所有阶段JSON: {json_path_all}")
    with open(json_path_all, 'w', encoding='utf-8') as f:
        json.dump(stages_data, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print("所有阶段HTML报告已生成:")
    print("="*60)
    print(f"  阶段0: {html_path_stage0}")
    print(f"  阶段1: {html_path_stage1}")
    print(f"  阶段2: {html_path_stage2}")
    print(f"  阶段3: {html_path_stage3}")
    print(f"  阶段4: {html_path_final}")
    print(f"\n运行时间: {time.time() - start_time:.2f}秒")


if __name__ == '__main__':
    main()

"""
输出所有对齐阶段的HTML报告 - 双链算法完整示例

这个示例展示了如何使用双链算法在对齐过程中获取各个阶段的中间结果并输出HTML。

用法:
    python demo/align_sentences_v2_all_stages_example.py -a demo/example/a.md -b demo/example/b.md
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import time

from src.sentence_aligner_v2 import (
    align_texts_dual_chain,
    get_alignment_statistics_v2,
    prepare_sentences
)
from src.html_report_v2 import save_html_report_stage1


def main():
    parser = argparse.ArgumentParser(
        description='使用双链算法对齐两个文本的句子，并输出所有阶段的HTML报告'
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
        default='alignment_v2_all_stages',
        help='输出文件前缀（不含扩展名），默认: alignment_v2_all_stages'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.6,
        help='相似度阈值（0-1），默认: 0.6（阶段二使用）'
    )
    parser.add_argument(
        '--ngram',
        type=int,
        default=2,
        help='n-gram大小，默认: 2（阶段二使用）'
    )
    parser.add_argument(
        '--no-formatting',
        action='store_true',
        help='不保留Markdown格式'
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

    # 切分句子
    print("\n切分句子...")
    sentences_a = prepare_sentences(text_a, preserve_formatting=not args.no_formatting)
    sentences_b = prepare_sentences(text_b, preserve_formatting=not args.no_formatting)

    print(f"原文句子数: {len(sentences_a)}")
    print(f"校对后句子数: {len(sentences_b)}")

    # 对齐句子（获取每个阶段的中间结果）
    print("\n" + "="*60)
    print("正在进行句子对齐（双链算法）...")
    print("="*60)

    alignment_final, alignment_stage1, alignment_stage2 = align_texts_dual_chain(
        text_a,
        text_b,
        preserve_formatting=not args.no_formatting,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram,
        return_stages=True
    )

    # 阶段1: 全等匹配
    print("\n" + "="*60)
    print("阶段1: 全等匹配")
    print("="*60)

    html_path_stage1 = f"{output_base}_stage1_exact_match.html"
    print(f"保存HTML: {html_path_stage1}")
    stats_stage1 = get_alignment_statistics_v2(alignment_stage1)
    save_html_report_stage1(
        alignment_stage1,
        html_path_stage1,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_stage1
    )
    print(f"统计: 总计={stats_stage1['total']}, 匹配={stats_stage1['match']}, "
          f"删除={stats_stage1['delete']}, 新增={stats_stage1['insert']}")
    if stats_stage1['total'] > 0:
        match_rate = stats_stage1['match'] / stats_stage1['total'] * 100
        print(f"匹配率: {match_rate:.2f}%")

    # 阶段2: 相似度匹配（最终结果）
    print("\n" + "="*60)
    print("阶段2: 相似度匹配（最终结果）")
    print("="*60)

    html_path_stage2 = f"{output_base}_stage2_similarity.html"
    print(f"保存HTML: {html_path_stage2}")
    stats_stage2 = get_alignment_statistics_v2(alignment_stage2)
    save_html_report_stage1(
        alignment_stage2,
        html_path_stage2,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_stage2
    )
    print(f"统计: 总计={stats_stage2['total']}, 匹配={stats_stage2['match']}, "
          f"删除={stats_stage2['delete']}, 新增={stats_stage2['insert']}")
    if stats_stage2['total'] > 0:
        match_rate = stats_stage2['match'] / stats_stage2['total'] * 100
        print(f"匹配率: {match_rate:.2f}%")

    # 最终结果（与阶段2相同，但单独保存一份）
    print("\n" + "="*60)
    print("最终结果")
    print("="*60)

    html_path_final = f"{output_base}_final.html"
    print(f"保存HTML: {html_path_final}")
    stats_final = get_alignment_statistics_v2(alignment_final)
    save_html_report_stage1(
        alignment_final,
        html_path_final,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats_final
    )
    print(f"统计: 总计={stats_final['total']}, 匹配={stats_final['match']}, "
          f"删除={stats_final['delete']}, 新增={stats_final['insert']}")
    if stats_final['total'] > 0:
        match_rate = stats_final['match'] / stats_final['total'] * 100
        print(f"匹配率: {match_rate:.2f}%")

    # 保存最终结果JSON
    json_path_final = f"{output_base}_final.json"
    print(f"\n保存最终结果JSON: {json_path_final}")
    with open(json_path_final, 'w', encoding='utf-8') as f:
        json.dump(alignment_final, f, ensure_ascii=False, indent=2)

    # 保存各阶段JSON（可选）
    stages_data = {
        "stage1_exact_match": alignment_stage1,
        "stage2_similarity": alignment_stage2,
        "final": alignment_final
    }

    json_path_all = f"{output_base}_all_stages.json"
    print(f"保存所有阶段JSON: {json_path_all}")
    with open(json_path_all, 'w', encoding='utf-8') as f:
        json.dump(stages_data, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print("所有阶段HTML报告已生成:")
    print("="*60)
    print(f"  阶段1: {html_path_stage1}")
    print(f"  阶段2: {html_path_stage2}")
    print(f"  最终结果: {html_path_final}")
    print(f"\n运行时间: {time.time() - start_time:.2f}秒")


if __name__ == '__main__':
    main()

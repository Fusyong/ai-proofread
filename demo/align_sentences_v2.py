"""
新版本句子对齐脚本（基于双链算法）

用法:
    python demo/align_sentences_v2.py -a demo/example/a.md -b demo/example/b.md
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import csv
import time

from src.sentence_aligner_v2 import (
    align_texts_dual_chain,
    get_alignment_statistics_v2,
    prepare_sentences
)
from src.html_report_v2 import save_html_report_stage1


def main():
    parser = argparse.ArgumentParser(
        description='使用双链算法对齐两个文本的句子（新版本）'
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
        default='alignment_result_v2_stage1',
        help='输出文件前缀（不含扩展名），默认: alignment_result_v2_stage1'
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

    # 记录开始时间
    start_time = time.time()

    # 读取文件
    print(f"读取原文: {args.text_a}")
    with open(args.text_a, 'r', encoding='utf-8') as f:
        text_a = f.read()

    print(f"读取校对后文本: {args.text_b}")
    with open(args.text_b, 'r', encoding='utf-8') as f:
        text_b = f.read()

    # 切分句子并保存为CSV（用于调试）
    print("切分句子...")
    sentences_a = prepare_sentences(text_a, preserve_formatting=not args.no_formatting)
    sentences_b = prepare_sentences(text_b, preserve_formatting=not args.no_formatting)

    # 保存A侧句子切分结果到CSV
    csv_path_a = f"{args.output}_sentences_a.csv"
    print(f"保存A侧句子切分结果: {csv_path_a}")
    with open(csv_path_a, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['句子索引', '行号', '原始文本'])
        for sent in sentences_a:
            writer.writerow([sent.index, sent.line_number, sent.text])

    # 保存B侧句子切分结果到CSV
    csv_path_b = f"{args.output}_sentences_b.csv"
    print(f"保存B侧句子切分结果: {csv_path_b}")
    with open(csv_path_b, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['句子索引', '行号', '原始文本'])
        for sent in sentences_b:
            writer.writerow([sent.index, sent.line_number, sent.text])

    # 对齐句子（目前只实现阶段一：全等匹配）
    print("正在进行句子对齐（阶段一：全等匹配）...")
    alignment = align_texts_dual_chain(
        text_a,
        text_b,
        preserve_formatting=not args.no_formatting,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram
    )

    # 统计信息
    stats = get_alignment_statistics_v2(alignment)
    print("\n对齐完成！统计信息:")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']}")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")

    if stats['total'] > 0:
        match_rate = stats['match'] / stats['total'] * 100
        print(f"  匹配率: {match_rate:.2f}%")

    # 保存结果
    output_base = args.output

    json_path = f"{output_base}.json"
    print(f"\n保存JSON报告: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(alignment, f, ensure_ascii=False, indent=2)

    html_path = f"{output_base}.html"
    print(f"保存HTML报告: {html_path}")
    title_a = Path(args.text_a).name
    title_b = Path(args.text_b).name

    # 计算运行时间
    runtime = time.time() - start_time

    save_html_report_stage1(
        alignment,
        html_path,
        title_a,
        title_b,
        runtime=runtime,
        stats=stats
    )

    print(f"\n所有报告已保存到: {output_base}.*")
    print(f"运行时间: {runtime:.2f}秒")


if __name__ == '__main__':
    main()


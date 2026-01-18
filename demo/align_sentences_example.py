"""
使用align_sentences_anchor对齐句子并生成HTML报告 - 完整示例

这个示例直接使用align_sentences_anchor函数（包含所有后处理步骤）进行对齐。

用法:
    python demo/align_sentences_example.py -a demo/example/a.md -b demo/example/b.md --threshold 0.6
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
    get_alignment_statistics
)
from src.splitter import split_chinese_sentences_with_line_numbers
from src.html_report_v2 import save_html_report_stage1


def main():
    parser = argparse.ArgumentParser(
        description='对齐两个文本的句子，生成HTML报告'
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
        default='alignment',
        help='输出文件前缀（不含扩展名），默认: alignment'
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

    # 执行对齐（包含所有后处理步骤）
    print("\n" + "="*60)
    print("执行对齐（锚点算法 + 所有后处理步骤）")
    print("="*60)

    alignment = align_sentences_anchor(
        sentences_a,
        sentences_b,
        window_size=args.window_size,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram
    )

    # 为对齐结果添加行号信息
    alignment = add_line_numbers_to_alignment(alignment)

    # 生成HTML报告
    html_path = f"{output_base}.html"
    print(f"\n保存HTML报告: {html_path}")
    stats = get_alignment_statistics(alignment)
    save_html_report_stage1(
        alignment,
        html_path,
        title_a=title_a,
        title_b=title_b,
        runtime=time.time() - start_time,
        stats=stats,
        algorithm_name="锚点算法",
        threshold=args.threshold,
        ngram_size=args.ngram
    )
    print(f"统计: 总计={stats['total']}, 匹配={stats['match']}, "
          f"删除={stats['delete']}, 新增={stats['insert']}, "
          f"移入={stats.get('movein', 0)}, 移出={stats.get('moveout', 0)}")

    # 保存结果JSON
    json_path = f"{output_base}.json"
    print(f"\n保存结果JSON: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(alignment, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print("处理完成")
    print("="*60)
    print(f"HTML报告: {html_path}")
    print(f"JSON结果: {json_path}")
    print(f"\n运行时间: {time.time() - start_time:.2f}秒")


if __name__ == '__main__':
    main()

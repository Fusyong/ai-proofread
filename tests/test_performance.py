"""
性能测试：对比单阶段和两阶段对齐算法的耗时和各项指标
"""

import argparse
import time
import json
import sys
from pathlib import Path
from src.sentence_aligner_simple import align_texts_anchor, get_alignment_statistics
from src.sentence_aligner_two_stage import align_texts_two_stage


def format_time(seconds):
    """格式化时间显示"""
    if seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.3f} s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.2f}s"


def test_algorithm_performance(text_a_path: str, text_b_path: str, iterations: int = 3):
    """测试算法性能"""

    # 读取文件
    print(f"读取原文: {text_a_path}")
    with open(text_a_path, 'r', encoding='utf-8') as f:
        text_a = f.read()

    print(f"读取校对后文本: {text_b_path}")
    with open(text_b_path, 'r', encoding='utf-8') as f:
        text_b = f.read()

    # 统计文本信息
    from src.splitter import split_chinese_sentences
    sentences_a = [s.strip() for s in split_chinese_sentences(text_a, True) if s.strip()]
    sentences_b = [s.strip() for s in split_chinese_sentences(text_b, True) if s.strip()]

    print(f"\n文本统计:")
    print(f"  原文句子数: {len(sentences_a)}")
    print(f"  校对后句子数: {len(sentences_b)}")
    print(f"  原文字符数: {len(text_a):,}")
    print(f"  校对后字符数: {len(text_b):,}")

    results = {}

    # ========== 测试单阶段算法 ==========
    print("\n" + "="*70)
    print("测试单阶段算法（锚点算法）")
    print("="*70)

    simple_times = []
    simple_results = []

    for i in range(iterations):
        print(f"  运行 {i+1}/{iterations}...", end=" ", flush=True)
        start_time = time.time()

        alignment = align_texts_anchor(
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

        elapsed = time.time() - start_time
        simple_times.append(elapsed)
        simple_results.append(alignment)
        print(f"完成 ({format_time(elapsed)})")

    # 计算平均时间
    avg_time = sum(simple_times) / len(simple_times)
    min_time = min(simple_times)
    max_time = max(simple_times)

    # 使用最后一次运行的结果进行统计
    stats = get_alignment_statistics(simple_results[-1])

    # 统计多对多匹配
    many_to_many_count = 0
    for item in simple_results[-1]:
        if item.get('type') == 'match':
            a_count = len(item.get('a_indices', []))
            b_count = len(item.get('b_indices', []))
            if a_count > 1 or b_count > 1:
                many_to_many_count += 1

    results['simple'] = {
        'times': simple_times,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'stats': stats,
        'many_to_many': many_to_many_count,
        'alignment': simple_results[-1]
    }

    print(f"\n  平均耗时: {format_time(avg_time)}")
    print(f"  最快耗时: {format_time(min_time)}")
    print(f"  最慢耗时: {format_time(max_time)}")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']} ({stats['match']/stats['total']*100:.2f}%)")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")
    print(f"  多对多匹配: {many_to_many_count}")

    # ========== 测试两阶段算法 ==========
    print("\n" + "="*70)
    print("测试两阶段算法（长度LCS + 锚点算法）")
    print("="*70)

    two_stage_times = []
    two_stage_results = []

    for i in range(iterations):
        print(f"  运行 {i+1}/{iterations}...", end=" ", flush=True)
        start_time = time.time()

        alignment = align_texts_two_stage(
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

        elapsed = time.time() - start_time
        two_stage_times.append(elapsed)
        two_stage_results.append(alignment)
        print(f"完成 ({format_time(elapsed)})")

    # 计算平均时间
    avg_time = sum(two_stage_times) / len(two_stage_times)
    min_time = min(two_stage_times)
    max_time = max(two_stage_times)

    # 使用最后一次运行的结果进行统计
    stats = get_alignment_statistics(two_stage_results[-1])

    # 统计多对多匹配
    many_to_many_count = 0
    for item in two_stage_results[-1]:
        if item.get('type') == 'match':
            a_count = len(item.get('a_indices', []))
            b_count = len(item.get('b_indices', []))
            if a_count > 1 or b_count > 1:
                many_to_many_count += 1

    results['two_stage'] = {
        'times': two_stage_times,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'stats': stats,
        'many_to_many': many_to_many_count,
        'alignment': two_stage_results[-1]
    }

    print(f"\n  平均耗时: {format_time(avg_time)}")
    print(f"  最快耗时: {format_time(min_time)}")
    print(f"  最慢耗时: {format_time(max_time)}")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']} ({stats['match']/stats['total']*100:.2f}%)")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")
    print(f"  多对多匹配: {many_to_many_count}")

    # ========== 对比结果 ==========
    print("\n" + "="*70)
    print("性能对比")
    print("="*70)

    simple_avg = results['simple']['avg_time']
    two_stage_avg = results['two_stage']['avg_time']
    time_ratio = two_stage_avg / simple_avg if simple_avg > 0 else 0

    print(f"\n耗时对比:")
    print(f"  单阶段算法: {format_time(simple_avg)}")
    print(f"  两阶段算法: {format_time(two_stage_avg)}")
    print(f"  时间比率: {time_ratio:.2f}x ({'+' if time_ratio > 1 else ''}{((time_ratio - 1) * 100):.1f}%)")

    print(f"\n匹配效果对比:")
    simple_stats = results['simple']['stats']
    two_stage_stats = results['two_stage']['stats']

    match_diff = two_stage_stats['match'] - simple_stats['match']
    match_rate_diff = (two_stage_stats['match'] / two_stage_stats['total'] * 100) - \
                     (simple_stats['match'] / simple_stats['total'] * 100)
    delete_diff = two_stage_stats['delete'] - simple_stats['delete']
    insert_diff = two_stage_stats['insert'] - simple_stats['insert']

    print(f"  匹配数: {simple_stats['match']} → {two_stage_stats['match']} ({match_diff:+d})")
    print(f"  匹配率: {simple_stats['match']/simple_stats['total']*100:.2f}% → {two_stage_stats['match']/two_stage_stats['total']*100:.2f}% ({match_rate_diff:+.2f}%)")
    print(f"  删除项: {simple_stats['delete']} → {two_stage_stats['delete']} ({delete_diff:+d})")
    print(f"  新增项: {simple_stats['insert']} → {two_stage_stats['insert']} ({insert_diff:+d})")
    print(f"  多对多匹配: {results['simple']['many_to_many']} → {results['two_stage']['many_to_many']}")

    # 计算吞吐量（句子/秒）
    simple_throughput = len(sentences_a) / simple_avg if simple_avg > 0 else 0
    two_stage_throughput = len(sentences_a) / two_stage_avg if two_stage_avg > 0 else 0

    print(f"\n吞吐量:")
    print(f"  单阶段算法: {simple_throughput:.1f} 句子/秒")
    print(f"  两阶段算法: {two_stage_throughput:.1f} 句子/秒")

    # 总结
    print("\n" + "="*70)
    print("总结")
    print("="*70)

    if match_rate_diff > 0:
        print(f"[+] 两阶段算法匹配率更高 (+{match_rate_diff:.2f}%)")
    elif match_rate_diff < 0:
        print(f"[-] 两阶段算法匹配率较低 ({match_rate_diff:.2f}%)")
    else:
        print(f"[=] 两种算法匹配率相同")

    if time_ratio < 1.5:
        print(f"[+] 两阶段算法耗时可接受 ({time_ratio:.2f}x)")
    elif time_ratio < 2.0:
        print(f"[~] 两阶段算法耗时略高 ({time_ratio:.2f}x)")
    else:
        print(f"[-] 两阶段算法耗时较高 ({time_ratio:.2f}x)")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='性能测试：对比单阶段和两阶段对齐算法'
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
        default='performance_test',
        help='输出文件前缀'
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=3,
        help='运行次数（用于计算平均耗时，默认3次）'
    )

    args = parser.parse_args()

    # 运行性能测试
    results = test_algorithm_performance(
        args.text_a,
        args.text_b,
        iterations=args.iterations
    )

    # 保存结果
    output_data = {
        'simple': {
            'times': results['simple']['times'],
            'avg_time': results['simple']['avg_time'],
            'min_time': results['simple']['min_time'],
            'max_time': results['simple']['max_time'],
            'stats': results['simple']['stats'],
            'many_to_many': results['simple']['many_to_many']
        },
        'two_stage': {
            'times': results['two_stage']['times'],
            'avg_time': results['two_stage']['avg_time'],
            'min_time': results['two_stage']['min_time'],
            'max_time': results['two_stage']['max_time'],
            'stats': results['two_stage']['stats'],
            'many_to_many': results['two_stage']['many_to_many']
        }
    }

    json_path = f"{args.output}.json"
    print(f"\n保存性能测试结果: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n性能测试完成！")


if __name__ == '__main__':
    main()


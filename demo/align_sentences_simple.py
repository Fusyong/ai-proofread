"""
简单快速的句子对齐脚本（基于锚点算法）

用法:
    python demo/align_sentences_simple.py -a demo/example/a.md -b demo/example/b.md
"""

from pathlib import Path
import argparse
import json
import csv
import time
from typing import List, Dict

from src.sentence_aligner_simple import (
    align_texts_anchor,
    get_alignment_statistics
)
from src.splitter import split_chinese_sentences


def save_json_report(alignment: List[Dict], output_path: str):
    """保存JSON格式的对齐报告"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(alignment, f, ensure_ascii=False, indent=2)


def save_csv_summary(alignment: List[Dict], output_path: str):
    """保存CSV格式的摘要报告"""
    stats = get_alignment_statistics(alignment)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['类型', '数量', '占比'])
        total = stats['total']
        for key in ['match', 'delete', 'insert']:
            count = stats[key]
            percentage = f"{count / total * 100:.2f}%" if total > 0 else "0%"
            writer.writerow([key, count, percentage])
        writer.writerow(['总计', total, '100%'])


def save_html_report(
    alignment: List[Dict],
    output_path: str,
    title_a: str = "",
    title_b: str = "",
    algorithm_name: str = "锚点算法",
    threshold: float = 0.6,
    ngram_size: int = 1,
    runtime: float = 0.0
):
    """生成HTML格式的可视化报告"""
    # 如果文件名为空，使用默认值
    if not title_a:
        title_a = "原文"
    if not title_b:
        title_b = "校对后"

    html_lines = []

    # HTML头部（注意：CSS中的花括号需要转义为{{和}}）
    html_lines.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>句子对齐报告（锚点算法）</title>
    <style>
        body {{
            font-family: "SimSun", "宋体", serif;
            font-size: 14px;
            line-height: 1.6;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .stats {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .stats th, .stats td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .stats th {{
            background-color: #3498db;
            color: white;
        }}
        .alignment-results {{
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .alignment-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .alignment-table th {{
            background-color: #3498db;
            color: white;
            padding: 10px;
            text-align: left;
            border: 1px solid #2980b9;
        }}
        .alignment-table td {{
            padding: 10px;
            border: 1px solid #ddd;
            vertical-align: top;
        }}
        .alignment-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .alignment-table tr:hover {{
            background-color: #f0f0f0;
        }}
        .alignment-table tr.match {{
            border-left: 4px solid #27ae60;
        }}
        .alignment-table tr.delete {{
            border-left: 4px solid #e74c3c;
        }}
        .alignment-table tr.insert {{
            border-left: 4px solid #3498db;
        }}
        .col-index {{
            width: 5%;
            text-align: center;
            font-weight: bold;
        }}
        .col-type {{
            width: 5%;
            font-weight: bold;
        }}
        .col-similarity {{
            width: 5%;
            text-align: center;
        }}
        .col-sentence-a {{
            width: 42.5%;
        }}
        .col-sentence-b {{
            width: 42.5%;
        }}
        .item-header {{
            font-weight: bold;
        }}
        .similarity {{
            font-size: 12px;
            color: #7f8c8d;
        }}
        .sentence-a {{
            color: #c0392b;
        }}
        .sentence-b {{
            color: #27ae60;
        }}
        .index {{
            font-size: 12px;
            color: #95a5a6;
            margin-right: 8px;
            font-weight: normal;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>句子对齐报告（{algorithm_name}）</h1>
        <p>比较文件 {title_a} 和 {title_b}</p>
        <p style="font-size: 13px; margin-top: 10px; opacity: 0.9;">
            相似度算法: {algorithm_name} | 阈值: {threshold:.2f} | N-gram大小: {ngram_size} | 运行时间: {runtime:.2f}秒
        </p>
    </div>
""")

    # 统计信息
    stats = get_alignment_statistics(alignment)
    html_lines.append("""    <div class="stats">
        <h2>统计信息</h2>
        <table>
            <tr>
                <th>类型</th>
                <th>数量</th>
                <th>占比</th>
            </tr>""")

    total = stats['total']
    for key in ['match', 'delete', 'insert']:
        count = stats[key]
        percentage = f"{count / total * 100:.2f}%" if total > 0 else "0%"
        html_lines.append(f"""
            <tr>
                <td>{key}</td>
                <td>{count}</td>
                <td>{percentage}</td>
            </tr>""")

    html_lines.append(f"""
            <tr>
                <td><strong>总计</strong></td>
                <td><strong>{total}</strong></td>
                <td><strong>100%</strong></td>
            </tr>
        </table>
    </div>""")

    # 对齐结果
    html_lines.append(f"""    <div class="alignment-results">
        <h2>对齐结果</h2>
        <table class="alignment-table">
            <thead>
                <tr>
                    <th class="col-index">序号</th>
                    <th class="col-type">类型</th>
                    <th class="col-similarity">相似度</th>
                    <th class="col-sentence-a">{title_a}</th>
                    <th class="col-sentence-b">{title_b}</th>
                </tr>
            </thead>
            <tbody>""")

    for idx, item in enumerate(alignment, 1):
        item_type = item['type']

        # 构建相似度文本
        similarity_text = ""
        if item.get('similarity'):
            similarity_text = f'{item["similarity"]:.2f}'

        # 构建原文句子
        sentence_a_text = ""
        if item['a']:
            # 使用a_indices数组，如果有多个索引则显示范围
            if item.get('a_indices'):
                a_indices = item['a_indices']
                if len(a_indices) == 1:
                    a_idx_str = str(a_indices[0])
                else:
                    a_idx_str = f"{a_indices[0]}-{a_indices[-1]}"
            else:
                a_idx_str = item.get('a_index', '?')
            sentence_a_text = f'<span class="index">[{a_idx_str}]</span><span class="sentence-a">{item["a"]}</span>'

        # 构建校对后句子
        sentence_b_text = ""
        if item['b']:
            # 使用b_indices数组，如果有多个索引则显示范围
            if item.get('b_indices'):
                b_indices = item['b_indices']
                if len(b_indices) == 1:
                    b_idx_str = str(b_indices[0])
                else:
                    b_idx_str = f"{b_indices[0]}-{b_indices[-1]}"
            else:
                b_idx_str = item.get('b_index', '?')
            sentence_b_text = f'<span class="index">[{b_idx_str}]</span><span class="sentence-b">{item["b"]}</span>'

        html_lines.append(f"""
            <tr class="{item_type}">
                <td class="col-index">{idx}</td>
                <td class="col-type"><span class="item-header">{item_type.upper()}</span></td>
                <td class="col-similarity"><span class="similarity">{similarity_text}</span></td>
                <td class="col-sentence-a">{sentence_a_text}</td>
                <td class="col-sentence-b">{sentence_b_text}</td>
            </tr>""")

    html_lines.append("""
            </tbody>
        </table>
    </div>
</body>
</html>""")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))


def main():
    parser = argparse.ArgumentParser(
        description='使用锚点算法对齐两个文本的句子（快速版本）'
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
        default='alignment_result_simple',
        help='输出文件前缀（不含扩展名），默认: alignment_result_simple'
    )
    parser.add_argument(
        '--window-size',
        type=int,
        default=10,
        help='搜索窗口大小（锚点左右各N个句子），默认: 10'
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
        default=1,
        help='n-gram大小，默认: 1'
    )
    parser.add_argument(
        '--offset',
        type=int,
        default=1,
        help='锚点偏移量，默认: 1'
    )
    parser.add_argument(
        '--max-window-expansion',
        type=int,
        default=3,
        help='最大窗口扩展倍数（用于处理大段落变化），默认: 3'
    )
    parser.add_argument(
        '--consecutive-fail-threshold',
        type=int,
        default=3,
        help='连续失败阈值（超过此值触发窗口扩展），默认: 3'
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

    # 对齐句子
    print("正在对齐句子（锚点算法）...")
    sentences_a_count = len([s for s in split_chinese_sentences(text_a, not args.no_formatting) if s.strip()])
    sentences_b_count = len([s for s in split_chinese_sentences(text_b, not args.no_formatting) if s.strip()])
    print(f"  原文句子数: {sentences_a_count}")
    print(f"  校对后句子数: {sentences_b_count}")

    alignment = align_texts_anchor(
        text_a,
        text_b,
        preserve_formatting=not args.no_formatting,
        window_size=args.window_size,
        similarity_threshold=args.threshold,
        ngram_size=args.ngram,
        offset=args.offset,
        max_window_expansion=args.max_window_expansion,
        consecutive_fail_threshold=args.consecutive_fail_threshold
    )

    # 统计信息
    stats = get_alignment_statistics(alignment)
    print("\n对齐完成！统计信息:")
    print(f"  总计: {stats['total']}")
    print(f"  匹配: {stats['match']}")
    print(f"  删除: {stats['delete']}")
    print(f"  新增: {stats['insert']}")

    # 保存结果
    output_base = args.output

    json_path = f"{output_base}.json"
    print(f"\n保存JSON报告: {json_path}")
    save_json_report(alignment, json_path)

    csv_path = f"{output_base}.csv"
    print(f"保存CSV摘要: {csv_path}")
    save_csv_summary(alignment, csv_path)

    html_path = f"{output_base}.html"
    print(f"保存HTML报告: {html_path}")
    title_a = Path(args.text_a).name
    title_b = Path(args.text_b).name

    # 计算运行时间
    runtime = time.time() - start_time

    save_html_report(
        alignment,
        html_path,
        title_a,
        title_b,
        algorithm_name="锚点算法",
        threshold=args.threshold,
        ngram_size=args.ngram,
        runtime=runtime
    )

    print(f"\n所有报告已保存到: {output_base}.*")


if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"运行时间: {end_time - start_time:.2f}秒")


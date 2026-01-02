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
import html
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
        .filter-controls {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border: 1px solid #bdc3c7;
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: nowrap;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 0 1 auto;
        }}
        .filter-label {{
            font-weight: bold;
            margin: 0;
            display: inline-block;
            color: #2c3e50;
            font-size: 13px;
            white-space: nowrap;
        }}
        .filter-buttons {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 6px 12px;
            border: 2px solid #3498db;
            background-color: white;
            color: #3498db;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{
            background-color: #e8f4f8;
        }}
        .filter-btn.active {{
            background-color: #3498db;
            color: white;
        }}
        .filter-input-group {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .filter-input {{
            padding: 6px 10px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            font-size: 13px;
            width: 80px;
        }}
        .filter-search {{
            padding: 6px 10px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            font-size: 13px;
            width: 200px;
        }}
        .filter-reset {{
            padding: 6px 15px;
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }}
        .filter-reset:hover {{
            background-color: #c0392b;
        }}
        .filter-stats {{
            font-size: 13px;
            color: #7f8c8d;
            margin-top: 10px;
            margin-bottom: 10px;
        }}
        .alignment-table tr.hidden {{
            display: none;
        }}
        .compare-btn {{
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.2s;
            width: 100%;
        }}
        .alignment-table tr:hover .compare-btn {{
            opacity: 1;
        }}
        .compare-btn:hover {{
            background-color: #2980b9;
        }}
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 5px;
            width: 90%;
            max-width: 1000px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }}
        .modal-title {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .close-btn {{
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 15px;
            cursor: pointer;
            font-size: 14px;
        }}
        .close-btn:hover {{
            background-color: #c0392b;
        }}
        .diff-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        .diff-panel {{
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 15px;
            background-color: #f9f9f9;
        }}
        .diff-panel-title {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .diff-content {{
            font-family: "SimSun", "宋体" !important;
            font-size: 14px !important;
            line-height: 1.5 !important;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .diff-content span {{
            display: inline;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        .diff-added {{
            background-color: #d5f4e6;
            color: #27ae60;
        }}
        .diff-removed {{
            background-color: #fadbd8;
            color: #c0392b;
        }}
        .diff-common {{
            color: #34495e;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/diff@7.0.0/dist/diff.min.js"></script>
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

    # 对齐结果
    html_lines.append(f"""    <div class="alignment-results">
        <h2>对齐结果</h2>
        <div class="filter-controls">
            <div class="filter-group">
                <label class="filter-label">类型筛选：</label>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-type="all" onclick="filterByType('all')">全部</button>
                    <button class="filter-btn active" data-type="match" onclick="filterByType('match')">MATCH</button>
                    <button class="filter-btn active" data-type="delete" onclick="filterByType('delete')">DELETE</button>
                    <button class="filter-btn active" data-type="insert" onclick="filterByType('insert')">INSERT</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">相似度范围：</label>
                <div class="filter-input-group">
                    <input type="number" class="filter-input" id="minSimilarity" placeholder="最小值" min="0" max="1" step="0.01" oninput="applyFilters()">
                    <span>至</span>
                    <input type="number" class="filter-input" id="maxSimilarity" placeholder="最大值" min="0" max="1" step="0.01" oninput="applyFilters()">
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">文本搜索：</label>
                <div class="filter-input-group">
                    <input type="text" class="filter-search" id="searchText" placeholder="在原文或校对后文本中搜索..." oninput="applyFilters()">
                    <button class="filter-reset" onclick="resetFilters()">重置筛选</button>
                </div>
            </div>
        </div>
        <div class="filter-stats" id="filterStats"></div>
        <table class="alignment-table">
            <thead>
                <tr>
                    <th class="col-index">序号</th>
                    <th class="col-type">类型</th>
                    <th class="col-similarity">相似度</th>
                    <th class="col-sentence-a">{title_a}</th>
                    <th class="col-sentence-b">{title_b}</th>
                    <th style="width: 50px;"></th>
                </tr>
            </thead>
            <tbody>""")

    for idx, item in enumerate(alignment, 1):
        item_type = item['type']

        # 获取相似度数值（用于筛选）
        similarity_value = item.get('similarity')
        if similarity_value is None:
            similarity_value = 0.0
        else:
            similarity_value = float(similarity_value)

        # 构建相似度文本
        similarity_text = ""
        if similarity_value:
            similarity_text = f'{similarity_value:.2f}'

        # 获取文本内容（用于搜索，需要转义HTML特殊字符）
        text_a_raw = item.get('a') or ''
        text_b_raw = item.get('b') or ''
        text_a_escaped = html.escape(str(text_a_raw))
        text_b_escaped = html.escape(str(text_b_raw))

        # 构建原文句子
        sentence_a_text = ""
        if item['a']:
            # 使用a_indices数组，如果有多个索引则显示范围
            if item.get('a_indices'):
                a_indices = item['a_indices']
                if len(a_indices) == 1:
                    a_idx_str = str(a_indices[0] + 1)
                else:
                    a_idx_str = f"{a_indices[0] + 1}-{a_indices[-1] + 1}"
            else:
                a_index = item.get('a_index', '?')
                if isinstance(a_index, (int, float)):
                    a_idx_str = str(int(a_index) + 1)
                else:
                    a_idx_str = str(a_index)
            sentence_a_text = f'<span class="index">[{a_idx_str}]</span><span class="sentence-a">{item["a"]}</span>'

        # 构建校对后句子
        sentence_b_text = ""
        if item['b']:
            # 使用b_indices数组，如果有多个索引则显示范围
            if item.get('b_indices'):
                b_indices = item['b_indices']
                if len(b_indices) == 1:
                    b_idx_str = str(b_indices[0] + 1)
                else:
                    b_idx_str = f"{b_indices[0] + 1}-{b_indices[-1] + 1}"
            else:
                b_index = item.get('b_index', '?')
                if isinstance(b_index, (int, float)):
                    b_idx_str = str(int(b_index) + 1)
                else:
                    b_idx_str = str(b_index)
            sentence_b_text = f'<span class="index">[{b_idx_str}]</span><span class="sentence-b">{item["b"]}</span>'

        html_lines.append(f"""
            <tr class="{item_type}" data-type="{item_type}" data-similarity="{similarity_value:.4f}" data-text-a="{text_a_escaped}" data-text-b="{text_b_escaped}" data-row-idx="{idx}">
                <td class="col-index">{idx}</td>
                <td class="col-type"><span class="item-header">{item_type.upper()}</span></td>
                <td class="col-similarity"><span class="similarity">{similarity_text}</span></td>
                <td class="col-sentence-a">{sentence_a_text}</td>
                <td class="col-sentence-b">{sentence_b_text}</td>
                <td style="position: relative; width: 50px; padding: 0;">
                    <button class="compare-btn" onclick="showDiffForRow(this)" title="比较差异">🔍</button>
                </td>
            </tr>""")

    html_lines.append("""
            </tbody>
        </table>
    </div>

    <!-- 差异比较弹窗 -->
    <div id="diffModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">文本差异比较</div>
                <button class="close-btn" onclick="closeDiffModal()">关闭</button>
            </div>
            <div class="diff-container">
                <div class="diff-panel">
                    <div class="diff-panel-title">原文</div>
                    <div id="diffOriginal" class="diff-content"></div>
                </div>
                <div class="diff-panel">
                    <div class="diff-panel-title">校对后</div>
                    <div id="diffModified" class="diff-content"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 类型筛选状态
        const typeFilters = {
            'all': true,
            'match': true,
            'delete': true,
            'insert': true
        };

        // 类型筛选函数
        function filterByType(type) {
            const btn = document.querySelector(`[data-type="${type}"]`);
            typeFilters[type] = !typeFilters[type];

            if (type === 'all') {
                // 全部按钮：切换所有类型
                const allActive = !typeFilters['all'];
                typeFilters['match'] = allActive;
                typeFilters['delete'] = allActive;
                typeFilters['insert'] = allActive;

                // 更新所有按钮状态
                document.querySelectorAll('.filter-btn[data-type]').forEach(b => {
                    if (b.dataset.type === 'all') {
                        b.classList.toggle('active', allActive);
                    } else {
                        b.classList.toggle('active', allActive);
                    }
                });
            } else {
                // 单个类型按钮
                btn.classList.toggle('active', typeFilters[type]);

                // 更新"全部"按钮状态
                const allActive = typeFilters['match'] && typeFilters['delete'] && typeFilters['insert'];
                const allBtn = document.querySelector('[data-type="all"]');
                allBtn.classList.toggle('active', allActive);
                typeFilters['all'] = allActive;
            }

            applyFilters();
        }

        // 应用所有筛选条件
        function applyFilters() {
            const rows = document.querySelectorAll('.alignment-table tbody tr');
            const minSimilarity = parseFloat(document.getElementById('minSimilarity').value) || 0;
            const maxSimilarity = parseFloat(document.getElementById('maxSimilarity').value) || 1;
            const searchText = document.getElementById('searchText').value.toLowerCase().trim();

            let visibleCount = 0;

            rows.forEach(row => {
                // 类型筛选
                const rowType = row.dataset.type;
                const typeMatch = typeFilters[rowType];

                // 相似度筛选
                const similarity = parseFloat(row.dataset.similarity) || 0;
                const similarityMatch = similarity >= minSimilarity && similarity <= maxSimilarity;

                // 文本搜索
                const textA = (row.dataset.textA || '').toLowerCase();
                const textB = (row.dataset.textB || '').toLowerCase();
                const textMatch = !searchText || textA.includes(searchText) || textB.includes(searchText);

                // 综合判断
                const shouldShow = typeMatch && similarityMatch && textMatch;

                if (shouldShow) {
                    row.classList.remove('hidden');
                    visibleCount++;
                } else {
                    row.classList.add('hidden');
                }
            });

            // 更新统计信息
            updateFilterStats(visibleCount, rows.length);
        }

        // 更新筛选统计信息
        function updateFilterStats(visible, total) {
            const statsEl = document.getElementById('filterStats');
            if (visible === total) {
                statsEl.textContent = `显示全部 ${total} 条结果`;
            } else {
                statsEl.textContent = `显示 ${visible} / ${total} 条结果`;
            }
        }

        // 重置所有筛选
        function resetFilters() {
            // 重置类型筛选
            typeFilters['all'] = true;
            typeFilters['match'] = true;
            typeFilters['delete'] = true;
            typeFilters['insert'] = true;

            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.add('active');
            });

            // 重置相似度范围
            document.getElementById('minSimilarity').value = '';
            document.getElementById('maxSimilarity').value = '';

            // 重置文本搜索
            document.getElementById('searchText').value = '';

            // 应用筛选
            applyFilters();
        }

        // 显示差异比较弹窗
        function showDiffForRow(btn) {
            const row = btn.closest('tr');
            const textA = row.dataset.textA || '';
            const textB = row.dataset.textB || '';
            const rowIdx = row.dataset.rowIdx || '';

            showDiff(rowIdx, textA, textB);
        }

        function showDiff(idx, textA, textB) {
            const modal = document.getElementById('diffModal');
            const originalEl = document.getElementById('diffOriginal');
            const modifiedEl = document.getElementById('diffModified');

            // 使用jsdiff比较文本
            if (typeof Diff !== 'undefined') {
                // 使用Intl.Segmenter处理中文分词（如果支持）
                let segmenter = null;
                if (typeof Intl !== 'undefined' && Intl.Segmenter) {
                    try {
                        segmenter = new Intl.Segmenter('zh', { granularity: 'word' });
                    } catch (e) {
                        // 如果不支持，使用默认方式
                    }
                }

                // 使用diffWordsWithSpace进行词级别的比较（更适合中文）
                const diff = segmenter
                    ? Diff.diffWordsWithSpace(textA, textB, segmenter)
                    : Diff.diffWords(textA, textB);

                // 渲染差异（合并显示，参考参考文件的样式）
                let displayHtml = '';

                diff.forEach(part => {
                    const escapedValue = escapeHtml(part.value);
                    let span = '<span';

                    if (part.added) {
                        span += ' style="color: green; text-decoration: underline 2px;">';
                    } else if (part.removed) {
                        span += ' style="color: red; text-decoration: dotted underline 2px;">';
                    } else {
                        span += ' style="color: black;">';
                    }

                    span += escapedValue + '</span>';
                    displayHtml += span;
                });

                // 在原文面板显示删除的内容，在校对后面板显示新增的内容
                let originalHtml = '';
                let modifiedHtml = '';

                diff.forEach(part => {
                    const escapedValue = escapeHtml(part.value);
                    if (part.removed) {
                        originalHtml += '<span class="diff-removed">' + escapedValue + '</span>';
                    } else if (!part.added) {
                        originalHtml += '<span class="diff-common">' + escapedValue + '</span>';
                    }

                    if (part.added) {
                        modifiedHtml += '<span class="diff-added">' + escapedValue + '</span>';
                    } else if (!part.removed) {
                        modifiedHtml += '<span class="diff-common">' + escapedValue + '</span>';
                    }
                });

                originalEl.innerHTML = originalHtml || '<span class="diff-common">（空）</span>';
                modifiedEl.innerHTML = modifiedHtml || '<span class="diff-common">（空）</span>';
            } else {
                // 如果jsdiff未加载，显示原始文本
                originalEl.textContent = textA || '（空）';
                modifiedEl.textContent = textB || '（空）';
            }

            modal.style.display = 'block';
        }

        // 关闭弹窗
        function closeDiffModal() {
            document.getElementById('diffModal').style.display = 'none';
        }

        // HTML转义函数
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 点击弹窗外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('diffModal');
            if (event.target === modal) {
                closeDiffModal();
            }
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            applyFilters();
        });
    </script>
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


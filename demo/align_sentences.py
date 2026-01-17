"""
简单快速的句子对齐脚本（基于锚点算法）

用法:
    python demo/align_sentences.py -a demo/example/a.md -b demo/example/b.md
"""

from pathlib import Path
import argparse
import json
import csv
import time
import html
from typing import List, Dict

from src.sentence_aligner import (
    align_sentences_anchor,
    get_alignment_statistics
)
from src.splitter import split_chinese_sentences, split_chinese_sentences_with_line_numbers


def split_sentences_with_line_numbers(text: str, preserve_formatting: bool = True) -> List[tuple]:
    """
    切分句子并跟踪每个句子在原始文本中的行号

    使用 splitter 模块的优化版本，在切分时直接跟踪行号

    Args:
        text: 要切分的文本
        preserve_formatting: 是否保留格式

    Returns:
        List[tuple]: [(sentence, start_line), ...] 列表，start_line是句子开头所在的行号（从1开始）
        注意：函数返回 (sentence, start_line, end_line)，但这里只使用 start_line
    """
    # 直接使用 splitter 模块的优化函数
    result = split_chinese_sentences_with_line_numbers(text, preserve_formatting)
    # 只返回 (sentence, start_line)，因为对齐时只需要首行行号
    return [(sentence, start_line) for sentence, start_line, _ in result]


def align_texts_anchor_with_line_numbers(
    text_a: str,
    text_b: str,
    preserve_formatting: bool = True,
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3
) -> List[Dict]:
    """
    对齐两个文本并添加行号信息

    Args:
        参数与align_texts_anchor相同

    Returns:
        对齐结果列表，每个元素包含行号信息：
        - a_line_number: 原文句子所在的行号
        - b_line_number: 校对后句子所在的行号（如果有）
        - a_line_numbers: 原文句子所在的行号列表（如果合并了多个句子，取首行）
        - b_line_numbers: 校对后句子所在的行号列表（如果合并了多个句子，取首行）
    """
    # 切分句子并获取行号
    sentences_a_with_lines = split_sentences_with_line_numbers(text_a, preserve_formatting)
    sentences_b_with_lines = split_sentences_with_line_numbers(text_b, preserve_formatting)

    # 提取句子列表
    sentences_a = [s for s, _ in sentences_a_with_lines]
    sentences_b = [s for s, _ in sentences_b_with_lines]

    # 创建行号映射
    line_numbers_a = [line_num for _, line_num in sentences_a_with_lines]
    line_numbers_b = [line_num for _, line_num in sentences_b_with_lines]

    # 对齐句子
    alignment = align_sentences_anchor(
        sentences_a,
        sentences_b,
        window_size=window_size,
        similarity_threshold=similarity_threshold,
        ngram_size=ngram_size,
        offset=offset,
        max_window_expansion=max_window_expansion,
        consecutive_fail_threshold=consecutive_fail_threshold
    )

    # 为对齐结果添加行号信息
    for item in alignment:
        # 处理原文行号
        if 'a_indices' in item:
            # 多个句子合并，取首行的行号
            a_indices = item['a_indices']
            if a_indices:
                item['a_line_numbers'] = [line_numbers_a[i] for i in a_indices]
                item['a_line_number'] = line_numbers_a[a_indices[0]]  # 首行
        elif 'a_index' in item and item['a_index'] is not None:
            a_idx = item['a_index']
            item['a_line_number'] = line_numbers_a[a_idx]
            item['a_line_numbers'] = [line_numbers_a[a_idx]]

        # 处理校对后行号
        if 'b_indices' in item:
            # 多个句子合并，取首行的行号
            b_indices = item['b_indices']
            if b_indices:
                item['b_line_numbers'] = [line_numbers_b[i] for i in b_indices]
                item['b_line_number'] = line_numbers_b[b_indices[0]]  # 首行
        elif 'b_index' in item and item['b_index'] is not None:
            b_idx = item['b_index']
            item['b_line_number'] = line_numbers_b[b_idx]
            item['b_line_numbers'] = [line_numbers_b[b_idx]]

    return alignment


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
        .alignment-table tr.match.partial-match {{
            border-left: 4px solid #f39c12;
        }}
        .alignment-table tr.movein {{
            border-left: 4px solid #f39c12;
        }}
        .alignment-table tr.moveout {{
            border-left: 4px solid #f39c12;
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
            color: black;
        }}
        .sentence-b {{
            color: black;
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
        .col-action {{
            width: 5%;
            text-align: center;
            position: relative;
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
        }}
        .header-compare-btn {{
            opacity: 1 !important;
        }}
        .alignment-table tr:hover .compare-btn {{
            opacity: 1;
        }}
        .compare-btn:hover {{
            background-color: #2980b9;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/diff@7.0.0/dist/diff.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>句子对齐</h1>
        <p>对齐文件 {title_a} 和 {title_b}</p>
        <p style="font-size: 13px; margin-top: 10px; opacity: 0.9;">
            相似度算法: {algorithm_name} | 阈值: {threshold:.2f} | N-gram大小: {ngram_size} | 运行时间: {runtime:.2f}秒
        </p>
    </div>
""")

    # 对齐结果
    html_lines.append(f"""    <div class="alignment-results">
        <div class="filter-controls">
            <div class="filter-group">
                <label class="filter-label">类型筛选：</label>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-type="all" onclick="filterByType('all')">全部</button>
                    <button class="filter-btn active" data-type="match" onclick="filterByType('match')">MATCH</button>
                    <button class="filter-btn active" data-type="movein" onclick="filterByType('movein')">MOVEIN</button>
                    <button class="filter-btn active" data-type="moveout" onclick="filterByType('moveout')">MOVEOUT</button>
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
                    <input type="text" class="filter-search" id="searchText" placeholder="在左右文本中搜索..." oninput="applyFilters()">
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
                    <th class="col-sentence-a">[句ID, 行ID]{title_a}</th>
                    <th class="col-sentence-b">[句ID, 行ID]{title_b}</th>
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

        # 判断是否需要显示差异（非完全匹配的行，包括movein和moveout）
        needs_diff = (item_type == 'match' and similarity_value < 1.0) or item_type in ['movein', 'moveout']

        # 获取文本内容（用于搜索，需要转义HTML特殊字符）
        text_a_raw = item.get('a') or ''
        text_b_raw = item.get('b') or ''
        text_a_escaped = html.escape(str(text_a_raw))
        text_b_escaped = html.escape(str(text_b_raw))

        # 构建原文句子
        sentence_a_text = ""
        if item['a']:
            # 获取句子索引
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

            # 获取行号（如果合并了多个句子，取首行的行号）
            a_line_num = item.get('a_line_number', '?')
            if isinstance(a_line_num, (int, float)):
                a_line_str = str(int(a_line_num))
            else:
                a_line_str = str(a_line_num)

            sentence_a_text = f'<span class="index">[{a_idx_str}, {a_line_str}]</span><span class="sentence-a">{item["a"]}</span>'

        # 构建校对后句子
        sentence_b_text = ""
        if item['b']:
            # 获取句子索引
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

            # 获取行号（如果合并了多个句子，取首行的行号）
            b_line_num = item.get('b_line_number', '?')
            if isinstance(b_line_num, (int, float)):
                b_line_str = str(int(b_line_num))
            else:
                b_line_str = str(b_line_num)

            sentence_b_text = f'<span class="index">[{b_idx_str}, {b_line_str}]</span><span class="sentence-b">{item["b"]}</span>'

        # 为需要比较的行添加标记
        needs_diff_attr = 'data-needs-diff="true"' if needs_diff else ''
        # 为相似度不足1的match行添加partial-match类（用于显示黄色边框）
        partial_match_class = ' partial-match' if (item_type == 'match' and similarity_value < 1.0) else ''
        html_lines.append(f"""
            <tr class="{item_type}{partial_match_class}" data-type="{item_type}" data-similarity="{similarity_value:.4f}" data-text-a="{text_a_escaped}" data-text-b="{text_b_escaped}" data-row-idx="{idx}" data-diff-mode="false" {needs_diff_attr}>
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

    <script>
        // 类型筛选状态
        const typeFilters = {
            'all': true,
            'match': true,
            'movein': true,
            'moveout': true,
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
                typeFilters['movein'] = allActive;
                typeFilters['moveout'] = allActive;
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
                const allActive = typeFilters['match'] && typeFilters['movein'] && typeFilters['moveout'] && typeFilters['delete'] && typeFilters['insert'];
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

            // 筛选后重新初始化渲染队列
            renderedRows.clear();
            updateRenderQueue();
            initialRender();
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
            typeFilters['movein'] = true;
            typeFilters['moveout'] = true;
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

        // 懒加载渲染配置
        const RENDER_BATCH_SIZE = 10; // 每批渲染的行数
        const VIEWPORT_BUFFER = 100; // 视口上下缓冲区（像素）
        const INITIAL_RENDER_BUFFER = 2000; // 初始渲染缓冲区（像素）

        // 渲染队列和状态
        let renderQueue = [];
        let isRendering = false;
        let renderedRows = new Set();

        // 检查元素是否在视口内（带缓冲区）
        function isInViewportWithBuffer(element, buffer = VIEWPORT_BUFFER) {
            const rect = element.getBoundingClientRect();
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
            return (
                rect.top >= -buffer &&
                rect.bottom <= viewportHeight + buffer
            );
        }

        // 计算行到视口的距离（用于优先级排序）
        function getDistanceToViewport(row) {
            const rect = row.getBoundingClientRect();
            const viewportTop = window.pageYOffset || document.documentElement.scrollTop;
            const viewportBottom = viewportTop + (window.innerHeight || document.documentElement.clientHeight);
            const rowTop = viewportTop + rect.top;
            const rowBottom = viewportTop + rect.bottom;

            if (rowBottom < viewportTop) {
                return viewportTop - rowBottom; // 在视口上方
            } else if (rowTop > viewportBottom) {
                return rowTop - viewportBottom; // 在视口下方
            } else {
                return 0; // 在视口内
            }
        }

        // 更新渲染队列（按优先级排序）
        function updateRenderQueue() {
            const allRows = document.querySelectorAll('.alignment-table tbody tr[data-needs-diff="true"]:not(.hidden)');
            renderQueue = [];

            allRows.forEach(row => {
                if (!renderedRows.has(row)) {
                    const distance = getDistanceToViewport(row);
                    renderQueue.push({ row: row, distance: distance });
                }
            });

            // 按距离排序：距离越近优先级越高
            renderQueue.sort((a, b) => a.distance - b.distance);
        }

        // 渲染单行的差异显示
        function renderDiffForRow(row) {
            const textA = row.dataset.textA || '';
            const textB = row.dataset.textB || '';
            const cellA = row.querySelector('.col-sentence-a');
            const cellB = row.querySelector('.col-sentence-b');

            if (!cellA || !cellB) return false;

            // 保存原始内容（如果还没有保存）
            if (row._originalA === undefined || row._originalB === undefined) {
                row._originalA = cellA.innerHTML;
                row._originalB = cellB.innerHTML;
            }

            // 显示差异
            if (typeof Diff !== 'undefined') {
                let segmenter = null;
                if (typeof Intl !== 'undefined' && Intl.Segmenter) {
                    try {
                        segmenter = new Intl.Segmenter('zh', { granularity: 'word' });
                    } catch (e) {
                        // 如果不支持，使用默认方式
                    }
                }

                const diff = segmenter
                    ? Diff.diffWordsWithSpace(textA, textB, segmenter)
                    : Diff.diffWords(textA, textB);

                let originalHtml = '';
                let modifiedHtml = '';

                diff.forEach(part => {
                    const escapedValue = escapeHtml(part.value);

                    if (part.removed) {
                        originalHtml += '<span style="color: red; text-decoration: dotted underline 2px;">' + escapedValue + '</span>';
                    } else if (!part.added) {
                        originalHtml += '<span style="color: black;">' + escapedValue + '</span>';
                    }

                    if (part.added) {
                        modifiedHtml += '<span style="color: green; text-decoration: underline 2px;">' + escapedValue + '</span>';
                    } else if (!part.removed) {
                        modifiedHtml += '<span style="color: black;">' + escapedValue + '</span>';
                    }
                });

                // 获取索引元素
                const indexA = cellA.querySelector('.index');
                const indexB = cellB.querySelector('.index');
                const indexAHtml = indexA ? indexA.outerHTML : '';
                const indexBHtml = indexB ? indexB.outerHTML : '';

                // 保留索引号码
                cellA.innerHTML = indexAHtml + (originalHtml || '');
                cellB.innerHTML = indexBHtml + (modifiedHtml || '');
            } else {
                // 如果jsdiff不可用，显示原始文本
                const indexA = cellA.querySelector('.index');
                const indexB = cellB.querySelector('.index');
                const indexAHtml = indexA ? indexA.outerHTML : '';
                const indexBHtml = indexB ? indexB.outerHTML : '';
                cellA.innerHTML = indexAHtml + escapeHtml(textA);
                cellB.innerHTML = indexBHtml + escapeHtml(textB);
            }

            row.dataset.diffMode = 'true';
            return true;
        }

        // 批量渲染函数
        function renderBatch() {
            if (isRendering || renderQueue.length === 0) {
                return;
            }

            isRendering = true;
            let rendered = 0;

            // 优先渲染视口内的行
            const viewportRows = renderQueue.filter(item =>
                isInViewportWithBuffer(item.row, VIEWPORT_BUFFER)
            );

            // 先渲染视口内的行
            const rowsToRender = viewportRows.length > 0
                ? viewportRows.slice(0, RENDER_BATCH_SIZE)
                : renderQueue.slice(0, RENDER_BATCH_SIZE);

            rowsToRender.forEach(item => {
                if (renderDiffForRow(item.row)) {
                    renderedRows.add(item.row);
                    rendered++;
                }
            });

            // 从队列中移除已渲染的行
            renderQueue = renderQueue.filter(item => !renderedRows.has(item.row));

            isRendering = false;

            // 如果还有待渲染的行，继续渲染
            if (renderQueue.length > 0) {
                // 使用 requestAnimationFrame 确保不阻塞UI
                requestAnimationFrame(() => {
                    setTimeout(renderBatch, 0);
                });
            }
        }

        // 初始渲染：优先渲染视口内的行
        function initialRender() {
            updateRenderQueue();

            // 先渲染视口内的行
            const viewportRows = renderQueue.filter(item =>
                isInViewportWithBuffer(item.row, INITIAL_RENDER_BUFFER)
            );

            // 渲染视口内的行
            viewportRows.forEach(item => {
                if (renderDiffForRow(item.row)) {
                    renderedRows.add(item.row);
                }
            });

            // 更新队列
            renderQueue = renderQueue.filter(item => !renderedRows.has(item.row));

            // 继续渲染其余行
            if (renderQueue.length > 0) {
                requestAnimationFrame(() => {
                    setTimeout(renderBatch, 100); // 延迟100ms开始渲染其余行
                });
            }
        }

        // HTML转义函数
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 滚动监听（使用节流优化性能）
        let scrollTimer = null;
        function handleScroll() {
            if (scrollTimer) {
                return;
            }

            scrollTimer = setTimeout(() => {
                // 更新渲染队列（重新计算优先级）
                updateRenderQueue();

                // 优先渲染视口内的行
                renderBatch();

                scrollTimer = null;
            }, 150); // 150ms节流
        }

        // 使用 Intersection Observer 监听行进入视口
        let intersectionObserver = null;
        function setupIntersectionObserver() {
            if (!('IntersectionObserver' in window)) {
                // 如果不支持 Intersection Observer，使用滚动监听
                return;
            }

            intersectionObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const row = entry.target;
                        if (row.dataset.needsDiff === 'true' && !renderedRows.has(row)) {
                            // 行进入视口，如果还没渲染，则渲染
                            updateRenderQueue();
                            renderBatch();
                        }
                    }
                });
            }, {
                root: null,
                rootMargin: `${VIEWPORT_BUFFER}px`,
                threshold: 0
            });

            // 观察所有需要渲染的行
            document.querySelectorAll('.alignment-table tbody tr[data-needs-diff="true"]').forEach(row => {
                intersectionObserver.observe(row);
            });
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            applyFilters();

            // 初始渲染
            initialRender();

            // 设置 Intersection Observer
            setupIntersectionObserver();

            // 添加滚动监听（作为 Intersection Observer 的补充）
            window.addEventListener('scroll', handleScroll, { passive: true });
            let mouseRow = null;
            document.addEventListener('mouseover', function(e) {
                const row = e.target.closest('.alignment-table tbody tr');
                if (row && row !== mouseRow) {
                    mouseRow = row;
                    if (globalDiffMode) {
                        // 更新鼠标所在行及其附近的行
                        const rows = Array.from(document.querySelectorAll('.alignment-table tbody tr:not(.hidden)'));
                        const currentIndex = rows.indexOf(row);
                        const start = Math.max(0, currentIndex - BUFFER_SIZE);
                        const end = Math.min(rows.length, currentIndex + BUFFER_SIZE + 1);

                        for (let i = start; i < end; i++) {
                            const r = rows[i];
                            if (r && r.dataset.diffMode !== 'true') {
                                applyDiffToRow(r, true);
                            }
                        }
                    }
                }
            });
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
        default=2,
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
    sentences_a = [s for s in split_chinese_sentences(text_a) if s.strip()]
    sentences_b = [s for s in split_chinese_sentences(text_b) if s.strip()]
    sentences_a_count = len(sentences_a)
    sentences_b_count = len(sentences_b)
    print(f"  原文句子数: {sentences_a_count}")
    print(f"  校对后句子数: {sentences_b_count}")

    alignment = align_texts_anchor_with_line_numbers(
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
    print(f"  移出: {stats['moveout']}")
    print(f"  移入: {stats['movein']}")

    # 保存结果
    output_base = args.output

    json_path = f"{output_base}.json"
    print(f"\n保存JSON报告: {json_path}")
    save_json_report(alignment, json_path)

    # csv_path = f"{output_base}.csv"
    # print(f"保存CSV摘要: {csv_path}")
    # save_csv_summary(alignment, csv_path)

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


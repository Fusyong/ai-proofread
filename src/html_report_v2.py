"""
新版本HTML报告生成模块

支持多阶段结果显示
"""

import html
from typing import List, Dict
from pathlib import Path


def save_html_report_stage1(
    alignment: List[Dict],
    output_path: str,
    title_a: str = "",
    title_b: str = "",
    runtime: float = 0.0,
    stats: Dict = None
):
    """
    生成阶段一（全等匹配）的HTML报告

    Args:
        alignment: 对齐结果列表（字典格式）
        output_path: 输出文件路径
        title_a: 原文文件名
        title_b: 校对后文件名
        runtime: 运行时间
        stats: 统计信息
    """
    if not title_a:
        title_a = "原文"
    if not title_b:
        title_b = "校对后"

    html_lines = []

    # HTML头部
    html_lines.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>句子对齐报告 - 阶段一（全等匹配）</title>
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
        .stage-badge {{
            background-color: #27ae60;
            color: white;
            padding: 5px 15px;
            border-radius: 3px;
            display: inline-block;
            margin-bottom: 10px;
            font-weight: bold;
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
            border-left: 4px solid #ffd700;
        }}
        .alignment-table tr.match:hover {{
            background-color: rgba(255, 215, 0, 0.3);
        }}
        .alignment-table tr.match.match-exact {{
            border-left: none;
        }}
        .alignment-table tr.match.match-exact:hover {{
            background-color: #f0f0f0;
        }}
        .alignment-table tr.delete {{
            border-left: 4px solid #e74c3c;
        }}
        .alignment-table tr.delete:hover {{
            background-color: rgba(231, 76, 60, 0.3);
        }}
        .alignment-table tr.insert {{
            border-left: 4px solid #27ae60;
        }}
        .alignment-table tr.insert:hover {{
            background-color: rgba(39, 174, 96, 0.3);
        }}
        .alignment-table tr.movein {{
            border-left: 4px solid #3498db;
        }}
        .alignment-table tr.movein:hover {{
            background-color: rgba(52, 152, 219, 0.3);
        }}
        .alignment-table tr.moveout {{
            border-left: 4px solid #9b59b6;
        }}
        .alignment-table tr.moveout:hover {{
            background-color: rgba(155, 89, 182, 0.3);
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
            flex-wrap: wrap;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .filter-label {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 13px;
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
        }}
        .alignment-table tr.hidden {{
            display: none;
        }}
        .stats-summary {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border: 1px solid #bdc3c7;
        }}
        .stats-summary h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            font-size: 12px;
            color: #7f8c8d;
        }}
    </style>
    <!-- 尝试多个CDN源加载jsdiff库 -->
    <script>
        // 加载jsdiff库的多个备用源
        (function() {{
            const cdnSources = [
                'https://cdn.jsdelivr.net/npm/diff@7.0.0/dist/diff.min.js',
                'https://unpkg.com/diff@7.0.0/dist/diff.min.js',
                'https://cdnjs.cloudflare.com/ajax/libs/diff/7.0.0/diff.min.js'
            ];

            let currentIndex = 0;

            function loadScript(src) {{
                return new Promise((resolve, reject) => {{
                    const script = document.createElement('script');
                    script.src = src;
                    script.onload = resolve;
                    script.onerror = () => {{
                        currentIndex++;
                        if (currentIndex < cdnSources.length) {{
                            // 尝试下一个CDN源
                            loadScript(cdnSources[currentIndex]).then(resolve).catch(reject);
                        }} else {{
                            // 所有CDN都失败，使用fallback
                            console.warn('无法从CDN加载jsdiff库，差异高亮功能将不可用');
                            reject(new Error('所有CDN源都加载失败'));
                        }}
                    }};
                    document.head.appendChild(script);
                }});
            }}

            // 开始加载
            loadScript(cdnSources[0]).catch(() => {{
                // 如果所有CDN都失败，仍然继续，只是差异高亮功能不可用
            }});
        }})();
    </script>
</head>
<body>
    <div class="header">
        <div class="stage-badge">阶段一：全等匹配</div>
        <h1>句子对齐报告</h1>
        <p>对齐文件 {title_a} 和 {title_b}</p>
        <p style="font-size: 13px; margin-top: 10px; opacity: 0.9;">
            运行时间: {runtime:.2f}秒
        </p>
    </div>""")

    # 统计信息
    if stats:
        html_lines.append("""    <div class="stats-summary">
        <h3>统计信息</h3>
        <div class="stats-grid">""")

        for key, value in stats.items():
            if key != 'total':
                html_lines.append(f"""            <div class="stat-item">
                <div class="stat-value">{value}</div>
                <div class="stat-label">{key.upper()}</div>
            </div>""")

        html_lines.append(f"""            <div class="stat-item">
                <div class="stat-value">{stats.get('total', 0)}</div>
                <div class="stat-label">总计</div>
            </div>
        </div>
    </div>""")

    # 对齐结果
    html_lines.append(f"""    <div class="alignment-results">
        <div class="filter-controls">
            <div class="filter-group">
                <label class="filter-label">类型筛选：</label>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-type="all" onclick="filterByType('all')">全部</button>
                    <button class="filter-btn active" data-type="match" onclick="filterByType('match')">MATCH</button>
                    <button class="filter-btn active" data-type="delete" onclick="filterByType('delete')">DELETE</button>
                    <button class="filter-btn active" data-type="insert" onclick="filterByType('insert')">INSERT</button>
                    <button class="filter-btn active" data-type="movein" onclick="filterByType('movein')">MOVEIN</button>
                    <button class="filter-btn active" data-type="moveout" onclick="filterByType('moveout')">MOVEOUT</button>
                </div>
            </div>
            <div class="filter-group">
                <label class="filter-label">文本搜索：</label>
                <input type="text" class="filter-search" id="searchText" placeholder="在左右文本中搜索..." oninput="applyFilters()">
                <button class="filter-reset" onclick="resetFilters()">重置筛选</button>
            </div>
        </div>
        <div class="filter-stats" id="filterStats"></div>
        <table class="alignment-table">
            <thead>
                <tr>
                    <th class="col-index">序号</th>
                    <th class="col-type">类型</th>
                    <th class="col-similarity">相似度</th>
                    <th class="col-sentence-a">[句ID, 行ID] {title_a}</th>
                    <th class="col-sentence-b">[句ID, 行ID] {title_b}</th>
                </tr>
            </thead>
            <tbody>""")

    for idx, item in enumerate(alignment, 1):
        item_type = item['type']
        similarity_value = item.get('similarity')
        similarity_text = f'{similarity_value:.2f}' if similarity_value is not None else ''

        # 获取文本内容（用于搜索）
        text_a_raw = item.get('a') or ''
        text_b_raw = item.get('b') or ''
        text_a_escaped = html.escape(str(text_a_raw))
        text_b_escaped = html.escape(str(text_b_raw))

        # 所有行都无条件应用jsdiff（只要至少有一个文本不为空）
        needs_diff = bool(text_a_raw or text_b_raw)

        # 构建原文句子
        sentence_a_text = ""
        if item.get('a'):
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

            # 获取行号
            a_line_num = item.get('a_line_number') or (item.get('a_line_numbers', [None])[0] if item.get('a_line_numbers') else None)
            if isinstance(a_line_num, (int, float)):
                a_line_str = str(int(a_line_num))
            else:
                a_line_str = str(a_line_num) if a_line_num else '?'

            sentence_a_text = f'<span class="index">[{a_idx_str}, {a_line_str}]</span><span class="sentence-a">{html.escape(item["a"])}</span>'

        # 构建校对后句子
        sentence_b_text = ""
        if item.get('b'):
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

            # 获取行号
            b_line_num = item.get('b_line_number') or (item.get('b_line_numbers', [None])[0] if item.get('b_line_numbers') else None)
            if isinstance(b_line_num, (int, float)):
                b_line_str = str(int(b_line_num))
            else:
                b_line_str = str(b_line_num) if b_line_num else '?'

            sentence_b_text = f'<span class="index">[{b_idx_str}, {b_line_str}]</span><span class="sentence-b">{html.escape(item["b"])}</span>'

        # 为需要比较的行添加标记
        needs_diff_attr = 'data-needs-diff="true"' if needs_diff else ''

        # 判断是否为完全匹配（相似度为1的match）
        is_exact_match = (item_type == 'match' and similarity_value is not None and abs(similarity_value - 1.0) < 0.001)
        row_class = f"{item_type} match-exact" if is_exact_match else item_type

        html_lines.append(f"""
            <tr class="{row_class}" data-type="{item_type}" data-text-a="{text_a_escaped}" data-text-b="{text_b_escaped}" data-row-idx="{idx}" data-diff-mode="false" {needs_diff_attr}>
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
            'delete': true,
            'insert': true,
            'movein': true,
            'moveout': true
        };

        // 类型筛选函数
        function filterByType(type) {
            const btn = document.querySelector(`[data-type="${type}"]`);
            typeFilters[type] = !typeFilters[type];

            if (type === 'all') {
                const allActive = !typeFilters['all'];
                typeFilters['match'] = allActive;
                typeFilters['delete'] = allActive;
                typeFilters['insert'] = allActive;
                typeFilters['movein'] = allActive;
                typeFilters['moveout'] = allActive;

                document.querySelectorAll('.filter-btn[data-type]').forEach(b => {
                    b.classList.toggle('active', allActive);
                });
            } else {
                btn.classList.toggle('active', typeFilters[type]);

                const allActive = typeFilters['match'] && typeFilters['delete'] && typeFilters['insert']
                    && typeFilters['movein'] && typeFilters['moveout'];
                const allBtn = document.querySelector('[data-type="all"]');
                allBtn.classList.toggle('active', allActive);
                typeFilters['all'] = allActive;
            }

            applyFilters();
        }

        // 应用所有筛选条件
        function applyFilters() {
            const rows = document.querySelectorAll('.alignment-table tbody tr');
            const searchText = document.getElementById('searchText').value.toLowerCase().trim();

            let visibleCount = 0;

            rows.forEach(row => {
                const rowType = row.dataset.type;
                const typeMatch = typeFilters[rowType] || typeFilters['all'];

                const textA = (row.dataset.textA || '').toLowerCase();
                const textB = (row.dataset.textB || '').toLowerCase();
                const textMatch = !searchText || textA.includes(searchText) || textB.includes(searchText);

                const shouldShow = typeMatch && textMatch;

                if (shouldShow) {
                    row.classList.remove('hidden');
                    visibleCount++;
                } else {
                    row.classList.add('hidden');
                }
            });

            updateFilterStats(visibleCount, rows.length);

            // 筛选后重新初始化渲染队列（优化：只重置可见行的渲染状态）
            if (typeof renderedRows !== 'undefined') {
                // 只清除隐藏行的渲染状态，保留可见行的渲染状态
                const visibleRows = document.querySelectorAll('.alignment-table tbody tr[data-needs-diff="true"]:not(.hidden)');
                const visibleRowSet = new Set(visibleRows);

                // 只从renderedRows中移除隐藏的行
                renderedRows.forEach(row => {
                    if (!visibleRowSet.has(row)) {
                        renderedRows.delete(row);
                    }
                });

                // 更新渲染队列（只包含可见的未渲染行）
                updateRenderQueue();

                // 延迟渲染，避免阻塞UI
                setTimeout(() => {
                    requestAnimationFrame(renderBatch);
                }, 50);
            }
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
            typeFilters['all'] = true;
            typeFilters['match'] = true;
            typeFilters['delete'] = true;
            typeFilters['insert'] = true;
            typeFilters['movein'] = true;
            typeFilters['moveout'] = true;

            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.add('active');
            });

            document.getElementById('searchText').value = '';

            applyFilters();
        }

        // 懒加载渲染配置
        const RENDER_BATCH_SIZE = 20; // 每批渲染的行数（增加批次大小以提高效率）
        const VIEWPORT_BUFFER = 200; // 视口上下缓冲区（像素）
        const INITIAL_RENDER_BUFFER = 500; // 初始渲染缓冲区（像素，减少初始渲染量）

        // 渲染队列和状态
        let renderQueue = [];
        let isRendering = false;
        let renderedRows = new Set();

        // 检查元素是否在视口内（带缓冲区）- 优化版本，避免频繁的getBoundingClientRect
        function isInViewportWithBuffer(element, buffer = VIEWPORT_BUFFER) {
            const rect = element.getBoundingClientRect();
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
            return (
                rect.top >= -buffer &&
                rect.bottom <= viewportHeight + buffer
            );
        }

        // 更新渲染队列（优化版本：只收集未渲染的行，不计算距离）
        function updateRenderQueue() {
            const allRows = document.querySelectorAll('.alignment-table tbody tr[data-needs-diff="true"]:not(.hidden)');
            renderQueue = [];

            // 只收集未渲染的行，不进行距离计算（避免大量getBoundingClientRect调用）
            allRows.forEach(row => {
                if (!renderedRows.has(row)) {
                    renderQueue.push({ row: row });
                }
            });
        }

        // HTML转义函数
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
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

            // 显示差异（检查Diff是否已加载）
            if (typeof Diff !== 'undefined' && Diff) {
                // 检查是否有diffWords方法（v7.0.0可能使用不同的导出方式）
                const diffWordsFunc = Diff.diffWords || (Diff.default && Diff.default.diffWords);
                const diffWordsWithSpaceFunc = Diff.diffWordsWithSpace || (Diff.default && Diff.default.diffWordsWithSpace);

                if (!diffWordsFunc) {
                    // 如果jsdiff不可用，显示原始文本
                    const indexA = cellA.querySelector('.index');
                    const indexB = cellB.querySelector('.index');
                    const indexAHtml = indexA ? indexA.outerHTML : '';
                    const indexBHtml = indexB ? indexB.outerHTML : '';
                    cellA.innerHTML = indexAHtml + escapeHtml(textA);
                    cellB.innerHTML = indexBHtml + escapeHtml(textB);
                    row.dataset.diffMode = 'true';
                    return true;
                }
                let segmenter = null;
                if (typeof Intl !== 'undefined' && Intl.Segmenter) {
                    try {
                        segmenter = new Intl.Segmenter('zh', { granularity: 'word' });
                    } catch (e) {
                        // 如果不支持，使用默认方式
                    }
                }

                // 使用兼容的方式调用diff函数
                // 根据diff@7.0.0文档，diffWordsWithSpace的第三个参数应该是options对象
                let diff;
                if (segmenter && diffWordsWithSpaceFunc) {
                    // 使用intlSegmenter选项（v7.0.0的正确用法）
                    try {
                        diff = diffWordsWithSpaceFunc(textA, textB, { intlSegmenter: segmenter });
                    } catch (e) {
                        // 如果失败，尝试直接传递segmenter（兼容旧版本）
                        try {
                            diff = diffWordsWithSpaceFunc(textA, textB, segmenter);
                        } catch (e2) {
                            // 如果都失败，使用普通的diffWordsWithSpace
                            diff = diffWordsWithSpaceFunc(textA, textB);
                        }
                    }
                } else if (diffWordsWithSpaceFunc) {
                    diff = diffWordsWithSpaceFunc(textA, textB);
                } else {
                    diff = diffWordsFunc(textA, textB);
                }

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

        // 批量渲染函数（优化版本）
        function renderBatch() {
            if (isRendering || renderQueue.length === 0) {
                return;
            }

            isRendering = true;

            // 优先渲染视口内的行
            const viewportRows = [];
            const otherRows = [];

            // 分离视口内和视口外的行（只对需要渲染的行进行检查）
            for (let i = 0; i < Math.min(renderQueue.length, RENDER_BATCH_SIZE * 3); i++) {
                const item = renderQueue[i];
                if (isInViewportWithBuffer(item.row, VIEWPORT_BUFFER)) {
                    viewportRows.push(item);
                } else {
                    otherRows.push(item);
                }
            }

            // 先渲染视口内的行
            const rowsToRender = viewportRows.length > 0
                ? viewportRows.slice(0, RENDER_BATCH_SIZE)
                : renderQueue.slice(0, RENDER_BATCH_SIZE);

            rowsToRender.forEach(item => {
                if (renderDiffForRow(item.row)) {
                    renderedRows.add(item.row);
                }
            });

            // 从队列中移除已渲染的行
            renderQueue = renderQueue.filter(item => !renderedRows.has(item.row));

            isRendering = false;

            // 如果还有待渲染的行，继续渲染（使用更长的延迟，减少CPU占用）
            if (renderQueue.length > 0) {
                setTimeout(() => {
                    requestAnimationFrame(renderBatch);
                }, 50); // 增加延迟到50ms
            }
        }

        // 初始渲染：优先渲染视口内的行（优化版本）
        function initialRender() {
            updateRenderQueue();

            // 只渲染视口内的行（减少初始渲染量）
            const viewportRows = [];
            for (let i = 0; i < Math.min(renderQueue.length, RENDER_BATCH_SIZE * 5); i++) {
                const item = renderQueue[i];
                if (isInViewportWithBuffer(item.row, INITIAL_RENDER_BUFFER)) {
                    viewportRows.push(item);
                }
            }

            // 渲染视口内的行（限制数量）
            viewportRows.slice(0, RENDER_BATCH_SIZE * 2).forEach(item => {
                if (renderDiffForRow(item.row)) {
                    renderedRows.add(item.row);
                }
            });

            // 更新队列
            renderQueue = renderQueue.filter(item => !renderedRows.has(item.row));

            // 继续渲染其余行（延迟更长时间，让页面先显示）
            if (renderQueue.length > 0) {
                setTimeout(() => {
                    requestAnimationFrame(renderBatch);
                }, 200); // 延迟200ms开始渲染其余行
            }
        }

        // 滚动监听（使用节流优化性能）
        let scrollTimer = null;
        function handleScroll() {
            if (scrollTimer) {
                return;
            }

            scrollTimer = setTimeout(() => {
                // 更新渲染队列（不重新计算距离，只收集未渲染的行）
                updateRenderQueue();

                // 优先渲染视口内的行
                renderBatch();

                scrollTimer = null;
            }, 200); // 200ms节流（增加节流时间）
        }

        // 使用 Intersection Observer 监听行进入视口
        let intersectionObserver = null;
        function setupIntersectionObserver() {
            if (!('IntersectionObserver' in window)) {
                // 如果不支持 Intersection Observer，使用滚动监听
                return;
            }

            intersectionObserver = new IntersectionObserver((entries) => {
                // 批量处理进入视口的行
                const rowsToRender = [];
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const row = entry.target;
                        if (row.dataset.needsDiff === 'true' && !renderedRows.has(row)) {
                            rowsToRender.push(row);
                        }
                    }
                });

                // 批量渲染（避免频繁调用renderBatch）
                if (rowsToRender.length > 0) {
                    rowsToRender.forEach(row => {
                        if (renderDiffForRow(row)) {
                            renderedRows.add(row);
                        }
                    });
                }
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
        });
    </script>
</body>
</html>""")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))



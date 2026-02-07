"""
简单快速的句子对齐算法

使用锚点机制和快速相似度算法（Jaccard）进行句子对齐。
适用于改动不大的文本，速度快，内存占用小。
"""

import re
from typing import List, Dict, Set, Optional
from src.splitter import split_chinese_sentences
from src.html_report_v2 import save_html_report_stage1


def get_ngrams(text: str, n: int = 2) -> Set[str]:
    """
    获取文本的n-gram集合（用于Jaccard相似度计算）

    Args:
        text: 输入文本
        n: n-gram的大小，默认2（bigram）

    Returns:
        n-gram集合
    """
    if len(text) < n:
        return {text}

    ngrams = set()
    for i in range(len(text) - n + 1):
        ngrams.add(text[i:i+n])
    return ngrams


def jaccard_similarity(text_a: str, text_b: str, n: int = 2) -> float:
    """
    计算两个文本的Jaccard相似度（基于n-gram）

    Args:
        text_a: 文本A
        text_b: 文本B
        n: n-gram大小

    Returns:
        相似度值，范围0-1
    """
    if not text_a or not text_b:
        return 0.0

    if text_a == text_b:
        return 1.0

    ngrams_a = get_ngrams(text_a, n)
    ngrams_b = get_ngrams(text_b, n)

    intersection = len(ngrams_a & ngrams_b)
    union = len(ngrams_a | ngrams_b)

    if union == 0:
        return 0.0

    return intersection / union


def normalize_sentence(sentence: str, remove_inner_whitespace: bool = True) -> str:
    """
    标准化句子（仅用于相似度计算，不修改原始数据）：忽略前后空白；可选忽略句中空白。

    注意：此函数只用于临时清理文本以进行相似度比较，不会修改原始句子数据。
    """
    s = sentence.strip()
    if remove_inner_whitespace:
        s = re.sub(r'\s', '', s)
    return s


def align_sentences_anchor(
    sentences_a: List[str],
    sentences_b: List[str],
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3,
    remove_inner_whitespace: bool = True
) -> List[Dict]:
    """
    使用锚点机制对齐句子（改进的贪心算法，支持动态窗口扩展和全局搜索）

    算法流程：
    1. 从A的第一个句子开始
    2. 在B中从当前锚点位置左右window_size范围内搜索最相似的句子
    3. 如果找到相似度超过threshold的句子，更新锚点
    4. 如果连续多个句子无法匹配，逐步扩大搜索窗口
    5. 如果扩大窗口后仍无法匹配，进行全局搜索重新定位锚点
    6. 处理A的下一个句子，锚点从当前位置+offset开始

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        window_size: 搜索窗口大小（锚点左右各window_size个句子）
        similarity_threshold: 相似度阈值，超过此值才认为匹配
        ngram_size: n-gram大小，用于Jaccard相似度计算
        offset: 下一个句子的锚点偏移量（默认1，即下一个位置）
        max_window_expansion: 最大窗口扩展倍数（默认3，即最多扩大到3倍）
        consecutive_fail_threshold: 连续失败阈值，超过此值触发窗口扩展（默认3）
        remove_inner_whitespace: 相似度计算时是否忽略句中空白字符（默认是）

    Returns:
        对齐结果列表，每个元素包含：
        - type: 'match' | 'delete' | 'insert'
        - a: 原文句子（delete/match时存在）
        - b: 校对后句子（insert/match时存在）
        - similarity: 相似度值（match时存在）
        - a_index: 原文句子索引
        - b_index: 校对后句子索引
    """
    n = len(sentences_a)
    m = len(sentences_b)

    if n == 0 and m == 0:
        return []

    result = []
    anchor = 0  # 当前锚点位置（在B中的索引）
    a_idx = 0   # 当前处理的A中句子索引
    b_used = set()  # 记录B中已匹配的句子索引
    b_to_result = {}  # 记录B中每个句子对应的结果项（用于插入新增句子）

    # 用于跟踪连续失败次数和动态窗口
    consecutive_fails = 0
    current_window = window_size

    # 按照A文件的顺序处理
    while a_idx < n:
        sent_a = normalize_sentence(sentences_a[a_idx], remove_inner_whitespace)

        # 动态调整搜索窗口：如果连续失败，逐步扩大窗口
        if consecutive_fails >= consecutive_fail_threshold:
            # 扩大搜索窗口（最多扩大到max_window_expansion倍）
            expansion_factor = min(
                max_window_expansion,
                1 + (consecutive_fails - consecutive_fail_threshold) // 2
            )
            current_window = window_size * expansion_factor
        else:
            # 重置窗口大小
            current_window = window_size

        # 确定搜索窗口
        window_start = max(0, anchor - current_window)
        window_end = min(m, anchor + current_window + 1)

        # 在窗口内搜索最相似的句子
        best_match_idx = None
        best_similarity = 0.0
        best_b_idx_in_window = None  # 窗口内最佳匹配位置（即使相似度不够）

        for b_idx in range(window_start, window_end):
            # 跳过已匹配的句子
            if b_idx in b_used:
                continue

            sent_b = normalize_sentence(sentences_b[b_idx], remove_inner_whitespace)
            similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = b_idx if similarity >= similarity_threshold else None
                best_b_idx_in_window = b_idx

        # 如果窗口内没找到匹配，进行全局搜索
        # 触发条件：
        # 1. 连续失败次数达到阈值
        # 2. 或者窗口已经扩大到一定程度（说明可能有大段落变化）
        # 3. 或者窗口内找到的相似度较高（>0.5）但不够阈值（可能是段落重排）
        should_global_search = (
            best_match_idx is None and consecutive_fails >= consecutive_fail_threshold
        ) or (
            best_match_idx is None and current_window >= window_size * 2
        ) or (
            best_match_idx is None and best_similarity > 0.5 and consecutive_fails >= 1
        )

        if should_global_search:
            # 全局搜索：在整个B文本中搜索（跳过已匹配的）
            for b_idx in range(m):
                if b_idx in b_used:
                    continue

                sent_b = normalize_sentence(sentences_b[b_idx], remove_inner_whitespace)
                similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                if similarity > best_similarity:
                    best_similarity = similarity
                    if similarity >= similarity_threshold:
                        best_match_idx = b_idx
                    best_b_idx_in_window = b_idx

        # 判断是否匹配
        if best_match_idx is not None and best_similarity >= similarity_threshold:
            # 匹配成功
            item = {
                'type': 'match',
                'a': sentences_a[a_idx],
                'b': sentences_b[best_match_idx],
                'similarity': best_similarity,
                'a_indices': [a_idx],
                'b_indices': [best_match_idx]
            }
            result.append(item)
            b_to_result[best_match_idx] = item

            # 更新锚点和标记
            anchor = best_match_idx + offset
            b_used.add(best_match_idx)
            consecutive_fails = 0  # 重置连续失败计数
        else:
            # 未找到匹配，视为删除
            result.append({
                'type': 'delete',
                'a': sentences_a[a_idx],
                'b': None,
                'similarity': None,
                'a_index': a_idx,
                'b_index': None
            })

            # 即使没有匹配，如果找到了相似度较高的句子，也适当更新锚点
            # 这有助于在段落重排时重新定位
            if best_b_idx_in_window is not None and best_similarity > 0.3:
                # 如果相似度超过0.3，说明可能是同一内容但改动较大
                # 更新锚点到该位置，但保持较小偏移
                anchor = max(anchor, best_b_idx_in_window)

            consecutive_fails += 1

        a_idx += 1

    # 处理B中剩余的未匹配句子（视为新增）
    # 按照B的原始顺序，紧跟在它上一句（在B中的前一句）的后面

    # 创建B索引到结果位置的映射（包括匹配项和已插入的新增项）
    b_idx_to_result_pos = {}
    for pos, item in enumerate(result):
        if item.get('b_indices'):
            # 对于MATCH项，使用b_indices数组
            for b_idx in item['b_indices']:
                b_idx_to_result_pos[b_idx] = pos
        elif item.get('b_index') is not None:
            # 对于INSERT项，使用b_index
            b_idx_to_result_pos[item['b_index']] = pos

    # 按B的原始顺序处理未匹配的句子
    for b_idx in range(m):
        if b_idx in b_used:
            continue  # 已匹配，跳过

        # 找到B中b_idx的前一句（b_idx-1）在结果中的位置
        insert_pos = len(result)  # 默认插入到末尾

        if b_idx > 0:
            # 查找前一句（b_idx-1）在结果中的位置
            prev_b_idx = b_idx - 1
            if prev_b_idx in b_idx_to_result_pos:
                # 前一句在结果中的位置
                prev_pos = b_idx_to_result_pos[prev_b_idx]
                # 插入到前一句之后
                insert_pos = prev_pos + 1
            else:
                # 前一句也是新增的，继续往前找
                for p_idx in range(prev_b_idx, -1, -1):
                    if p_idx in b_idx_to_result_pos:
                        insert_pos = b_idx_to_result_pos[p_idx] + 1
                        break

        # 创建新增项
        item = {
            'type': 'insert',
            'a': None,
            'b': sentences_b[b_idx],
            'similarity': None,
            'a_index': None,
            'b_index': b_idx
        }

        # 插入到结果中
        result.insert(insert_pos, item)

        # 更新映射（因为插入了新项，后面的位置都变了）
        # 重新构建映射
        b_idx_to_result_pos = {}
        for pos, item in enumerate(result):
            if item.get('b_indices'):
                # 对于MATCH项，使用b_indices数组
                for b_idx in item['b_indices']:
                    b_idx_to_result_pos[b_idx] = pos
            elif item.get('b_index') is not None:
                # 对于INSERT项，使用b_index
                b_idx_to_result_pos[item['b_index']] = pos

    # 结果已经按照A、B文件的原始顺序排列
    # - 匹配和删除按A的顺序
    # - 新增按B的原始顺序插入到合适位置

    # 后处理：在相邻的DELETE和INSERT序列之间尝试重新匹配
    result = rematch_adjacent_delete_insert(
        result,
        similarity_threshold,
        ngram_size,
        remove_inner_whitespace=remove_inner_whitespace
    )

    # 后处理：在一定的序号上下范围内处理不相邻的DELETE和INSERT
    result = rematch_non_adjacent_delete_insert(
        result,
        similarity_threshold,
        ngram_size,
        index_range=window_size,  # 使用窗口大小作为索引范围
        remove_inner_whitespace=remove_inner_whitespace
    )

    # 后处理：将单独的DELETE项合并到相邻的MATCH组中
    result = merge_delete_into_match(
        result,
        ngram_size,
        remove_inner_whitespace=remove_inner_whitespace
    )

    # 后处理：将单独的INSERT项合并到相邻的MATCH组中（与 delete 合并对称，处理 b 侧）
    result = merge_insert_into_match(
        result,
        ngram_size,
        remove_inner_whitespace=remove_inner_whitespace
    )

    # 后处理：检测和处理句子移动，创建movein和moveout条目
    result = detect_and_handle_movements(result)

    return result


def align_sentences_anchor_initial(
    sentences_a: List[str],
    sentences_b: List[str],
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3,
    remove_inner_whitespace: bool = True
) -> List[Dict]:
    """
    使用锚点机制对齐句子（初始对齐，不包含后处理）

    这是 align_sentences_anchor 的简化版本，只进行初始对齐，不进行后处理。
    用于需要获取各阶段中间结果的场景。

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        window_size: 搜索窗口大小（锚点左右各window_size个句子）
        similarity_threshold: 相似度阈值，超过此值才认为匹配
        ngram_size: n-gram大小，用于Jaccard相似度计算
        offset: 下一个句子的锚点偏移量（默认1，即下一个位置）
        max_window_expansion: 最大窗口扩展倍数（默认3，即最多扩大到3倍）
        consecutive_fail_threshold: 连续失败阈值，超过此值触发窗口扩展（默认3）
        remove_inner_whitespace: 相似度计算时是否忽略句中空白字符（默认是）

    Returns:
        初始对齐结果列表（不包含后处理），每个元素包含：
        - type: 'match' | 'delete' | 'insert'
        - a: 原文句子（delete/match时存在）
        - b: 校对后句子（insert/match时存在）
        - similarity: 相似度值（match时存在）
        - a_index/a_indices: 原文句子索引
        - b_index/b_indices: 校对后句子索引
    """
    n = len(sentences_a)
    m = len(sentences_b)

    if n == 0 and m == 0:
        return []

    result = []
    anchor = 0  # 当前锚点位置（在B中的索引）
    a_idx = 0   # 当前处理的A中句子索引
    b_used = set()  # 记录B中已匹配的句子索引
    b_to_result = {}  # 记录B中每个句子对应的结果项（用于插入新增句子）

    # 用于跟踪连续失败次数和动态窗口
    consecutive_fails = 0
    current_window = window_size

    # 按照A文件的顺序处理
    while a_idx < n:
        sent_a = normalize_sentence(sentences_a[a_idx], remove_inner_whitespace)

        # 动态调整搜索窗口：如果连续失败，逐步扩大窗口
        if consecutive_fails >= consecutive_fail_threshold:
            # 扩大搜索窗口（最多扩大到max_window_expansion倍）
            expansion_factor = min(
                max_window_expansion,
                1 + (consecutive_fails - consecutive_fail_threshold) // 2
            )
            current_window = window_size * expansion_factor
        else:
            # 重置窗口大小
            current_window = window_size

        # 确定搜索窗口
        window_start = max(0, anchor - current_window)
        window_end = min(m, anchor + current_window + 1)

        # 在窗口内搜索最相似的句子
        best_match_idx = None
        best_similarity = 0.0
        best_b_idx_in_window = None  # 窗口内最佳匹配位置（即使相似度不够）

        for b_idx in range(window_start, window_end):
            # 跳过已匹配的句子
            if b_idx in b_used:
                continue

            sent_b = normalize_sentence(sentences_b[b_idx], remove_inner_whitespace)
            similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = b_idx if similarity >= similarity_threshold else None
                best_b_idx_in_window = b_idx

        # 如果窗口内没找到匹配，进行全局搜索
        # 触发条件：
        # 1. 连续失败次数达到阈值
        # 2. 或者窗口已经扩大到一定程度（说明可能有大段落变化）
        # 3. 或者窗口内找到的相似度较高（>0.5）但不够阈值（可能是段落重排）
        should_global_search = (
            best_match_idx is None and consecutive_fails >= consecutive_fail_threshold
        ) or (
            best_match_idx is None and current_window >= window_size * 2
        ) or (
            best_match_idx is None and best_similarity > 0.5 and consecutive_fails >= 1
        )

        if should_global_search:
            # 全局搜索：在整个B文本中搜索（跳过已匹配的）
            for b_idx in range(m):
                if b_idx in b_used:
                    continue

                sent_b = normalize_sentence(sentences_b[b_idx], remove_inner_whitespace)
                similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                if similarity > best_similarity:
                    best_similarity = similarity
                    if similarity >= similarity_threshold:
                        best_match_idx = b_idx
                    best_b_idx_in_window = b_idx

        # 判断是否匹配
        if best_match_idx is not None and best_similarity >= similarity_threshold:
            # 匹配成功
            item = {
                'type': 'match',
                'a': sentences_a[a_idx],
                'b': sentences_b[best_match_idx],
                'similarity': best_similarity,
                'a_indices': [a_idx],
                'b_indices': [best_match_idx]
            }
            result.append(item)
            b_to_result[best_match_idx] = item

            # 更新锚点和标记
            anchor = best_match_idx + offset
            b_used.add(best_match_idx)
            consecutive_fails = 0  # 重置连续失败计数
        else:
            # 未找到匹配，视为删除
            result.append({
                'type': 'delete',
                'a': sentences_a[a_idx],
                'b': None,
                'similarity': None,
                'a_index': a_idx,
                'b_index': None
            })

            # 即使没有匹配，如果找到了相似度较高的句子，也适当更新锚点
            # 这有助于在段落重排时重新定位
            if best_b_idx_in_window is not None and best_similarity > 0.3:
                # 如果相似度超过0.3，说明可能是同一内容但改动较大
                # 更新锚点到该位置，但保持较小偏移
                anchor = max(anchor, best_b_idx_in_window)

            consecutive_fails += 1

        a_idx += 1

    # 处理B中剩余的未匹配句子（视为新增）
    # 按照B的原始顺序，紧跟在它上一句（在B中的前一句）的后面

    # 创建B索引到结果位置的映射（包括匹配项和已插入的新增项）
    b_idx_to_result_pos = {}
    for pos, item in enumerate(result):
        if item.get('b_indices'):
            # 对于MATCH项，使用b_indices数组
            for b_idx in item['b_indices']:
                b_idx_to_result_pos[b_idx] = pos
        elif item.get('b_index') is not None:
            # 对于INSERT项，使用b_index
            b_idx_to_result_pos[item['b_index']] = pos

    # 按B的原始顺序处理未匹配的句子
    for b_idx in range(m):
        if b_idx in b_used:
            continue  # 已匹配，跳过

        # 找到B中b_idx的前一句（b_idx-1）在结果中的位置
        insert_pos = len(result)  # 默认插入到末尾

        if b_idx > 0:
            # 查找前一句（b_idx-1）在结果中的位置
            prev_b_idx = b_idx - 1
            if prev_b_idx in b_idx_to_result_pos:
                # 前一句在结果中的位置
                prev_pos = b_idx_to_result_pos[prev_b_idx]
                # 插入到前一句之后
                insert_pos = prev_pos + 1
            else:
                # 前一句也是新增的，继续往前找
                for p_idx in range(prev_b_idx, -1, -1):
                    if p_idx in b_idx_to_result_pos:
                        insert_pos = b_idx_to_result_pos[p_idx] + 1
                        break

        # 创建新增项
        item = {
            'type': 'insert',
            'a': None,
            'b': sentences_b[b_idx],
            'similarity': None,
            'a_index': None,
            'b_index': b_idx
        }

        # 插入到结果中
        result.insert(insert_pos, item)

        # 更新映射（因为插入了新项，后面的位置都变了）
        # 重新构建映射
        b_idx_to_result_pos = {}
        for pos, item in enumerate(result):
            if item.get('b_indices'):
                # 对于MATCH项，使用b_indices数组
                for b_idx in item['b_indices']:
                    b_idx_to_result_pos[b_idx] = pos
            elif item.get('b_index') is not None:
                # 对于INSERT项，使用b_index
                b_idx_to_result_pos[item['b_index']] = pos

    # 结果已经按照A、B文件的原始顺序排列
    # - 匹配和删除按A的顺序
    # - 新增按B的原始顺序插入到合适位置
    # 注意：此函数不进行后处理，返回初始对齐结果

    return result


def _generate_merged_candidates(items: List[Dict], text_key: str, merge: bool = True) -> List[Dict]:
    """
    生成合并后的候选句子

    对于较短的序列，生成单个句子和相邻句子的合并组合

    Args:
        items: 句子项列表（DELETE或INSERT）
        text_key: 文本键名（'a'或'b'）
        merge: 是否生成合并候选（默认True）

    Returns:
        候选句子列表，每个包含：
        - text: 合并后的文本
        - indices: 原始索引列表
        - matched: 是否已匹配
    """
    candidates = []

    # 添加单个句子
    for idx, item in enumerate(items):
        if item[text_key]:
            candidates.append({
                'text': item[text_key],
                'indices': [idx],
                'matched': False,
                'original_item': item
            })

    # 如果允许合并且序列较短（<=3个），尝试合并相邻的句子
    if merge and len(items) <= 3:
        # 合并相邻的两个句子
        for start in range(len(items) - 1):
            merged_text = ''
            indices = []
            for j in range(start, min(start + 2, len(items))):
                if items[j][text_key]:
                    if merged_text:
                        merged_text += items[j][text_key]
                    else:
                        merged_text = items[j][text_key]
                    indices.append(j)

            if merged_text:
                candidates.append({
                    'text': merged_text,
                    'indices': indices,
                    'matched': False,
                    'original_items': [items[i] for i in indices]
                })

        # 如果序列很短（<=2个），也尝试合并所有句子
        if len(items) <= 2 and len(items) > 1:
            merged_text = ''
            indices = []
            for j in range(len(items)):
                if items[j][text_key]:
                    if merged_text:
                        merged_text += items[j][text_key]
                    else:
                        merged_text = items[j][text_key]
                    indices.append(j)

            if merged_text and len(indices) > 1:
                # 检查是否已经作为两个句子的合并添加过
                if not any(c['indices'] == indices for c in candidates if 'original_items' in c):
                    candidates.append({
                        'text': merged_text,
                        'indices': indices,
                        'matched': False,
                        'original_items': [items[i] for i in indices]
                    })

    return candidates


def rematch_adjacent_delete_insert(
    alignment: List[Dict],
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    remove_inner_whitespace: bool = True,
    html_output_path: Optional[str] = None,
    title_a: str = "原文",
    title_b: str = "校对后"
) -> List[Dict]:
    """
    后处理：在相邻的DELETE和INSERT序列之间尝试重新匹配

    算法：
    1. 扫描对齐结果，找到相邻的DELETE和INSERT序列（无论顺序）
    2. 在这些序列之间尝试匹配
    3. 如果找到相似度足够高的匹配，将它们合并为MATCH

    Args:
        alignment: 初始对齐结果
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        html_output_path: 可选的HTML输出路径，如果提供则生成HTML报告
        title_a: 原文标题（用于HTML报告）
        title_b: 校对后标题（用于HTML报告）

    Returns:
        优化后的对齐结果
    """
    if not alignment:
        return alignment

    result = []
    i = 0

    while i < len(alignment):
        current_item = alignment[i]

        # 如果是DELETE或INSERT，查找连续的序列
        if current_item['type'] in ['delete', 'insert']:
            delete_items = []
            insert_items = []

            # 收集连续的DELETE和INSERT序列
            while i < len(alignment) and alignment[i]['type'] in ['delete', 'insert']:
                item = alignment[i]
                if item['type'] == 'delete':
                    delete_items.append(item)
                else:
                    insert_items.append(item)
                i += 1

            # 如果既有DELETE又有INSERT，尝试匹配
            if delete_items and insert_items:
                # 在DELETE和INSERT之间进行匹配
                matched_pairs = []

                # 如果一方较短，尝试合并相邻的句子
                # 在较短的一方生成合并候选，以便与较长的一方进行匹配
                if len(delete_items) < len(insert_items):
                    # DELETE较短，生成DELETE的合并候选（以便匹配多个INSERT）
                    delete_candidates = _generate_merged_candidates(delete_items, 'a')
                    insert_candidates = _generate_merged_candidates(insert_items, 'b', merge=False)
                elif len(insert_items) < len(delete_items):
                    # INSERT较短，生成DELETE的合并候选（以便多个DELETE匹配一个INSERT）
                    delete_candidates = _generate_merged_candidates(delete_items, 'a')
                    insert_candidates = _generate_merged_candidates(insert_items, 'b', merge=False)
                else:
                    # 长度相等，都生成合并候选（但优先单个匹配）
                    delete_candidates = _generate_merged_candidates(delete_items, 'a')
                    insert_candidates = _generate_merged_candidates(insert_items, 'b')

                # 尝试匹配：包括单个句子和合并后的句子
                # 优先匹配合并的句子（更长的候选），然后匹配单个句子
                # 按候选长度降序排序，优先匹配更长的（合并的）候选
                delete_candidates_sorted = sorted(
                    delete_candidates,
                    key=lambda c: len(c['indices']),
                    reverse=True
                )
                insert_candidates_sorted = sorted(
                    insert_candidates,
                    key=lambda c: len(c['indices']),
                    reverse=True
                )

                for d_candidate in delete_candidates_sorted:
                    if d_candidate['matched']:
                        continue

                    best_insert_candidate = None
                    best_similarity = 0.0

                    for ins_candidate in insert_candidates_sorted:
                        if ins_candidate['matched']:
                            continue

                        if d_candidate['text'] and ins_candidate['text']:
                            sent_a = normalize_sentence(d_candidate['text'], remove_inner_whitespace)
                            sent_b = normalize_sentence(ins_candidate['text'], remove_inner_whitespace)
                            similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                            if similarity > best_similarity and similarity >= similarity_threshold:
                                best_similarity = similarity
                                best_insert_candidate = ins_candidate

                    # 如果找到匹配，创建MATCH项
                    if best_insert_candidate is not None:
                        matched_pairs.append((d_candidate, best_insert_candidate, best_similarity))
                        d_candidate['matched'] = True
                        best_insert_candidate['matched'] = True

                # 创建匹配映射：记录哪些索引已被匹配
                delete_matched_indices = set()
                insert_matched_indices = set()
                match_items = []  # (第一个delete_idx, match_item)

                for d_candidate, ins_candidate, sim in matched_pairs:
                    # 记录所有被匹配的索引
                    delete_matched_indices.update(d_candidate['indices'])
                    insert_matched_indices.update(ins_candidate['indices'])

                    # 创建MATCH项
                    # 收集所有A的原始索引
                    if len(d_candidate['indices']) == 1:
                        a_text = d_candidate['original_item']['a']
                        # 使用a_indices字段，如果没有则从a_index获取
                        a_indices = d_candidate['original_item'].get('a_indices',
                            [d_candidate['original_item'].get('a_index', d_candidate['indices'][0])])
                    else:
                        # 合并的句子，收集所有原始索引
                        a_indices = []
                        for j in range(len(d_candidate['indices'])):
                            orig_item = d_candidate['original_items'][j]
                            item_indices = orig_item.get('a_indices',
                                [orig_item.get('a_index', d_candidate['indices'][j])])
                            a_indices.extend(item_indices)
                        a_text = d_candidate['text']

                    # 收集所有B的原始索引
                    if len(ins_candidate['indices']) == 1:
                        b_text = ins_candidate['original_item']['b']
                        # 使用b_indices字段，如果没有则从b_index获取
                        b_indices = ins_candidate['original_item'].get('b_indices',
                            [ins_candidate['original_item'].get('b_index', ins_candidate['indices'][0])])
                    else:
                        # 合并的句子，收集所有原始索引
                        b_indices = []
                        for j in range(len(ins_candidate['indices'])):
                            orig_item = ins_candidate['original_items'][j]
                            item_indices = orig_item.get('b_indices',
                                [orig_item.get('b_index', ins_candidate['indices'][j])])
                            b_indices.extend(item_indices)
                        b_text = ins_candidate['text']

                    match_item = {
                        'type': 'match',
                        'a': a_text,
                        'b': b_text,
                        'similarity': sim,
                        'a_indices': a_indices,
                        'b_indices': b_indices
                    }
                    # 保留行号信息（从原始项中收集）
                    a_line_numbers = []
                    b_line_numbers = []

                    # 处理A侧行号
                    if 'original_items' in d_candidate:
                        for orig_item in d_candidate['original_items']:
                            if orig_item:
                                if 'a_line_numbers' in orig_item:
                                    a_line_numbers.extend(orig_item['a_line_numbers'])
                                elif 'a_line_number' in orig_item and orig_item['a_line_number'] is not None:
                                    a_line_numbers.append(orig_item['a_line_number'])
                    elif 'original_item' in d_candidate and d_candidate['original_item']:
                        orig_item = d_candidate['original_item']
                        if 'a_line_numbers' in orig_item:
                            a_line_numbers.extend(orig_item['a_line_numbers'])
                        elif 'a_line_number' in orig_item and orig_item['a_line_number'] is not None:
                            a_line_numbers.append(orig_item['a_line_number'])

                    # 处理B侧行号
                    if 'original_items' in ins_candidate:
                        for orig_item in ins_candidate['original_items']:
                            if orig_item:
                                if 'b_line_numbers' in orig_item:
                                    b_line_numbers.extend(orig_item['b_line_numbers'])
                                elif 'b_line_number' in orig_item and orig_item['b_line_number'] is not None:
                                    b_line_numbers.append(orig_item['b_line_number'])
                    elif 'original_item' in ins_candidate and ins_candidate['original_item']:
                        orig_item = ins_candidate['original_item']
                        if 'b_line_numbers' in orig_item:
                            b_line_numbers.extend(orig_item['b_line_numbers'])
                        elif 'b_line_number' in orig_item and orig_item['b_line_number'] is not None:
                            b_line_numbers.append(orig_item['b_line_number'])

                    if a_line_numbers:
                        match_item['a_line_numbers'] = a_line_numbers
                        match_item['a_line_number'] = a_line_numbers[0]
                    if b_line_numbers:
                        match_item['b_line_numbers'] = b_line_numbers
                        match_item['b_line_number'] = b_line_numbers[0]

                    # 使用第一个DELETE索引作为键
                    match_items.append((d_candidate['indices'][0], match_item))

                # 按照原始顺序重建：记录每个原始项在delete_items/insert_items中的索引
                start_pos = i - len(delete_items) - len(insert_items)
                delete_counter = 0
                insert_counter = 0
                match_items_by_delete_pos = {pos: item for pos, item in match_items}

                for orig_pos in range(start_pos, i):
                    orig_item = alignment[orig_pos]
                    if orig_item['type'] == 'delete':
                        d_idx = delete_counter
                        delete_counter += 1
                        if d_idx in delete_matched_indices:
                            # 检查是否应该添加MATCH项（只在第一个匹配的索引处添加）
                            if d_idx in match_items_by_delete_pos:
                                result.append(match_items_by_delete_pos[d_idx])
                            # 如果不在match_items_by_delete_pos中，说明是合并匹配的一部分，跳过
                        else:
                            # 未匹配的DELETE
                            result.append(delete_items[d_idx])
                    elif orig_item['type'] == 'insert':
                        ins_idx = insert_counter
                        insert_counter += 1
                        if ins_idx in insert_matched_indices:
                            # INSERT已被匹配，跳过（MATCH项会在对应的DELETE位置添加）
                            pass
                        else:
                            # 未匹配的INSERT
                            result.append(insert_items[ins_idx])
            else:
                # 没有同时存在DELETE和INSERT，直接添加
                result.extend(delete_items)
                result.extend(insert_items)
        else:
            # 其他类型的项（MATCH等），直接添加
            result.append(current_item)
            i += 1

    # 如果提供了HTML输出路径，生成HTML报告
    if html_output_path:
        stats = get_alignment_statistics(result)
        save_html_report_stage1(
            result,
            html_output_path,
            title_a=title_a,
            title_b=title_b,
            runtime=0.0,
            stats=stats
        )

    return result


def rematch_non_adjacent_delete_insert(
    alignment: List[Dict],
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    index_range: int = 10,
    remove_inner_whitespace: bool = True,
    html_output_path: Optional[str] = None,
    title_a: str = "原文",
    title_b: str = "校对后"
) -> List[Dict]:
    """
    后处理：在一定的序号上下范围内处理不相邻的DELETE和INSERT

    算法：
    1. 收集所有的DELETE和INSERT项，记录它们的原始索引（a_index和b_index）
    2. 对于每个DELETE，在一定的索引范围内查找INSERT
       - 基于a_index和b_index的差值来判断是否在范围内
       - 或者基于在结果列表中的位置范围
    3. 尝试匹配，如果找到相似度足够高的匹配，将它们合并为MATCH
    4. 避免重复匹配（每个DELETE和INSERT最多匹配一次）

    Args:
        alignment: 对齐结果（已经过相邻匹配处理）
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        index_range: 序号范围，用于判断DELETE和INSERT是否在合理范围内（默认10）
        html_output_path: 可选的HTML输出路径，如果提供则生成HTML报告
        title_a: 原文标题（用于HTML报告）
        title_b: 校对后标题（用于HTML报告）

    Returns:
        优化后的对齐结果
    """
    if not alignment:
        return alignment

    # 第一步：收集所有的DELETE和INSERT项，记录它们在结果中的位置和原始索引
    delete_items = []  # [(position, item, a_index), ...]
    insert_items = []  # [(position, item, b_index), ...]

    for pos, item in enumerate(alignment):
        if item['type'] == 'delete':
            # 获取a_index
            a_idx = None
            if item.get('a_indices') and len(item['a_indices']) == 1:
                a_idx = item['a_indices'][0]
            elif item.get('a_index') is not None:
                a_idx = item['a_index']

            if a_idx is not None:
                delete_items.append((pos, item, a_idx))

        elif item['type'] == 'insert':
            # 获取b_index
            b_idx = None
            if item.get('b_indices') and len(item['b_indices']) == 1:
                b_idx = item['b_indices'][0]
            elif item.get('b_index') is not None:
                b_idx = item['b_index']

            if b_idx is not None:
                insert_items.append((pos, item, b_idx))

    if not delete_items or not insert_items:
        # 没有DELETE或INSERT，直接返回
        return alignment

    # 第二步：尝试匹配不相邻的DELETE和INSERT
    # 对于每个DELETE，在一定的范围内查找INSERT
    matched_pairs = []  # [(delete_pos, insert_pos, similarity), ...]
    delete_matched = set()  # 已匹配的DELETE位置
    insert_matched = set()  # 已匹配的INSERT位置

    # 按a_index排序DELETE项，按b_index排序INSERT项
    delete_items_sorted = sorted(delete_items, key=lambda x: x[2])  # 按a_index排序
    insert_items_sorted = sorted(insert_items, key=lambda x: x[2])  # 按b_index排序

    for d_pos, d_item, d_a_idx in delete_items_sorted:
        if d_pos in delete_matched:
            continue

        best_insert = None
        best_similarity = 0.0
        best_insert_pos = None

        # 在INSERT项中查找匹配
        for ins_pos, ins_item, ins_b_idx in insert_items_sorted:
            if ins_pos in insert_matched:
                continue

            # 判断是否在合理范围内
            # 方法1：基于原始索引的差值（如果a_index和b_index接近，说明可能是同一内容）
            index_diff = abs(d_a_idx - ins_b_idx)

            # 方法2：基于在结果列表中的位置差值
            position_diff = abs(d_pos - ins_pos)

            # 如果索引差值或位置差值在范围内，尝试匹配
            if index_diff <= index_range or position_diff <= index_range:
                # 计算相似度
                if d_item.get('a') and ins_item.get('b'):
                    sent_a = normalize_sentence(d_item['a'], remove_inner_whitespace)
                    sent_b = normalize_sentence(ins_item['b'], remove_inner_whitespace)
                    similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                    if similarity > best_similarity and similarity >= similarity_threshold:
                        best_similarity = similarity
                        best_insert = ins_item
                        best_insert_pos = ins_pos

        # 如果找到匹配，记录
        if best_insert is not None:
            matched_pairs.append((d_pos, best_insert_pos, best_similarity))
            delete_matched.add(d_pos)
            insert_matched.add(best_insert_pos)

    # 如果没有找到匹配，直接返回原结果
    if not matched_pairs:
        return alignment

    # 第三步：构建新的结果列表，将匹配的DELETE和INSERT替换为MATCH
    result = []
    delete_matched_positions = {d_pos for d_pos, _, _ in matched_pairs}
    insert_matched_positions = {ins_pos for _, ins_pos, _ in matched_pairs}
    match_items_by_delete_pos = {}  # {delete_pos: match_item}

    # 创建匹配项
    for d_pos, ins_pos, sim in matched_pairs:
        d_item = alignment[d_pos]
        ins_item = alignment[ins_pos]

        # 收集索引
        a_indices = d_item.get('a_indices', [])
        if not a_indices and d_item.get('a_index') is not None:
            a_indices = [d_item['a_index']]

        b_indices = ins_item.get('b_indices', [])
        if not b_indices and ins_item.get('b_index') is not None:
            b_indices = [ins_item['b_index']]

        match_item = {
            'type': 'match',
            'a': d_item['a'],
            'b': ins_item['b'],
            'similarity': sim,
            'a_indices': a_indices,
            'b_indices': b_indices
        }
        # 保留行号信息
        if 'a_line_numbers' in d_item:
            match_item['a_line_numbers'] = d_item['a_line_numbers']
            if match_item['a_line_numbers']:
                match_item['a_line_number'] = match_item['a_line_numbers'][0]
        elif 'a_line_number' in d_item and d_item['a_line_number'] is not None:
            match_item['a_line_number'] = d_item['a_line_number']
            match_item['a_line_numbers'] = [d_item['a_line_number']]

        if 'b_line_numbers' in ins_item:
            match_item['b_line_numbers'] = ins_item['b_line_numbers']
            if match_item['b_line_numbers']:
                match_item['b_line_number'] = match_item['b_line_numbers'][0]
        elif 'b_line_number' in ins_item and ins_item['b_line_number'] is not None:
            match_item['b_line_number'] = ins_item['b_line_number']
            match_item['b_line_numbers'] = [ins_item['b_line_number']]

        match_items_by_delete_pos[d_pos] = match_item

    # 构建结果：按照原始顺序，将匹配的项替换为MATCH
    for pos, item in enumerate(alignment):
        if pos in delete_matched_positions:
            # DELETE已匹配，添加MATCH项
            if pos in match_items_by_delete_pos:
                result.append(match_items_by_delete_pos[pos])
        elif pos in insert_matched_positions:
            # INSERT已匹配，跳过（MATCH项已在对应的DELETE位置添加）
            pass
        else:
            # 其他项，直接添加
            result.append(item)

    # 如果提供了HTML输出路径，生成HTML报告
    if html_output_path:
        stats = get_alignment_statistics(result)
        save_html_report_stage1(
            result,
            html_output_path,
            title_a=title_a,
            title_b=title_b,
            runtime=0.0,
            stats=stats
        )

    return result


def detect_and_handle_movements(
    alignment: List[Dict],
    movement_threshold: int = 2
) -> List[Dict]:
    """
    检测和处理句子移动，创建movein和moveout条目（基于b侧id连续性分组）

    算法：
    1. 只检查b侧id（b_index）的连续性
    2. 把所有连续条目构成的块区分出来
    3. 把条目最少的块移动到大块之间，看是否能拼接为更大的块
    4. 如此循环，直到无法再合并

    Args:
        alignment: 对齐结果
        movement_threshold: 保留参数以兼容旧代码，但不再使用

    Returns:
        处理后的对齐结果，包含movein和moveout条目
    """
    if not alignment:
        return alignment

    def get_b_index(item: Dict) -> Optional[int]:
        """获取条目的b_index"""
        if item.get('b_indices') and len(item['b_indices']) == 1:
            return item['b_indices'][0]
        elif item.get('b_index') is not None:
            return item['b_index']
        return None

    def get_a_index(item: Dict) -> Optional[int]:
        """获取条目的a_index"""
        if item.get('a_indices') and len(item['a_indices']) == 1:
            return item['a_indices'][0]
        elif item.get('a_index') is not None:
            return item['a_index']
        return None

    # 第一步：收集所有match项，只关注b侧id的连续性
    match_items = []  # [(item, pos, b_idx), ...]
    for pos, item in enumerate(alignment):
        if item.get('type') == 'match':
            b_idx = get_b_index(item)
            if b_idx is not None:
                match_items.append((item, pos, b_idx))

    if len(match_items) < 2:
        # 少于2个match项，无法判断移动
        return alignment

    # 第二步：根据b_index的连续性分组为块，并预先计算每个块的min/max b_index
    def group_into_blocks_with_metadata(match_items):
        """根据b_index的连续性将match项分组为块，并返回块的元数据"""
        if not match_items:
            return [], []

        # 按位置排序（只排序一次）
        sorted_items = sorted(match_items, key=lambda x: x[1])  # 按pos排序

        blocks = []
        block_metadata = []  # [(min_b, max_b, first_pos, last_pos), ...]
        current_block = [sorted_items[0]]

        for i in range(1, len(sorted_items)):
            prev_item, prev_pos, prev_b_idx = sorted_items[i-1]
            curr_item, curr_pos, curr_b_idx = sorted_items[i]

            # 检查b_index是否连续（差值=1）
            if curr_b_idx == prev_b_idx + 1:
                # 连续，加入当前块
                current_block.append((curr_item, curr_pos, curr_b_idx))
            else:
                # 不连续，保存当前块并开始新块
                if current_block:
                    # 由于块内b_index连续，min就是第一个，max就是最后一个
                    first_b_idx = current_block[0][2]
                    last_b_idx = current_block[-1][2]
                    blocks.append(current_block)
                    block_metadata.append((
                        first_b_idx,  # min_b（第一个b_index）
                        last_b_idx,   # max_b（最后一个b_index）
                        current_block[0][1],  # first_pos
                        current_block[-1][1]  # last_pos
                    ))
                current_block = [(curr_item, curr_pos, curr_b_idx)]

        # 添加最后一个块
        if current_block:
            # 由于块内b_index连续，min就是第一个，max就是最后一个
            first_b_idx = current_block[0][2]
            last_b_idx = current_block[-1][2]
            blocks.append(current_block)
            block_metadata.append((
                first_b_idx,  # min_b（第一个b_index）
                last_b_idx,   # max_b（最后一个b_index）
                current_block[0][1],  # first_pos
                current_block[-1][1]  # last_pos
            ))

        return blocks, block_metadata

    # 迭代优化：尝试移动小块来合并成更大的块，直到只剩下一个块
    movements = []  # [(原match项, moveout项, movein项, 插入位置信息), ...]
    max_iterations = 100  # 最多迭代100次，避免无限循环

    for iteration in range(max_iterations):
        blocks, block_metadata = group_into_blocks_with_metadata(match_items)

        if len(blocks) <= 1:
            # 只有一个块或没有块，所有条目已连贯
            break

        # 找出所有最小的块（条目数最少），可能有多个相同大小的最小块
        min_block_size = min(len(block) for block in blocks)
        smallest_blocks = [(idx, block) for idx, block in enumerate(blocks) if len(block) == min_block_size]

        # 尝试处理每个最小块，找到一个可以合并的
        merged = False
        for smallest_block_idx, smallest_block in smallest_blocks:
            # 使用预先计算的元数据
            smallest_min_b, smallest_max_b, smallest_first_pos, smallest_last_pos = block_metadata[smallest_block_idx]

            best_insert_pos = None
            best_merged_size = 0  # 合并后形成的连续块大小

            # 首先检查是否可以插入到两个块之间（形成更大的连续块）
            # 优化：使用预先计算的元数据，避免重复计算min/max
            for prev_block_idx, (prev_min_b, prev_max_b, prev_first_pos, prev_last_pos) in enumerate(block_metadata):
                if prev_block_idx == smallest_block_idx:
                    continue

                # 检查prev_block是否可以接在smallest之前
                if prev_max_b + 1 != smallest_min_b:
                    continue

                # 查找可以接在smallest之后的块
                for next_block_idx, (next_min_b, next_max_b, next_first_pos, next_last_pos) in enumerate(block_metadata):
                    if next_block_idx == smallest_block_idx or next_block_idx == prev_block_idx:
                        continue

                    # 检查是否可以插入到prev_block和next_block之间
                    if smallest_max_b + 1 == next_min_b:
                        # 可以插入到两个块之间，形成更大的连续块
                        insert_pos = next_first_pos
                        merged_size = len(blocks[prev_block_idx]) + len(smallest_block) + len(blocks[next_block_idx])
                        if merged_size > best_merged_size:
                            best_insert_pos = insert_pos
                            best_merged_size = merged_size

            # 如果没有找到可以插入到两个块之间的位置，检查是否可以与单个块合并
            if best_insert_pos is None:
                for target_block_idx, (target_min_b, target_max_b, target_first_pos, target_last_pos) in enumerate(block_metadata):
                    if target_block_idx == smallest_block_idx:
                        continue

                    # 检查是否可以合并（最小块的b_index范围与目标块的b_index范围相邻）
                    merged_size = 0
                    insert_pos = None

                    if smallest_max_b + 1 == target_min_b:
                        # 最小块在目标块之前，可以合并
                        insert_pos = target_first_pos
                        merged_size = len(smallest_block) + len(blocks[target_block_idx])
                    elif target_max_b + 1 == smallest_min_b:
                        # 最小块在目标块之后，可以合并
                        insert_pos = target_last_pos + 1
                        merged_size = len(smallest_block) + len(blocks[target_block_idx])

                    if insert_pos is not None and merged_size > best_merged_size:
                        best_insert_pos = insert_pos
                        best_merged_size = merged_size

            # 如果找到了最佳插入位置，创建movein/moveout
            if best_insert_pos is not None:
                for item, pos, b_idx in smallest_block:
                    a_idx = get_a_index(item)
                    if a_idx is None:
                        continue

                    original_similarity = item.get('similarity')
                    if original_similarity is None:
                        original_similarity = 0.0
                    else:
                        original_similarity = float(original_similarity)

                    # 创建moveout和movein
                    moveout_item = item.copy()
                    moveout_item.update({
                        'type': 'moveout',
                        'similarity': original_similarity,
                        'a_index': a_idx,
                        'b_index': b_idx,
                        'original_b_index': b_idx,
                    })
                    # 保留所有字段
                    for field in ['a_indices', 'b_indices', 'a_line_number', 'b_line_number',
                                 'a_line_numbers', 'b_line_numbers', 'id', 'group_id', 'offset']:
                        if field in item:
                            moveout_item[field] = item[field]

                    movein_item = item.copy()
                    movein_item.update({
                        'type': 'movein',
                        'similarity': original_similarity,
                        'a_index': a_idx,
                        'b_index': b_idx,
                        'original_a_index': a_idx,
                    })
                    # 保留所有字段
                    for field in ['a_indices', 'b_indices', 'a_line_number', 'b_line_number',
                                 'a_line_numbers', 'b_line_numbers', 'id', 'group_id', 'offset']:
                        if field in item:
                            movein_item[field] = item[field]

                    movements.append((item, moveout_item, movein_item, {
                        'moveout_insert_at_a': a_idx,  # moveout在原位置
                        'movein_insert_pos': best_insert_pos,  # movein插入到目标位置
                    }))

                merged = True
                # 从match_items中移除已处理的项，以便下次迭代时不再处理
                # 使用位置集合来快速查找和移除
                smallest_positions = {pos for _, pos, _ in smallest_block}
                match_items = [(item, pos, b_idx) for item, pos, b_idx in match_items
                              if pos not in smallest_positions]
                # 找到一个可以合并的块后，跳出循环，继续下一次迭代
                break

        if not merged:
            # 无法再合并，退出循环
            break

    # 如果没有检测到移动，直接返回原结果
    if not movements:
        return alignment

    # 第三步：构建新的结果列表
    # 创建移动项的映射
    match_to_movements = {}
    for original, moveout, movein, insert_info in movements:
        match_to_movements[id(original)] = (moveout, movein, insert_info)

    # 第一遍：处理A的顺序（替换match项，并插入需要额外插入的moveout）
    # 收集需要额外插入的moveout项（基于位置）
    moveout_insertions = {}  # {position: [moveout_items]}
    for original, moveout, movein, insert_info in movements:
        if 'moveout_insert_pos' in insert_info:
            # 需要额外插入的moveout（基于位置）
            pos = insert_info['moveout_insert_pos']
            if pos not in moveout_insertions:
                moveout_insertions[pos] = []
            moveout_insertions[pos].append(moveout)

    result_a_order = []
    for pos, item in enumerate(alignment):
        # 先插入需要在此位置插入的moveout项
        if pos in moveout_insertions:
            result_a_order.extend(moveout_insertions[pos])

        # 然后处理当前项
        if id(item) in match_to_movements:
            # 这是移动的match项，根据情况替换为moveout或movein
            moveout, movein, insert_info = match_to_movements[id(item)]
            # 判断应该替换为什么：
            # - 如果moveout_insert_pos存在，说明moveout需要插入到后面，当前位置应该替换为movein（a异常、b正常的情况）
            # - 如果movein_insert_pos存在，说明movein需要插入到后面，当前位置应该替换为moveout（a正常、b异常的情况）
            # - 如果都不存在，说明是双侧异常的情况，需要根据具体情况处理
            if 'moveout_insert_pos' in insert_info:
                # a异常、b正常：当前位置替换为movein
                result_a_order.append(movein)
            elif 'movein_insert_pos' in insert_info:
                # a正常、b异常：当前位置替换为moveout
                result_a_order.append(moveout)
            else:
                # 双侧异常的情况，默认替换为moveout（这种情况应该很少）
                result_a_order.append(moveout)
        else:
            result_a_order.append(item)

    # 处理末尾插入的moveout
    if len(alignment) in moveout_insertions:
        result_a_order.extend(moveout_insertions[len(alignment)])

    # 第二遍：处理B的顺序（插入movein项）
    # 收集所有需要额外插入的movein项（已经在当前位置的movein不需要再插入）
    movein_items = []  # [(insert_pos或b_index, movein, is_position_based), ...]
    for original, moveout, movein, insert_info in movements:
        if 'movein_insert_pos' in insert_info:
            # 基于位置的插入（a正常、b异常的情况，movein需要插入到后面）
            movein_items.append((insert_info['movein_insert_pos'], movein, True))
        elif 'movein_insert_at_b' in insert_info:
            # 基于b_index的插入（这种情况应该很少，因为movein_insert_at_b通常意味着movein已经在当前位置）
            # 但为了兼容性，仍然处理
            movein_items.append((insert_info['movein_insert_at_b'], movein, False))
        # 如果只有moveout_insert_pos，说明movein已经在当前位置替换了，不需要再插入

    # 按插入位置或b_index排序
    movein_items.sort(key=lambda x: x[0])

    # 创建b_index到结果位置的映射
    b_idx_to_pos = {}
    for pos, item in enumerate(result_a_order):
        if item.get('b_indices'):
            for b_idx in item['b_indices']:
                b_idx_to_pos[b_idx] = pos
        elif item.get('b_index') is not None:
            b_idx_to_pos[item['b_index']] = pos

    # 预先计算所有movein项应该插入的位置
    insertions = {}  # {position: [movein_items]}

    for insert_key, movein, is_position_based in movein_items:
        if is_position_based:
            # 基于位置的插入（直接使用位置）
            insert_pos = insert_key
        else:
            # 基于b_index的插入（需要查找位置）
            b_idx = insert_key
            insert_pos = len(result_a_order)  # 默认插入到末尾

            if b_idx > 0:
                prev_b_idx = b_idx - 1
                if prev_b_idx in b_idx_to_pos:
                    insert_pos = b_idx_to_pos[prev_b_idx] + 1
                else:
                    # 前一句也是新增的，继续往前找（最多查找10次，避免无限循环）
                    for p_idx in range(prev_b_idx, max(-1, prev_b_idx - 10), -1):
                        if p_idx in b_idx_to_pos:
                            insert_pos = b_idx_to_pos[p_idx] + 1
                            break

        # 将movein项添加到对应位置的列表中
        if insert_pos not in insertions:
            insertions[insert_pos] = []
        insertions[insert_pos].append(movein)

    # 一次性构建结果，避免频繁insert
    result = []
    for pos in range(len(result_a_order) + 1):  # +1 用于处理末尾插入
        # 先添加当前位置的movein项（如果有）
        if pos in insertions:
            result.extend(insertions[pos])

        # 然后添加原始项（如果不是末尾）
        if pos < len(result_a_order):
            result.append(result_a_order[pos])

    return result


def merge_delete_into_match(
    alignment: List[Dict],
    ngram_size: int = 2,
    remove_inner_whitespace: bool = True
) -> List[Dict]:
    """
    后处理：将单独的DELETE项合并到相邻的MATCH组中

    算法：
    1. 扫描对齐结果，找到单独的DELETE项
    2. 检查相邻的MATCH项（前一个或后一个）
    3. 尝试将DELETE项的内容合并到MATCH项的A部分
    4. 重新计算与B部分的相似度
    5. 如果相似度提高，则合并成功

    Args:
        alignment: 对齐结果
        ngram_size: n-gram大小

    Returns:
        优化后的对齐结果
    """
    if not alignment:
        return alignment

    result = []
    i = 0

    while i < len(alignment):
        current_item = alignment[i]

        # 如果是单独的DELETE项，尝试合并到相邻的MATCH
        if current_item['type'] == 'delete' and current_item.get('a'):
            # 检查前一个和后一个项
            prev_item = alignment[i - 1] if i > 0 else None
            next_item = alignment[i + 1] if i < len(alignment) - 1 else None

            best_match = None
            best_similarity = 0.0
            merge_direction = None  # 'prev' 或 'next'

            # 尝试合并到前一个MATCH
            if (prev_item is not None and
                prev_item.get('type') == 'match' and
                prev_item.get('a') and
                prev_item.get('b')):
                prev_a = prev_item.get('a', '')
                prev_b = prev_item.get('b', '')
                merged_a = prev_a + current_item['a']
                sent_a = normalize_sentence(merged_a, remove_inner_whitespace)
                sent_b = normalize_sentence(prev_b, remove_inner_whitespace)
                new_similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                # 如果新相似度高于原相似度，则合并
                prev_sim = prev_item.get('similarity', 0.0)
                if new_similarity > prev_sim:
                    if new_similarity > best_similarity:
                        best_similarity = new_similarity
                        best_match = prev_item
                        merge_direction = 'prev'

            # 尝试合并到后一个MATCH
            if (next_item is not None and
                next_item.get('type') == 'match' and
                next_item.get('a') and
                next_item.get('b')):
                merged_a = current_item['a'] + next_item['a']
                sent_a = normalize_sentence(merged_a, remove_inner_whitespace)
                sent_b = normalize_sentence(next_item['b'], remove_inner_whitespace)
                new_similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                # 如果新相似度高于原相似度，则合并
                if new_similarity > next_item.get('similarity', 0.0):
                    if new_similarity > best_similarity:
                        best_similarity = new_similarity
                        best_match = next_item
                        merge_direction = 'next'

            # 如果找到可以合并的MATCH，进行合并
            if best_match is not None:
                if merge_direction == 'prev':
                    # 合并到前一个MATCH，更新result中最后一个项（前一个MATCH）
                    if result and result[-1].get('type') == 'match':
                        result[-1]['a'] = result[-1]['a'] + current_item['a']
                        result[-1]['similarity'] = best_similarity
                        # 更新索引数组
                        delete_a_indices = current_item.get('a_indices', [])
                        if delete_a_indices:
                            if 'a_indices' not in result[-1]:
                                result[-1]['a_indices'] = []
                            result[-1]['a_indices'].extend(delete_a_indices)
                        elif current_item.get('a_index') is not None:
                            # 如果a_indices不存在，但a_index存在，也处理a_index
                            if 'a_indices' not in result[-1]:
                                result[-1]['a_indices'] = []
                            result[-1]['a_indices'].append(current_item['a_index'])
                    # 跳过当前DELETE
                    i += 1
                    continue
                else:  # merge_direction == 'next'
                    # 合并到后一个MATCH，更新alignment中的后一个MATCH
                    # 这样在后续处理时会使用更新后的值
                    next_item['a'] = current_item['a'] + next_item['a']
                    next_item['similarity'] = best_similarity
                    # 更新索引数组
                    delete_a_indices = current_item.get('a_indices', [])
                    if delete_a_indices:
                        if 'a_indices' not in next_item:
                            next_item['a_indices'] = []
                        next_item['a_indices'] = delete_a_indices + next_item.get('a_indices', [])
                    elif current_item.get('a_index') is not None:
                        # 如果a_indices不存在，但a_index存在，也处理a_index
                        if 'a_indices' not in next_item:
                            next_item['a_indices'] = []
                        next_item['a_indices'] = [current_item['a_index']] + next_item.get('a_indices', [])
                    # 跳过当前DELETE
                    i += 1
                    continue

        # 其他情况，直接添加
        result.append(current_item)
        i += 1

    return result


def merge_insert_into_match(
    alignment: List[Dict],
    ngram_size: int = 2,
    remove_inner_whitespace: bool = True
) -> List[Dict]:
    """
    后处理：将单独的INSERT项合并到相邻的MATCH组中（与 merge_delete_into_match 对称，处理 b 侧）

    算法：
    1. 扫描对齐结果，找到单独的INSERT项
    2. 检查相邻的MATCH项（前一个或后一个）
    3. 尝试将INSERT项的内容合并到MATCH项的B部分
    4. 重新计算与A部分的相似度，或若归一化后 insert.b 是 match.a 的前缀/后缀则允许合并

    Args:
        alignment: 对齐结果
        ngram_size: n-gram大小
        remove_inner_whitespace: 相似度计算时是否忽略句中空白

    Returns:
        优化后的对齐结果
    """
    if not alignment:
        return alignment

    result = []
    i = 0

    while i < len(alignment):
        current_item = alignment[i]

        # 如果是单独的INSERT项，尝试合并到相邻的MATCH
        if current_item.get('type') == 'insert' and current_item.get('b'):
            prev_item = alignment[i - 1] if i > 0 else None
            next_item = alignment[i + 1] if i < len(alignment) - 1 else None

            best_match = None
            best_similarity = 0.0
            merge_direction = None  # 'prev' 或 'next'

            # 尝试合并到前一个MATCH（INSERT 的 b 追加到前一个 MATCH 的 b 后）
            if (prev_item is not None and
                prev_item.get('type') == 'match' and
                prev_item.get('a') and
                prev_item.get('b')):
                prev_a = prev_item.get('a', '')
                prev_b = prev_item.get('b', '')
                merged_b = prev_b + current_item['b']
                sent_a = normalize_sentence(prev_a, remove_inner_whitespace)
                sent_b = normalize_sentence(merged_b, remove_inner_whitespace)
                new_similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                prev_sim = prev_item.get('similarity', 0.0)
                # 结构条件：若归一化后 insert.b 是 prevMatch.a 的后缀，也允许合并
                norm_insert_b_prev = normalize_sentence(current_item['b'], remove_inner_whitespace)
                insert_is_suffix_of_prev_a = (len(norm_insert_b_prev) > 0 and
                                              sent_a.endswith(norm_insert_b_prev))

                if new_similarity > prev_sim or insert_is_suffix_of_prev_a:
                    sim_to_use = new_similarity if new_similarity > prev_sim else max(new_similarity, prev_sim)
                    if insert_is_suffix_of_prev_a or sim_to_use > best_similarity:
                        best_similarity = sim_to_use
                        best_match = prev_item
                        merge_direction = 'prev'

            # 尝试合并到后一个MATCH（INSERT 的 b 拼到后一个 MATCH 的 b 前）
            if (next_item is not None and
                next_item.get('type') == 'match' and
                next_item.get('a') and
                next_item.get('b')):
                merged_b = current_item['b'] + next_item['b']
                sent_a = normalize_sentence(next_item['a'], remove_inner_whitespace)
                sent_b = normalize_sentence(merged_b, remove_inner_whitespace)
                new_similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                next_sim = next_item.get('similarity', 0.0)
                # 与 DELETE 合并对称：若归一化后 insert.b 是 nextMatch.a 的前缀，则允许合并
                norm_insert_b = normalize_sentence(current_item['b'], remove_inner_whitespace)
                insert_is_prefix_of_next_a = (len(norm_insert_b) > 0 and sent_a.startswith(norm_insert_b))

                if new_similarity > next_sim or insert_is_prefix_of_next_a:
                    sim_to_use = new_similarity if new_similarity > next_sim else max(new_similarity, next_sim)
                    if insert_is_prefix_of_next_a or sim_to_use > best_similarity:
                        best_similarity = sim_to_use
                        best_match = next_item
                        merge_direction = 'next'

            # 如果找到可以合并的MATCH，进行合并
            if best_match is not None:
                if merge_direction == 'prev':
                    if result and result[-1].get('type') == 'match':
                        result[-1]['b'] = result[-1]['b'] + current_item['b']
                        result[-1]['similarity'] = best_similarity
                        insert_b_indices = current_item.get('b_indices', [])
                        if insert_b_indices:
                            if 'b_indices' not in result[-1]:
                                result[-1]['b_indices'] = []
                            result[-1]['b_indices'].extend(insert_b_indices)
                        elif current_item.get('b_index') is not None:
                            if 'b_indices' not in result[-1]:
                                result[-1]['b_indices'] = []
                            result[-1]['b_indices'].append(current_item['b_index'])
                        # 合并 b 侧行号
                        if current_item.get('b_line_numbers'):
                            if 'b_line_numbers' not in result[-1]:
                                result[-1]['b_line_numbers'] = (result[-1].get('b_line_number') is not None
                                                                 and [result[-1]['b_line_number']] or [])
                            result[-1]['b_line_numbers'].extend(current_item['b_line_numbers'])
                        elif current_item.get('b_line_number') is not None:
                            if 'b_line_numbers' not in result[-1]:
                                result[-1]['b_line_numbers'] = (result[-1].get('b_line_number') is not None
                                                                 and [result[-1]['b_line_number']] or [])
                            result[-1]['b_line_numbers'].append(current_item['b_line_number'])
                    i += 1
                    continue
                else:  # merge_direction == 'next'
                    next_item['b'] = current_item['b'] + next_item['b']
                    next_item['similarity'] = best_similarity
                    insert_b_indices = current_item.get('b_indices', [])
                    if insert_b_indices:
                        if 'b_indices' not in next_item:
                            next_item['b_indices'] = []
                        next_item['b_indices'] = insert_b_indices + next_item.get('b_indices', [])
                    elif current_item.get('b_index') is not None:
                        if 'b_indices' not in next_item:
                            next_item['b_indices'] = []
                        next_item['b_indices'] = [current_item['b_index']] + next_item.get('b_indices', [])
                    # 合并 b 侧行号（prepend）
                    if current_item.get('b_line_numbers'):
                        if 'b_line_numbers' not in next_item:
                            next_item['b_line_numbers'] = (next_item.get('b_line_number') is not None
                                                           and [next_item['b_line_number']] or [])
                        next_item['b_line_numbers'] = (current_item['b_line_numbers'] +
                                                       next_item.get('b_line_numbers', []))
                    elif current_item.get('b_line_number') is not None:
                        if 'b_line_numbers' not in next_item:
                            next_item['b_line_numbers'] = (next_item.get('b_line_number') is not None
                                                           and [next_item['b_line_number']] or [])
                        next_item['b_line_numbers'] = ([current_item['b_line_number']] +
                                                       next_item.get('b_line_numbers', []))
                    i += 1
                    continue

        # 其他情况，直接添加
        result.append(current_item)
        i += 1

    return result


def align_texts_anchor(
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
    对齐两个完整文本（使用改进的锚点算法）

    Args:
        text_a: 原文
        text_b: 校对后文本
        preserve_formatting: 是否保留格式
        window_size: 搜索窗口大小
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        offset: 锚点偏移量
        max_window_expansion: 最大窗口扩展倍数
        consecutive_fail_threshold: 连续失败阈值，超过此值触发窗口扩展

    Returns:
        对齐结果列表
    """
    # 切分句子（保留原始数据，不清理空白字符）
    # 注意：只过滤完全为空的句子，但保留只包含空白字符的句子
    # 空白字符的清理只在normalize_sentence中进行，用于相似度计算
    sentences_a = [
        s for s in split_chinese_sentences(text_a)
        if s  # 只过滤None或空字符串，保留只包含空白字符的句子
    ]
    sentences_b = [
        s for s in split_chinese_sentences(text_b)
        if s  # 只过滤None或空字符串，保留只包含空白字符的句子
    ]

    # 对齐句子
    return align_sentences_anchor(
        sentences_a,
        sentences_b,
        window_size=window_size,
        similarity_threshold=similarity_threshold,
        ngram_size=ngram_size,
        offset=offset,
        max_window_expansion=max_window_expansion,
        consecutive_fail_threshold=consecutive_fail_threshold
    )


def get_alignment_statistics(alignment: List[Dict]) -> Dict:
    """
    统计对齐结果

    Args:
        alignment: 对齐结果列表

    Returns:
        统计信息字典
    """
    stats = {
        'total': len(alignment),
        'match': 0,
        'movein': 0,
        'moveout': 0,
        'delete': 0,
        'insert': 0
    }

    for item in alignment:
        item_type = item['type']
        if item_type in stats:
            stats[item_type] += 1

    return stats


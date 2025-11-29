"""
简单快速的句子对齐算法

使用锚点机制和快速相似度算法（Jaccard）进行句子对齐。
适用于改动不大的文本，速度快，内存占用小。
"""

import re
from typing import List, Dict, Set
from src.splitter import split_chinese_sentences


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


def normalize_sentence(sentence: str) -> str:
    """
    标准化句子（用于相似度计算）

    Args:
        sentence: 原始句子

    Returns:
        标准化后的句子
    """
    # 去除首尾空白
    s = sentence.strip()
    # 统一全角空格为半角空格
    s = s.replace('　', ' ')
    # 合并多个连续空格为一个
    s = re.sub(r' +', ' ', s)
    return s


def align_sentences_anchor(
    sentences_a: List[str],
    sentences_b: List[str],
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3
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
        sent_a = normalize_sentence(sentences_a[a_idx])

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

            sent_b = normalize_sentence(sentences_b[b_idx])
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

                sent_b = normalize_sentence(sentences_b[b_idx])
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
    result = rematch_delete_insert_sequences(
        result,
        similarity_threshold,
        ngram_size
    )

    # 后处理：将单独的DELETE项合并到相邻的MATCH组中
    result = merge_delete_into_match(
        result,
        ngram_size
    )

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


def rematch_delete_insert_sequences(
    alignment: List[Dict],
    similarity_threshold: float = 0.6,
    ngram_size: int = 2
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
                            sent_a = normalize_sentence(d_candidate['text'])
                            sent_b = normalize_sentence(ins_candidate['text'])
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

    return result


def merge_delete_into_match(
    alignment: List[Dict],
    ngram_size: int = 2
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
                sent_a = normalize_sentence(merged_a)
                sent_b = normalize_sentence(prev_b)
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
                sent_a = normalize_sentence(merged_a)
                sent_b = normalize_sentence(next_item['b'])
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
                            result[-1]['a_indices'].extend(delete_a_indices)
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
                        next_item['a_indices'] = delete_a_indices + next_item.get('a_indices', [])
                    # 跳过当前DELETE
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
    # 切分句子
    sentences_a = [
        s.strip() for s in split_chinese_sentences(text_a, preserve_formatting)
        if s.strip()
    ]
    sentences_b = [
        s.strip() for s in split_chinese_sentences(text_b, preserve_formatting)
        if s.strip()
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
        'delete': 0,
        'insert': 0
    }

    for item in alignment:
        stats[item['type']] += 1

    return stats


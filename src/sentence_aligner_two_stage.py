"""
两阶段句子对齐算法

第一阶段：使用句子长度序列 + LCS算法快速确定锚点
第二阶段：在锚点约束下使用改进的锚点算法进行精细对齐
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from src.splitter import split_chinese_sentences
from src.sentence_aligner_simple import (
    jaccard_similarity,
    normalize_sentence,
    get_ngrams
)


def compute_sentence_lengths(sentences: List[str], ignore_whitespace: bool = True) -> List[int]:
    """
    计算句子长度序列（忽略空白字符）

    Args:
        sentences: 句子列表
        ignore_whitespace: 是否忽略空白字符（默认True）

    Returns:
        长度列表
    """
    if ignore_whitespace:
        # 移除所有空白字符后计算长度
        return [len(re.sub(r'\s+', '', s)) for s in sentences]
    else:
        return [len(s) for s in sentences]


def compute_length_windows(lengths: List[int], window_size: int = 3) -> List[Tuple[int, ...]]:
    """
    计算长度窗口序列（用于更稳定的匹配）

    使用相邻多个句子的长度组合，提高匹配的稳定性

    Args:
        lengths: 长度列表
        window_size: 窗口大小（相邻几个句子的长度）

    Returns:
        长度窗口序列，每个元素是长度为window_size的元组
    """
    windows = []
    for i in range(len(lengths) - window_size + 1):
        windows.append(tuple(lengths[i:i+window_size]))
    # 对于末尾不足window_size的句子，用最后一个窗口
    if len(lengths) > 0 and len(windows) == 0:
        windows.append(tuple(lengths))
    elif len(lengths) > len(windows):
        # 补充末尾的窗口
        for i in range(len(windows), len(lengths)):
            start = max(0, i - window_size + 1)
            windows.append(tuple(lengths[start:i+1]))
    return windows


def lcs_length_sequence(
    lengths_a: List[int],
    lengths_b: List[int],
    window_size: int = 3,
    min_match_length: int = 2,
    strict_match: bool = True
) -> List[Tuple[int, int]]:
    """
    使用LCS算法在长度序列中找到匹配的锚点

    使用严格匹配：长度必须完全相同（忽略空白字符后）

    Args:
        lengths_a: 原文句子长度列表（已忽略空白字符）
        lengths_b: 校对后句子长度列表（已忽略空白字符）
        window_size: 长度窗口大小（用于更稳定的匹配）
        min_match_length: 最小匹配长度（连续匹配的句子数）
        strict_match: 是否使用严格匹配（长度必须完全相同）

    Returns:
        锚点列表，每个元素是 (a_index, b_index) 表示匹配的句子索引
    """
    if not lengths_a or not lengths_b:
        return []

    if strict_match:
        # 严格匹配：直接比较单个长度，必须完全相同
        # 使用更智能的匹配策略：考虑位置约束，避免跨度过大的匹配
        matches = []
        used_a = set()
        used_b = set()

        # 对于A中的每个句子，在B中查找匹配
        # 使用位置约束：匹配的B索引应该在A索引的合理范围内
        # 允许的最大偏移：考虑到文本可能有少量移动，允许一定偏移
        max_offset_ratio = 0.2  # 允许的最大偏移比例（相对于文本长度）
        max_offset = max(int(len(lengths_a) * max_offset_ratio),
                        int(len(lengths_b) * max_offset_ratio),
                        10)  # 至少允许10个句子的偏移

        for a_idx in range(len(lengths_a)):
            if a_idx in used_a:
                continue

            length_a = lengths_a[a_idx]
            if length_a == 0:  # 跳过空句子
                continue

            # 在B中查找完全相同的长度，考虑位置约束
            best_b_idx = None
            best_offset = max_offset + 1

            # 搜索范围：从当前位置前后一定范围内搜索
            # 使用更严格的搜索范围
            search_start = max(0, a_idx - max_offset)
            search_end = min(len(lengths_b), a_idx + max_offset + 1)

            for b_idx in range(search_start, search_end):
                if b_idx in used_b:
                    continue

                if lengths_b[b_idx] == length_a:
                    # 计算位置偏移
                    offset = abs(b_idx - a_idx)
                    if offset < best_offset:
                        best_offset = offset
                        best_b_idx = b_idx

            # 如果找到匹配且偏移合理，添加为锚点
            if best_b_idx is not None and best_offset <= max_offset:
                matches.append((a_idx, best_b_idx))
                used_a.add(a_idx)
                used_b.add(best_b_idx)

        # 按位置排序
        matches.sort()
        return matches
    else:
        # 使用长度窗口进行匹配（原有逻辑，但阈值更严格）
        windows_a = compute_length_windows(lengths_a, window_size)
        windows_b = compute_length_windows(lengths_b, window_size)

        # 严格匹配：窗口必须完全相同
        matches = []
        used_a = set()
        used_b = set()

        for i in range(len(windows_a)):
            if i in used_a:
                continue
            for j in range(len(windows_b)):
                if j in used_b:
                    continue
                # 严格匹配：窗口必须完全相同
                if windows_a[i] == windows_b[j]:
                    matches.append((i, j))
                    used_a.add(i)
                    used_b.add(j)
                    break

        # 按位置排序
        matches.sort()
        return matches


def align_sentences_two_stage(
    sentences_a: List[str],
    sentences_b: List[str],
    # 第一阶段参数
    length_window_size: int = 3,
    length_similarity_threshold: float = 0.8,
    # 第二阶段参数（使用现有算法的参数）
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3,
    # 多对多匹配参数
    enable_many_to_many: bool = True,
    max_merge_size: int = 3
) -> List[Dict]:
    """
    两阶段句子对齐算法

    第一阶段：使用长度序列 + LCS 确定锚点
    第二阶段：在锚点约束下使用改进的锚点算法

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        length_window_size: 长度窗口大小
        length_similarity_threshold: 长度相似度阈值
        window_size: 第二阶段搜索窗口大小
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        offset: 锚点偏移量
        max_window_expansion: 最大窗口扩展倍数
        consecutive_fail_threshold: 连续失败阈值
        enable_many_to_many: 是否启用多对多匹配
        max_merge_size: 最大合并句子数

    Returns:
        对齐结果列表
    """
    n = len(sentences_a)
    m = len(sentences_b)

    if n == 0 and m == 0:
        return []

    # ========== 第一阶段：使用长度序列确定锚点 ==========
    # 计算长度（忽略空白字符）
    lengths_a = compute_sentence_lengths(sentences_a, ignore_whitespace=True)
    lengths_b = compute_sentence_lengths(sentences_b, ignore_whitespace=True)

    # 使用LCS找到锚点（严格匹配：长度必须完全相同）
    anchors = lcs_length_sequence(
        lengths_a,
        lengths_b,
        window_size=length_window_size,
        strict_match=True  # 使用严格匹配
    )

    # 添加边界锚点（如果还没有）
    if not anchors:
        # 如果没有找到任何锚点，添加首尾锚点
        anchors = [(0, 0), (n - 1, m - 1)]
    else:
        # 确保有首尾锚点
        if anchors[0][0] != 0 or anchors[0][1] != 0:
            anchors.insert(0, (0, 0))
        if anchors[-1][0] != n - 1 or anchors[-1][1] != m - 1:
            anchors.append((n - 1, m - 1))

    # 去重并排序
    anchors = sorted(list(set(anchors)))

    # ========== 第二阶段：在锚点之间分段对齐 ==========
    result = []
    b_used = set()
    anchor_set = set(anchors)  # 用于快速查找锚点

    # 验证锚点质量：检查锚点周围的句子是否真的匹配
    validated_anchors = _validate_anchors(
        anchors, sentences_a, sentences_b, similarity_threshold, ngram_size
    )

    # 在锚点之间分段对齐
    for anchor_idx in range(len(validated_anchors) - 1):
        start_a, start_b = validated_anchors[anchor_idx]
        end_a, end_b = validated_anchors[anchor_idx + 1]

        # 计算分段大小，用于动态调整搜索窗口
        segment_size_a = end_a - start_a + 1
        segment_size_b = end_b - start_b + 1
        segment_size = max(segment_size_a, segment_size_b)

        # 根据分段大小动态调整搜索窗口
        # 分段越大，搜索窗口越大（但不超过分段大小）
        dynamic_window = min(
            max(window_size, segment_size // 2),
            segment_size
        )

        # 提取锚点之间的句子段（包括起始锚点，不包括结束锚点）
        segment_a = sentences_a[start_a:end_a + 1]
        segment_b = sentences_b[start_b:end_b + 1]

        # 调整索引映射
        segment_a_start = start_a
        segment_b_start = start_b

        if segment_a and segment_b:
            # 标记段内的锚点，避免重复匹配
            segment_anchors = {
                (i - segment_a_start, j - segment_b_start)
                for i, j in anchor_set
                if start_a <= i <= end_a and start_b <= j <= end_b
            }

            # 在段内使用改进的锚点算法对齐
            # 在分段边界使用更大的搜索窗口
            is_boundary_segment = (anchor_idx == 0 or
                                  anchor_idx == len(validated_anchors) - 2)
            boundary_window_multiplier = 1.5 if is_boundary_segment else 1.0

            segment_result = _align_segment_with_anchor(
                segment_a,
                segment_b,
                segment_a_start,
                segment_b_start,
                window_size=int(dynamic_window * boundary_window_multiplier),
                similarity_threshold=similarity_threshold,
                ngram_size=ngram_size,
                offset=offset,
                max_window_expansion=max_window_expansion,
                consecutive_fail_threshold=consecutive_fail_threshold,
                enable_many_to_many=enable_many_to_many,
                max_merge_size=max_merge_size,
                b_used=b_used,
                segment_anchors=segment_anchors
            )

            result.extend(segment_result)

            # 更新已使用的B索引
            for item in segment_result:
                if item.get('b_indices'):
                    b_used.update(item['b_indices'])

    # 处理B中未匹配的句子（新增）
    # 按照B的原始顺序插入
    b_idx_to_result_pos = {}
    for pos, item in enumerate(result):
        if item.get('b_indices'):
            for b_idx in item['b_indices']:
                b_idx_to_result_pos[b_idx] = pos

    for b_idx in range(m):
        if b_idx in b_used:
            continue

        # 找到插入位置
        insert_pos = len(result)
        if b_idx > 0:
            prev_b_idx = b_idx - 1
            if prev_b_idx in b_idx_to_result_pos:
                insert_pos = b_idx_to_result_pos[prev_b_idx] + 1

        item = {
            'type': 'insert',
            'a': None,
            'b': sentences_b[b_idx],
            'similarity': None,
            'a_indices': [],
            'b_indices': [b_idx]
        }
        result.insert(insert_pos, item)

        # 更新映射
        b_idx_to_result_pos = {}
        for pos, item in enumerate(result):
            if item.get('b_indices'):
                for b_idx in item['b_indices']:
                    b_idx_to_result_pos[b_idx] = pos

    # 后处理：DELETE-INSERT重新匹配和DELETE合并到MATCH
    from src.sentence_aligner_simple import (
        rematch_delete_insert_sequences,
        merge_delete_into_match
    )

    result = rematch_delete_insert_sequences(
        result,
        similarity_threshold,
        ngram_size
    )

    result = merge_delete_into_match(result, ngram_size)

    return result


def _validate_anchors(
    anchors: List[Tuple[int, int]],
    sentences_a: List[str],
    sentences_b: List[str],
    similarity_threshold: float,
    ngram_size: int
) -> List[Tuple[int, int]]:
    """
    验证锚点质量：检查锚点周围的句子是否真的匹配

    Args:
        anchors: 原始锚点列表
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小

    Returns:
        验证后的锚点列表
    """
    from src.sentence_aligner_simple import jaccard_similarity, normalize_sentence

    validated = []

    for a_idx, b_idx in anchors:
        # 检查索引是否有效
        if a_idx >= len(sentences_a) or b_idx >= len(sentences_b):
            continue

        # 验证锚点：检查句子是否真的相似
        sent_a = normalize_sentence(sentences_a[a_idx])
        sent_b = normalize_sentence(sentences_b[b_idx])
        similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

        # 如果相似度足够高，保留锚点
        # 对于长度匹配的锚点，相似度阈值可以稍微降低（因为长度已经匹配）
        min_similarity = similarity_threshold * 0.7  # 降低30%的阈值

        # 如果相似度足够高，保留锚点
        if similarity >= min_similarity:
            validated.append((a_idx, b_idx))
        # 如果相似度太低，可能是错误的锚点，跳过
        # 但保留边界锚点（首尾）和长度完全相同的锚点
        elif a_idx == 0 and b_idx == 0:
            validated.append((a_idx, b_idx))  # 保留起始锚点
        elif a_idx == len(sentences_a) - 1 and b_idx == len(sentences_b) - 1:
            validated.append((a_idx, b_idx))  # 保留结束锚点
        elif similarity >= min_similarity * 0.5:  # 即使相似度较低，如果长度匹配也保留
            # 检查长度是否真的相同（忽略空白字符）
            len_a = len(re.sub(r'\s+', '', sentences_a[a_idx]))
            len_b = len(re.sub(r'\s+', '', sentences_b[b_idx]))
            if len_a == len_b and len_a > 0:  # 长度相同且非空
                validated.append((a_idx, b_idx))

    # 确保有首尾锚点
    if not validated or validated[0] != (0, 0):
        validated.insert(0, (0, 0))
    if not validated or validated[-1] != (len(sentences_a) - 1, len(sentences_b) - 1):
        validated.append((len(sentences_a) - 1, len(sentences_b) - 1))

    return sorted(list(set(validated)))


def _align_segment_with_anchor(
    segment_a: List[str],
    segment_b: List[str],
    segment_a_start: int,
    segment_b_start: int,
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3,
    enable_many_to_many: bool = True,
    max_merge_size: int = 3,
    b_used: Optional[Set[int]] = None,
    segment_anchors: Optional[Set[Tuple[int, int]]] = None
) -> List[Dict]:
    """
    在锚点约束的段内使用改进的锚点算法对齐

    这是第二阶段的实现，基于现有算法但增加了多对多匹配支持

    Args:
        segment_a: 段内原文句子列表
        segment_b: 段内校对后句子列表
        segment_a_start: 段在原文中的起始索引
        segment_b_start: 段在校对后文本中的起始索引
        b_used: 已使用的B索引集合（用于跨段协调）
        其他参数同align_sentences_two_stage
    """
    n = len(segment_a)
    m = len(segment_b)

    if n == 0 and m == 0:
        return []

    if b_used is None:
        b_used = set()
    if segment_anchors is None:
        segment_anchors = set()

    result = []
    anchor = 0
    a_idx = 0
    segment_b_used = set()  # 段内已使用的B索引
    consecutive_fails = 0
    current_window = window_size

    # 先处理段内的锚点匹配
    for seg_a_idx, seg_b_idx in segment_anchors:
        if seg_a_idx < len(segment_a) and seg_b_idx < len(segment_b):
            a_original_idx = segment_a_start + seg_a_idx
            b_original_idx = segment_b_start + seg_b_idx
            result.append({
                'type': 'match',
                'a': segment_a[seg_a_idx],
                'b': segment_b[seg_b_idx],
                'similarity': 1.0,  # 锚点匹配假设为完全匹配
                'a_indices': [a_original_idx],
                'b_indices': [b_original_idx]
            })
            b_used.add(b_original_idx)
            segment_b_used.add(seg_b_idx)

    while a_idx < n:
        # 跳过已经是锚点的句子
        if any(seg_a_idx == a_idx for seg_a_idx, _ in segment_anchors):
            a_idx += 1
            continue

        sent_a = normalize_sentence(segment_a[a_idx])

        # 动态调整搜索窗口
        if consecutive_fails >= consecutive_fail_threshold:
            expansion_factor = min(
                max_window_expansion,
                1 + (consecutive_fails - consecutive_fail_threshold) // 2
            )
            current_window = window_size * expansion_factor
        else:
            current_window = window_size

        # 确定搜索窗口
        # 在分段边界处使用更大的搜索范围
        is_near_start = a_idx < 3  # 接近分段开始
        is_near_end = a_idx >= n - 3  # 接近分段结束

        if is_near_start or is_near_end:
            # 在边界处扩大搜索窗口
            boundary_expansion = 1.5
            expanded_window = int(current_window * boundary_expansion)
        else:
            expanded_window = current_window

        window_start = max(0, anchor - expanded_window)
        window_end = min(m, anchor + expanded_window + 1)

        # 在窗口内搜索最相似的句子
        best_match_idx = None
        best_similarity = 0.0
        best_b_idx_in_window = None

        for b_idx in range(window_start, window_end):
            # 检查是否在全局或段内已使用
            b_global_idx = segment_b_start + b_idx
            if b_global_idx in b_used or b_idx in segment_b_used:
                continue

            sent_b = normalize_sentence(segment_b[b_idx])
            similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = b_idx if similarity >= similarity_threshold else None
                best_b_idx_in_window = b_idx

        # 如果启用多对多匹配且未找到匹配，尝试合并匹配
        if enable_many_to_many and best_match_idx is None:
            best_match_idx, best_similarity = _try_many_to_many_match(
                segment_a, a_idx,
                segment_b, window_start, window_end,
                segment_b_used, segment_b_start, b_used,
                similarity_threshold, ngram_size, max_merge_size
            )

        # 全局搜索回退（在段内）
        if best_match_idx is None and consecutive_fails >= consecutive_fail_threshold:
            for b_idx in range(m):
                b_global_idx = segment_b_start + b_idx
                if b_global_idx in b_used or b_idx in segment_b_used:
                    continue

                sent_b = normalize_sentence(segment_b[b_idx])
                similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

                if similarity > best_similarity:
                    best_similarity = similarity
                    if similarity >= similarity_threshold:
                        best_match_idx = b_idx
                    best_b_idx_in_window = b_idx

        # 判断是否匹配
        if best_match_idx is not None and best_similarity >= similarity_threshold:
            # 匹配成功
            a_original_idx = segment_a_start + a_idx
            b_original_idx = segment_b_start + best_match_idx
            item = {
                'type': 'match',
                'a': segment_a[a_idx],
                'b': segment_b[best_match_idx],
                'similarity': best_similarity,
                'a_indices': [a_original_idx],
                'b_indices': [b_original_idx]
            }
            result.append(item)

            anchor = best_match_idx + offset
            b_used.add(b_original_idx)
            segment_b_used.add(best_match_idx)
            consecutive_fails = 0
        else:
            # 未找到匹配，视为删除
            a_original_idx = segment_a_start + a_idx
            result.append({
                'type': 'delete',
                'a': segment_a[a_idx],
                'b': None,
                'similarity': None,
                'a_indices': [a_original_idx],
                'b_indices': []
            })

            if best_b_idx_in_window is not None and best_similarity > 0.3:
                anchor = max(anchor, best_b_idx_in_window)

            consecutive_fails += 1

        a_idx += 1

    # 处理段内B中未匹配的句子（新增）- 这些会在主函数中统一处理
    # 这里只返回段内的对齐结果

    return result


def _try_many_to_many_match(
    sentences_a: List[str],
    a_idx: int,
    sentences_b: List[str],
    window_start: int,
    window_end: int,
    segment_b_used: Set[int],
    segment_b_start: int,
    b_used: Set[int],
    similarity_threshold: float,
    ngram_size: int,
    max_merge_size: int
) -> Tuple[Optional[int], float]:
    """
    尝试多对多匹配

    Args:
        sentences_a: 原文句子列表
        a_idx: 当前A的索引
        sentences_b: 校对后句子列表
        window_start: 窗口起始位置
        window_end: 窗口结束位置
        b_used: 已使用的B索引集合
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        max_merge_size: 最大合并句子数

    Returns:
        (匹配的B索引, 相似度) 或 (None, 0.0)
    """
    sent_a = normalize_sentence(sentences_a[a_idx])

    # 尝试合并A的相邻句子（最多max_merge_size个）
    best_match_idx = None
    best_similarity = 0.0

    for merge_size in range(2, min(max_merge_size + 1, len(sentences_a) - a_idx + 1)):
        # 合并A的句子
        merged_a = ''.join(sentences_a[a_idx:a_idx + merge_size])
        merged_a_norm = normalize_sentence(merged_a)

        # 在窗口内搜索匹配的B句子（单个或合并）
        for b_idx in range(window_start, window_end):
            b_global_idx = segment_b_start + b_idx
            if b_global_idx in b_used or b_idx in segment_b_used:
                continue

            # 尝试单个B句子
            sent_b = normalize_sentence(sentences_b[b_idx])
            similarity = jaccard_similarity(merged_a_norm, sent_b, ngram_size)

            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match_idx = b_idx

            # 尝试合并B的相邻句子
            for b_merge_size in range(2, min(max_merge_size + 1, len(sentences_b) - b_idx + 1)):
                if b_idx + b_merge_size > window_end:
                    break

                # 检查是否都被使用
                if any(segment_b_start + i in b_used or i in segment_b_used
                       for i in range(b_idx, b_idx + b_merge_size)):
                    continue

                merged_b = ''.join(sentences_b[b_idx:b_idx + b_merge_size])
                merged_b_norm = normalize_sentence(merged_b)
                similarity = jaccard_similarity(merged_a_norm, merged_b_norm, ngram_size)

                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_match_idx = b_idx

    return best_match_idx, best_similarity


def align_texts_two_stage(
    text_a: str,
    text_b: str,
    preserve_formatting: bool = True,
    # 第一阶段参数
    length_window_size: int = 3,
    length_similarity_threshold: float = 0.8,
    # 第二阶段参数
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1,
    max_window_expansion: int = 3,
    consecutive_fail_threshold: int = 3,
    # 多对多匹配参数
    enable_many_to_many: bool = True,
    max_merge_size: int = 3
) -> List[Dict]:
    """
    对齐两个完整文本（使用两阶段算法）

    Args:
        text_a: 原文
        text_b: 校对后文本
        preserve_formatting: 是否保留格式
        length_window_size: 长度窗口大小
        length_similarity_threshold: 长度相似度阈值
        window_size: 第二阶段搜索窗口大小
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        offset: 锚点偏移量
        max_window_expansion: 最大窗口扩展倍数
        consecutive_fail_threshold: 连续失败阈值
        enable_many_to_many: 是否启用多对多匹配
        max_merge_size: 最大合并句子数

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
    return align_sentences_two_stage(
        sentences_a,
        sentences_b,
        length_window_size=length_window_size,
        length_similarity_threshold=length_similarity_threshold,
        window_size=window_size,
        similarity_threshold=similarity_threshold,
        ngram_size=ngram_size,
        offset=offset,
        max_window_expansion=max_window_expansion,
        consecutive_fail_threshold=consecutive_fail_threshold,
        enable_many_to_many=enable_many_to_many,
        max_merge_size=max_merge_size
    )


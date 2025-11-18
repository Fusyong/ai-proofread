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
    offset: int = 1
) -> List[Dict]:
    """
    使用锚点机制对齐句子（贪心算法）

    算法流程：
    1. 从A的第一个句子开始
    2. 在B中从当前锚点位置左右window_size范围内搜索最相似的句子
    3. 如果找到相似度超过threshold的句子，更新锚点
    4. 处理A的下一个句子，锚点从当前位置+offset开始

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        window_size: 搜索窗口大小（锚点左右各window_size个句子）
        similarity_threshold: 相似度阈值，超过此值才认为匹配
        ngram_size: n-gram大小，用于Jaccard相似度计算
        offset: 下一个句子的锚点偏移量（默认1，即下一个位置）

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

    # 按照A文件的顺序处理
    while a_idx < n:
        sent_a = normalize_sentence(sentences_a[a_idx])

        # 确定搜索窗口
        window_start = max(0, anchor - window_size)
        window_end = min(m, anchor + window_size + 1)

        # 在窗口内搜索最相似的句子
        best_match_idx = None
        best_similarity = 0.0

        for b_idx in range(window_start, window_end):
            # 跳过已匹配的句子
            if b_idx in b_used:
                continue

            sent_b = normalize_sentence(sentences_b[b_idx])
            similarity = jaccard_similarity(sent_a, sent_b, ngram_size)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = b_idx

        # 判断是否匹配
        if best_match_idx is not None and best_similarity >= similarity_threshold:
            # 匹配成功
            item = {
                'type': 'match',
                'a': sentences_a[a_idx],
                'b': sentences_b[best_match_idx],
                'similarity': best_similarity,
                'a_index': a_idx,
                'b_index': best_match_idx
            }
            result.append(item)
            b_to_result[best_match_idx] = item

            # 更新锚点和标记
            anchor = best_match_idx + offset
            b_used.add(best_match_idx)
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
            # 锚点不移动或小幅移动
            # anchor保持不变或+1

        a_idx += 1

    # 处理B中剩余的未匹配句子（视为新增）
    # 按照B的原始顺序，紧跟在它上一句（在B中的前一句）的后面

    # 创建B索引到结果位置的映射（包括匹配项和已插入的新增项）
    b_idx_to_result_pos = {}
    for pos, item in enumerate(result):
        if item.get('b_index') is not None:
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
            if item.get('b_index') is not None:
                b_idx_to_result_pos[item['b_index']] = pos

    # 结果已经按照A、B文件的原始顺序排列
    # - 匹配和删除按A的顺序
    # - 新增按B的原始顺序插入到合适位置

    return result


def align_texts_anchor(
    text_a: str,
    text_b: str,
    preserve_formatting: bool = True,
    window_size: int = 10,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2,
    offset: int = 1
) -> List[Dict]:
    """
    对齐两个完整文本（使用锚点算法）

    Args:
        text_a: 原文
        text_b: 校对后文本
        preserve_formatting: 是否保留格式
        window_size: 搜索窗口大小
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小
        offset: 锚点偏移量

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
        offset=offset
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


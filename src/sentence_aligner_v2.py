"""
新版本句子对齐算法（基于双链结构）

核心特性：
1. 双链结构维护对齐关系
2. 分阶段对齐：全等匹配 + 相似度匹配
3. 规范化处理：比较时规范化，结果用原始文本
4. 分组与交叉处理
5. 多阶段调试支持
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.splitter import split_chinese_sentences_with_line_numbers
from src.sentence_aligner import jaccard_similarity


class AlignmentType(Enum):
    """对齐类型"""
    MATCH = "match"
    DELETE = "delete"
    INSERT = "insert"
    MOVEIN = "movein"
    MOVEOUT = "moveout"


@dataclass
class Sentence:
    """句子数据结构"""
    text: str  # 原始文本
    normalized: str  # 规范化文本（用于比较）
    index: int  # 句子索引（从0开始）
    line_number: int  # 行号（从1开始）
    matched: bool = False  # 是否已匹配


@dataclass
class AlignmentItem:
    """对齐项数据结构"""
    type: AlignmentType
    a: Optional[str] = None  # 原文句子（原始文本）
    b: Optional[str] = None  # 校对后句子（原始文本）
    a_indices: List[int] = field(default_factory=list)  # 原文句子索引列表
    b_indices: List[int] = field(default_factory=list)  # 校对后句子索引列表
    similarity: Optional[float] = None  # 相似度值
    a_line_numbers: List[int] = field(default_factory=list)  # 原文行号列表
    b_line_numbers: List[int] = field(default_factory=list)  # 校对后行号列表
    offset: Optional[int] = None  # 偏移量（b_index - a_index，用于分组）
    group_id: Optional[int] = None  # 组ID（用于标识同一组匹配）

    def to_dict(self) -> Dict:
        """转换为字典格式（兼容旧格式）"""
        result = {
            'type': self.type.value,
            'a': self.a,
            'b': self.b,
            'similarity': self.similarity,
        }

        # 索引处理（兼容旧格式）
        if len(self.a_indices) == 1:
            result['a_index'] = self.a_indices[0]
        if len(self.a_indices) > 1:
            result['a_indices'] = self.a_indices
        if len(self.b_indices) == 1:
            result['b_index'] = self.b_indices[0]
        if len(self.b_indices) > 1:
            result['b_indices'] = self.b_indices

        # 行号处理
        if len(self.a_line_numbers) == 1:
            result['a_line_number'] = self.a_line_numbers[0]
        if len(self.a_line_numbers) > 1:
            result['a_line_numbers'] = self.a_line_numbers
        if len(self.b_line_numbers) == 1:
            result['b_line_number'] = self.b_line_numbers[0]
        if len(self.b_line_numbers) > 1:
            result['b_line_numbers'] = self.b_line_numbers

        return result


def normalize_for_comparison(text: str) -> str:
    """
    规范化文本用于比较

    规则：
    1. 删除所有空格（包括全角、半角）
    2. 英文引号统一改为中文引号
    3. 统一标点符号（可选）

    Args:
        text: 原始文本

    Returns:
        规范化后的文本
    """
    if not text:
        return ""

    # 1. 删除所有空格
    normalized = re.sub(r'[\s\u3000]+', '', text)  # \u3000是全角空格

    # 2. 英文引号转换为中文引号
    # 单引号
    normalized = normalized.replace("'", "'")  # 左单引号
    normalized = normalized.replace("'", "'")  # 右单引号
    # 双引号
    normalized = normalized.replace('"', '"')  # 左双引号
    normalized = normalized.replace('"', '"')  # 右双引号

    # 3. 统一标点符号（可选，根据需求决定是否启用）
    # normalized = normalized.replace(':', '：')
    # normalized = normalized.replace(',', '，')

    return normalized


def prepare_sentences(text: str, preserve_formatting: bool = True) -> List[Sentence]:
    """
    准备句子列表（包含原始文本和规范化文本）

    Args:
        text: 原始文本
        preserve_formatting: 是否保留格式

    Returns:
        句子列表
    """
    # 使用现有的切分函数（带行号）
    sentences_with_lines = split_chinese_sentences_with_line_numbers(text, preserve_formatting)

    sentences = []
    for idx, (sentence_text, start_line, _) in enumerate(sentences_with_lines):
        if not sentence_text.strip():
            continue

        normalized = normalize_for_comparison(sentence_text)
        sentence = Sentence(
            text=sentence_text,
            normalized=normalized,
            index=idx,
            line_number=start_line,  # 使用起始行号
            matched=False
        )
        sentences.append(sentence)

    return sentences


def validate_dual_chain(alignment: List[AlignmentItem],
                       sentences_a: List[Sentence],
                       sentences_b: List[Sentence]) -> Tuple[bool, List[str]]:
    """
    验证双链的连续性和完整性

    Args:
        alignment: 对齐结果列表
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    # 检查完整性：所有句子都应该被包含
    a_used = set()
    b_used = set()

    for item in alignment:
        # 收集A侧索引
        if item.a_indices:
            for idx in item.a_indices:
                if idx in a_used:
                    errors.append(f"A侧句子 {idx} 被重复使用")
                a_used.add(idx)
        # 收集B侧索引
        if item.b_indices:
            for idx in item.b_indices:
                if idx in b_used:
                    errors.append(f"B侧句子 {idx} 被重复使用")
                b_used.add(idx)

    # 检查A侧完整性
    a_missing = set(range(len(sentences_a))) - a_used
    if a_missing:
        errors.append(f"A侧缺失句子索引: {sorted(a_missing)}")

    # 检查B侧完整性
    b_missing = set(range(len(sentences_b))) - b_used
    if b_missing:
        errors.append(f"B侧缺失句子索引: {sorted(b_missing)}")

    # 检查连续性（可选，根据需求决定是否严格检查）
    # 这里可以添加更严格的连续性检查逻辑

    return len(errors) == 0, errors


def get_alignment_statistics_v2(alignment: List) -> Dict:
    """
    统计对齐结果（新版本）

    支持AlignmentItem对象列表或字典列表

    Args:
        alignment: 对齐结果列表（AlignmentItem对象或字典）

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
        # 支持字典和对象两种格式
        if isinstance(item, dict):
            item_type = item.get('type', '')
        else:
            item_type = item.type.value if hasattr(item, 'type') else ''

        if item_type in stats:
            stats[item_type] += 1

    return stats


def align_sentences_exact_match(sentences_a: List[Sentence],
                                sentences_b: List[Sentence]) -> List[AlignmentItem]:
    """
    阶段一：全等匹配

    找到规范化后完全相同的句子，并维护双链的连续性

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表

    Returns:
        对齐结果列表（包含全等匹配项和未匹配项的占位符）
    """
    alignment = []
    a_used = set()  # A侧已匹配的索引
    b_used = set()  # B侧已匹配的索引

    # 创建B侧规范化文本到索引的映射（用于快速查找）
    # 注意：可能有多个句子规范化后相同，所以使用列表
    b_normalized_map: Dict[str, List[int]] = {}
    for idx, sent_b in enumerate(sentences_b):
        normalized = sent_b.normalized
        if normalized not in b_normalized_map:
            b_normalized_map[normalized] = []
        b_normalized_map[normalized].append(idx)

    # 第一遍：找到所有全等匹配
    for a_idx, sent_a in enumerate(sentences_a):
        if a_idx in a_used:
            continue

        normalized_a = sent_a.normalized
        if normalized_a in b_normalized_map:
            # 找到匹配的B侧句子
            # 优先选择索引最接近的（保持连续性）
            candidates = [b_idx for b_idx in b_normalized_map[normalized_a] if b_idx not in b_used]

            if candidates:
                # 选择索引最接近的候选（如果有多个匹配）
                # 这里简单选择第一个，后续可以优化为选择索引最接近的
                b_idx = candidates[0]

                # 创建匹配项
                item = AlignmentItem(
                    type=AlignmentType.MATCH,
                    a=sentences_a[a_idx].text,
                    b=sentences_b[b_idx].text,
                    a_indices=[a_idx],
                    b_indices=[b_idx],
                    similarity=1.0,  # 全等匹配相似度为1.0
                    a_line_numbers=[sentences_a[a_idx].line_number],
                    b_line_numbers=[sentences_b[b_idx].line_number],
                    offset=b_idx - a_idx
                )
                alignment.append(item)

                # 标记为已使用
                a_used.add(a_idx)
                b_used.add(b_idx)
                sentences_a[a_idx].matched = True
                sentences_b[b_idx].matched = True

    # 第二遍：按A侧顺序插入未匹配的句子，维护双链连续性
    # 策略：按A侧顺序处理，对于未匹配的A侧句子，插入delete项
    # 对于未匹配的B侧句子，在合适位置插入insert项

    # 先按A侧顺序插入delete项
    result = []
    a_idx = 0
    b_idx = 0

    # 创建已匹配项的索引映射，用于确定插入位置
    a_to_item = {}  # A侧索引 -> 对齐项
    b_to_item = {}  # B侧索引 -> 对齐项

    for item in alignment:
        if item.a_indices:
            for idx in item.a_indices:
                a_to_item[idx] = item
        if item.b_indices:
            for idx in item.b_indices:
                b_to_item[idx] = item

    # 按A侧顺序构建结果
    for a_idx in range(len(sentences_a)):
        if a_idx in a_used:
            # 已匹配，找到对应的对齐项
            if a_idx in a_to_item:
                item = a_to_item[a_idx]
                # 检查是否已经添加（避免重复）
                if item not in result:
                    result.append(item)
        else:
            # 未匹配，创建delete项
            delete_item = AlignmentItem(
                type=AlignmentType.DELETE,
                a=sentences_a[a_idx].text,
                b=None,
                a_indices=[a_idx],
                b_indices=[],
                similarity=None,
                a_line_numbers=[sentences_a[a_idx].line_number],
                b_line_numbers=[],
                offset=None
            )
            result.append(delete_item)

    # 处理B侧未匹配的句子，插入到合适位置
    # 策略：在B侧已匹配项之后插入对应的insert项
    # 需要找到每个B侧未匹配句子应该插入的位置

    # 创建B侧索引到结果位置的映射
    b_idx_to_result_pos = {}
    for pos, item in enumerate(result):
        if item.b_indices:
            for b_idx in item.b_indices:
                b_idx_to_result_pos[b_idx] = pos

    # 按B侧顺序处理未匹配的句子
    insert_items = []  # [(插入位置, item), ...]

    for b_idx in range(len(sentences_b)):
        if b_idx in b_used:
            continue

        # 找到插入位置：在b_idx-1之后
        insert_pos = len(result)  # 默认插入到末尾

        if b_idx > 0:
            # 查找前一个B侧句子在结果中的位置
            prev_b_idx = b_idx - 1
            if prev_b_idx in b_idx_to_result_pos:
                insert_pos = b_idx_to_result_pos[prev_b_idx] + 1
            else:
                # 前一句也是未匹配的，继续往前找（最多查找10次，避免无限循环）
                for p_idx in range(prev_b_idx, max(-1, prev_b_idx - 10), -1):
                    if p_idx in b_idx_to_result_pos:
                        insert_pos = b_idx_to_result_pos[p_idx] + 1
                        break

        # 创建insert项
        insert_item = AlignmentItem(
            type=AlignmentType.INSERT,
            a=None,
            b=sentences_b[b_idx].text,
            a_indices=[],
            b_indices=[b_idx],
            similarity=None,
            a_line_numbers=[],
            b_line_numbers=[sentences_b[b_idx].line_number],
            offset=None
        )

        insert_items.append((insert_pos, b_idx, insert_item))  # 添加b_idx用于排序

    # 按插入位置排序（从后往前插入，避免位置变化）
    # 对于相同插入位置的项，按B侧索引降序排序
    # 这样从后往前插入时，先插入索引大的，后插入索引小的，最终顺序是升序的
    insert_items.sort(key=lambda x: (x[0], x[1]), reverse=True)  # 位置降序，b_idx降序

    # 插入insert项（从后往前插入，避免位置偏移）
    for insert_pos, b_idx, insert_item in insert_items:
        result.insert(insert_pos, insert_item)

    return result


def identify_processing_units(alignment: List[AlignmentItem]) -> List[Tuple[int, int, str]]:
    """
    识别处理单元：连续的insert或delete序列

    Args:
        alignment: 对齐结果列表

    Returns:
        处理单元列表，每个元素为 (start_idx, end_idx, unit_type)
        unit_type: 'delete' 或 'insert'
    """
    units = []
    i = 0

    while i < len(alignment):
        item = alignment[i]

        # 如果是delete或insert，查找连续的序列
        if item.type == AlignmentType.DELETE:
            start_idx = i
            # 查找连续的delete项
            while i < len(alignment) and alignment[i].type == AlignmentType.DELETE:
                i += 1
            end_idx = i - 1
            units.append((start_idx, end_idx, 'delete'))
        elif item.type == AlignmentType.INSERT:
            start_idx = i
            # 查找连续的insert项
            while i < len(alignment) and alignment[i].type == AlignmentType.INSERT:
                i += 1
            end_idx = i - 1
            units.append((start_idx, end_idx, 'insert'))
        else:
            i += 1

    return units


def compare_processing_units(
    unit_a_items: List[AlignmentItem],
    unit_b_items: List[AlignmentItem],
    sentences_a: List[Sentence],  # 保留用于后续扩展（如行号查找）
    sentences_b: List[Sentence],  # 保留用于后续扩展（如行号查找）
    similarity_threshold: float,
    ngram_size: int
) -> Tuple[bool, float, Optional[AlignmentItem]]:
    """
    比较两个处理单元

    策略：
    1. 先整体比较
    2. 如果整体比较失败，按较短一方的长度从较长一方截取进行比较

    Args:
        unit_a_items: A侧处理单元（delete项列表）
        unit_b_items: B侧处理单元（insert项列表）
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小

    Returns:
        (是否匹配成功, 相似度值, 匹配项或None)
    """
    # 收集A侧和B侧的文本
    a_texts = []
    a_indices = []
    a_line_numbers = []
    for item in unit_a_items:
        if item.a:
            a_texts.append(item.a)
            a_indices.extend(item.a_indices)
            a_line_numbers.extend(item.a_line_numbers)

    b_texts = []
    b_indices = []
    b_line_numbers = []
    for item in unit_b_items:
        if item.b:
            b_texts.append(item.b)
            b_indices.extend(item.b_indices)
            b_line_numbers.extend(item.b_line_numbers)

    if not a_texts or not b_texts:
        return False, 0.0, None

    # 合并文本
    a_merged = ''.join(a_texts)
    b_merged = ''.join(b_texts)

    # 规范化
    a_normalized = normalize_for_comparison(a_merged)
    b_normalized = normalize_for_comparison(b_merged)

    # 1. 整体比较
    similarity = jaccard_similarity(a_normalized, b_normalized, ngram_size)

    if similarity >= similarity_threshold:
        # 整体匹配成功
        match_item = AlignmentItem(
            type=AlignmentType.MATCH,
            a=a_merged,
            b=b_merged,
            a_indices=a_indices,
            b_indices=b_indices,
            similarity=similarity,
            a_line_numbers=a_line_numbers,
            b_line_numbers=b_line_numbers,
            offset=b_indices[0] - a_indices[0] if a_indices and b_indices else None
        )
        return True, similarity, match_item

    # 2. 截取比较：按较短一方的长度从较长一方截取
    if len(a_normalized) < len(b_normalized):
        # A侧较短，从B侧截取相同长度
        b_truncated = b_normalized[:len(a_normalized)]
        truncated_similarity = jaccard_similarity(a_normalized, b_truncated, ngram_size)
        if truncated_similarity > similarity:
            similarity = truncated_similarity
    elif len(b_normalized) < len(a_normalized):
        # B侧较短，从A侧截取相同长度
        a_truncated = a_normalized[:len(b_normalized)]
        truncated_similarity = jaccard_similarity(a_truncated, b_normalized, ngram_size)
        if truncated_similarity > similarity:
            similarity = truncated_similarity

    if similarity >= similarity_threshold:
        # 截取匹配成功
        match_item = AlignmentItem(
            type=AlignmentType.MATCH,
            a=a_merged,
            b=b_merged,
            a_indices=a_indices,
            b_indices=b_indices,
            similarity=similarity,
            a_line_numbers=a_line_numbers,
            b_line_numbers=b_line_numbers,
            offset=b_indices[0] - a_indices[0] if a_indices and b_indices else None
        )
        return True, similarity, match_item

    return False, similarity, None


def align_sentences_similarity(sentences_a: List[Sentence],
                               sentences_b: List[Sentence],
                               alignment: List[AlignmentItem],
                               similarity_threshold: float = 0.6,
                               ngram_size: int = 2) -> List[AlignmentItem]:
    """
    阶段二：相似度匹配

    处理未匹配的句子，使用相似度判断

    策略：
    1. 识别处理单元（连续的insert/delete序列）
    2. 对每个delete单元，尝试与insert单元匹配
    3. 先整体比较，如果失败再截取比较

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        alignment: 阶段一的对齐结果
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小

    Returns:
        完整的对齐结果列表
    """
    # 识别处理单元
    units = identify_processing_units(alignment)

    # 分离delete和insert单元
    delete_units = [(start, end) for start, end, unit_type in units if unit_type == 'delete']
    insert_units = [(start, end) for start, end, unit_type in units if unit_type == 'insert']

    # 记录匹配关系：delete单元 -> insert单元 -> match项
    matches = {}  # {(d_start, d_end): ((i_start, i_end), match_item)}
    used_insert_units = set()

    # 对每个delete单元，尝试与insert单元匹配
    for d_start, d_end in delete_units:
        delete_items = [alignment[i] for i in range(d_start, d_end + 1)]

        # 尝试与每个未使用的insert单元匹配
        best_match = None
        best_similarity = 0.0
        best_insert_range = None

        for i_start, i_end in insert_units:
            if (i_start, i_end) in used_insert_units:
                continue

            insert_items = [alignment[i] for i in range(i_start, i_end + 1)]

            # 比较处理单元
            matched, similarity, match_item = compare_processing_units(
                delete_items, insert_items,
                sentences_a, sentences_b,
                similarity_threshold, ngram_size
            )

            if matched and similarity > best_similarity:
                best_match = match_item
                best_similarity = similarity
                best_insert_range = (i_start, i_end)

        # 如果找到匹配，记录匹配关系
        if best_match is not None:
            matches[(d_start, d_end)] = (best_insert_range, best_match)
            used_insert_units.add(best_insert_range)

    # 重建结果列表：替换匹配的delete和insert单元为match项
    # 创建已处理范围的集合
    processed_ranges = set()  # {(start, end), ...}
    for (d_start, d_end), (insert_range, match_item) in matches.items():
        i_start, i_end = insert_range
        processed_ranges.add((d_start, d_end))
        processed_ranges.add((i_start, i_end))

    result = []
    i = 0

    while i < len(alignment):
        # 检查当前位置是否在某个已处理的范围中
        in_processed_range = False
        for start, end in processed_ranges:
            if start <= i <= end:
                # 如果在delete单元中且已匹配，插入match项
                if (start, end) in matches:
                    insert_range, match_item = matches[(start, end)]
                    result.append(match_item)
                    # 标记对应的insert单元也已处理
                    i_start, i_end = insert_range
                    processed_ranges.add((i_start, i_end))
                # 跳过整个范围
                i = end + 1
                in_processed_range = True
                break

        if in_processed_range:
            continue

        # 检查当前位置是否在某个delete单元中（未匹配的）
        in_delete_unit = False
        for d_start, d_end in delete_units:
            if d_start <= i <= d_end and (d_start, d_end) not in processed_ranges:
                # 未匹配的delete单元，保留原样
                result.append(alignment[i])
                i += 1
                in_delete_unit = True
                break

        if in_delete_unit:
            continue

        # 检查当前位置是否在某个insert单元中（未匹配的）
        in_insert_unit = False
        for i_start, i_end in insert_units:
            if i_start <= i <= i_end and (i_start, i_end) not in processed_ranges:
                # 未匹配的insert单元，保留原样
                result.append(alignment[i])
                i += 1
                in_insert_unit = True
                break

        if not in_insert_unit:
            # 普通项（match等），直接添加
            result.append(alignment[i])
            i += 1

    return result


def align_sentences_dual_chain(
    sentences_a: List[Sentence],
    sentences_b: List[Sentence],
    similarity_threshold: float = 0.6,
    ngram_size: int = 2
) -> List[AlignmentItem]:
    """
    主对齐函数：使用双链结构对齐句子

    Args:
        sentences_a: 原文句子列表
        sentences_b: 校对后句子列表
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小

    Returns:
        对齐结果列表
    """
    # 阶段一：全等匹配
    alignment = align_sentences_exact_match(sentences_a, sentences_b)

    # 阶段二：相似度匹配
    alignment = align_sentences_similarity(
        sentences_a, sentences_b, alignment,
        similarity_threshold, ngram_size
    )

    # 验证双链
    is_valid, errors = validate_dual_chain(alignment, sentences_a, sentences_b)
    if not is_valid:
        print("警告：双链验证失败：")
        for error in errors:
            print(f"  - {error}")

    return alignment


def align_texts_dual_chain(
    text_a: str,
    text_b: str,
    preserve_formatting: bool = True,
    similarity_threshold: float = 0.6,
    ngram_size: int = 2
) -> List[Dict]:
    """
    对齐两个完整文本（使用双链算法）

    Args:
        text_a: 原文
        text_b: 校对后文本
        preserve_formatting: 是否保留格式
        similarity_threshold: 相似度阈值
        ngram_size: n-gram大小

    Returns:
        对齐结果列表（字典格式）
    """
    # 准备句子
    sentences_a = prepare_sentences(text_a, preserve_formatting)
    sentences_b = prepare_sentences(text_b, preserve_formatting)

    # 对齐
    alignment = align_sentences_dual_chain(
        sentences_a, sentences_b,
        similarity_threshold, ngram_size
    )

    # 转换为字典格式
    return [item.to_dict() for item in alignment]


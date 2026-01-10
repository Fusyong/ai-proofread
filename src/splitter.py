"""
用于分拆markdown文件的工具模块
"""

import re
from typing import List, Tuple

def cut_text_by_length(text: str, cut_by: int=600) -> List[str]:
    """
    将文本大致按长度切分（在指定长度前后最近一个空行处）

    Args:
        text (str): 文本
        length (int): 长度

    Returns:
        List[str]: 切分后的文本列表
    """
    # 如果length小于50，则按50字切分
    cut_by = 50 if cut_by < 50 else int(cut_by)
    # 按行分割文本
    lines = text.splitlines()

    # 存储切分后的文本
    result = []
    current_chunk = []
    current_length = 0

    for line in lines:
        current_chunk.append(line)
        current_length += len(line)

        # 如果当前块长度超过目标长度且遇到空行,则切分
        if current_length >= cut_by and not line.strip():
            result.append('\n'.join(current_chunk))
            current_chunk = []
            current_length = 0

    # 添加最后一个块
    if current_chunk:
        result.append('\n'.join(current_chunk))

    return result

def cut_text_in_list_by_length(text_list: List[str], threshold:int=1500, cut_by:int=800) -> List[str]:
    """将列表中的超长段落切分为多个短段落

    Args:
        text_list (List[str]): 段落列表
        threshold (int): 段落最大长度，超过此长度的段落将被拆分
        cut_by (int): 拆分长段落时的目标长度

    Returns:
        List[str]: 处理后的段落列表
    """
    text_list_short = []
    for i in text_list:
        if len(i)>threshold:
            text_list_short.extend(cut_text_by_length(i, cut_by=cut_by))
        else:
            text_list_short.append(i)
    return text_list_short

def split_markdown_by_title(text: str, levels: List[int]=[2]) -> List[str]:
    """
    将markdown文本按标题级别切分

    Args:
        text (str): markdown文本
        levels (List[int]): 要切分的标题级别列表

    Returns:
        List[str]: 按标题切分的文本列表
    """
    # 按行分割文本
    lines = text.splitlines()

    # 存储切分后的段落
    raw_paragraphs = []
    current_paragraph = []

    for line in lines:
        # 检查是否为要切分的标题
        is_title_to_cut = False
        for l in levels:
            if line.startswith(f"{'#' * l} "):
                is_title_to_cut = True
                break

        if is_title_to_cut:
            # 如果当前段落不为空，添加到结果中
            if current_paragraph:
                raw_paragraphs.append('\n'.join(current_paragraph))
                current_paragraph = []

            # 将当前标题行添加到新段落
            current_paragraph.append(line)
        else:
            # 将当前行添加到当前段落
            current_paragraph.append(line)

    # 添加最后一个段落（如果存在）
    if current_paragraph:
        raw_paragraphs.append('\n'.join(current_paragraph))

    return raw_paragraphs

def split_markdown_by_title_and_length_with_context(text: str, levels: List[int]=[2], cut_by: int=600) -> List[dict]:
    """
    1. 将markdown文本按标题级别切分;
    2. 再按cut_by字符切分，作为target；
    3. 保留完整上下文，作为context；
    """
    # 按标题切分文本
    raw_paragraphs = split_markdown_by_title(text, levels=levels)

    # 长文本按cut_by字符切分，并添加target标签并保留上下文
    label_paragraphs = []
    for paragraph in raw_paragraphs:
        pieces = cut_text_by_length(paragraph, cut_by=cut_by)
        new_pieces = []
        # 为每个片段添加target标签并保留上下文
        for piece in pieces:
            dict_piece = {
                'context': paragraph,
                'target': piece,
            }
            new_pieces.append(dict_piece)
        label_paragraphs.extend(new_pieces)

    return label_paragraphs

def merge_short_paragraphs(paragraphs: List[str], min_length: int=100) -> List[str]:
    """
    合并短段落到后一段

    Args:
        paragraphs (List[str]): 段落列表
        min_length (int): 段落最小长度，小于此长度的段落将被合并

    Returns:
        List[str]: 合并短段落后的段落列表
    """
    result = []
    temp_paragraphs = []

    for para in paragraphs:
        para_length = len(para)

        if para_length < min_length:
            # 短段落暂存
            temp_paragraphs.append(para)
        else:
            # 正常长度段落
            if temp_paragraphs:
                # 如果有暂存段落，合并后添加
                temp_paragraphs.append(para)
                result.append('\n'.join(temp_paragraphs))
                temp_paragraphs = []
            else:
                # 直接添加
                result.append(para)

    # 处理剩余的暂存段落
    if temp_paragraphs:
        result.append('\n'.join(temp_paragraphs))

    return result

def split_markdown_by_title_and_length_and_merge(text: str, levels: List[int]=[2], threshold: int=1000, cut_by: int=800, min_length: int=120) -> List[dict]:
    """
    1. 将markdown文本按标题级别切分，
    2. 然后按cut_by字符进一步切分，
    3. 合并不足min_length字符的零碎段落
    """
    # 1. 按指定的标题级别拆分
    text_list = split_markdown_by_title(text, levels=levels)

    # 2. 进一步将超threshold字符的长段落按cut_by字符尝试切分
    text_list = cut_text_in_list_by_length(text_list, threshold=threshold, cut_by=cut_by)

    # 3. 合并不足min_length字符的零碎段落
    text_list = merge_short_paragraphs(text_list, min_length=min_length)
    # 如果仍有超长段落，可在原文上手动设置伪标题和空行

    # 添加target标签
    text_list = [{'target':x} for x in text_list if x.strip()]

    return text_list

def split_chinese_sentences(text: str, preserve_formatting: bool = True) -> List[str]:
    """
    将中文文本按句子切分

    句子结尾标记包括：
    1. 基本句末标点：[。！？…]+ 后面可能跟引号、括号等
    2. 段落标记：空行、换行符
    3. 特殊情况：
       - 列表项、标题等末尾可能没有标点，但遇到空行或新行时也应切分
       - 引号内的句号可能不是句子结尾（如"他说："你好。"）
       - 数字后的句号可能是小数点（如3.14）
       - 省略号可能是...或……
       - 括号内的内容（如（注：这是注释））

    Args:
        text (str): 要切分的文本
        preserve_formatting (bool): 是否保留原始格式（换行、空格等），默认True

    Returns:
        List[str]: 切分后的句子列表
    """
    if not text.strip():
        return []

    # 如果保留格式，先按行处理；否则统一处理
    if preserve_formatting:
        return _split_sentences_with_formatting(text)
    else:
        return _split_sentences_plain(text)


def split_chinese_sentences_with_line_numbers(text: str, preserve_formatting: bool = True) -> List[Tuple[str, int, int]]:
    """
    将中文文本按句子切分，并跟踪每个句子在原始文本中的行号

    Args:
        text (str): 要切分的文本
        preserve_formatting (bool): 是否保留原始格式（换行、空格等），默认True

    Returns:
        List[Tuple[str, int, int]]: 切分后的句子列表，每个元素为 (sentence, start_line, end_line)
        - sentence: 切分后的句子文本
        - start_line: 句子开头所在的行号（从1开始）
        - end_line: 句子结尾所在的行号（从1开始）
    """
    if not text.strip():
        return []

    # 如果保留格式，先按行处理；否则统一处理
    if preserve_formatting:
        return _split_sentences_with_formatting_with_lines(text)
    else:
        return _split_sentences_plain_with_lines(text)


def _split_sentences_plain(text: str) -> List[str]:
    """纯文本句子切分（不保留格式）"""
    sentences = []
    current_sentence = []
    in_quote = False
    quote_char = None
    i = 0

    while i < len(text):
        char = text[i]
        current_sentence.append(char)

        # 处理引号状态
        if char in ['“', '”', '‘', '’', '「', '」', '『', '』']:
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char or (char in ['“', '”'] and quote_char in ['“', '”']):
                in_quote = False
                quote_char = None

        # 检查是否是句子结尾（不在引号内）
        if not in_quote:
            end_pos = _get_sentence_end_pos(text, i)
            if end_pos > i:
                # 收集从当前位置+1到句子结尾的所有字符（当前位置已添加）
                for j in range(i + 1, end_pos):
                    if j < len(text):
                        current_sentence.append(text[j])
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []
                i = end_pos
                continue

        i += 1

    # 处理最后一句
    if current_sentence:
        sentence = ''.join(current_sentence).strip()
        if sentence:
            sentences.append(sentence)

    return sentences


def _split_sentences_plain_with_lines(text: str) -> List[Tuple[str, int, int]]:
    """纯文本句子切分（不保留格式），带行号跟踪"""
    # 先按行分割，记录每行的起始位置
    lines = text.split('\n')
    line_starts = []  # 每行在原始文本中的起始字符位置
    current_pos = 0
    for line in lines:
        line_starts.append(current_pos)
        current_pos += len(line) + 1  # +1 for the newline character

    sentences = []
    current_sentence = []
    sentence_start_pos = 0  # 当前句子在文本中的起始位置
    in_quote = False
    quote_char = None
    i = 0

    while i < len(text):
        char = text[i]

        # 记录句子起始位置
        if not current_sentence:
            sentence_start_pos = i

        current_sentence.append(char)

        # 处理引号状态
        if char in ['“', '”', '‘', '’', '「', '」', '『', '』']:
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char or (char in ['“', '”'] and quote_char in ['“', '”']):
                in_quote = False
                quote_char = None

        # 检查是否是句子结尾（不在引号内）
        if not in_quote:
            end_pos = _get_sentence_end_pos(text, i)
            if end_pos > i:
                # 收集从当前位置+1到句子结尾的所有字符（当前位置已添加）
                for j in range(i + 1, end_pos):
                    if j < len(text):
                        current_sentence.append(text[j])
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    # 计算行号
                    start_line = _get_line_number(sentence_start_pos, line_starts)
                    end_line = _get_line_number(end_pos - 1, line_starts)
                    sentences.append((sentence, start_line, end_line))
                current_sentence = []
                i = end_pos
                continue

        i += 1

    # 处理最后一句
    if current_sentence:
        sentence = ''.join(current_sentence).strip()
        if sentence:
            start_line = _get_line_number(sentence_start_pos, line_starts)
            end_line = _get_line_number(len(text) - 1, line_starts)
            sentences.append((sentence, start_line, end_line))

    return sentences


def _get_line_number(pos: int, line_starts: List[int]) -> int:
    """根据字符位置和行起始位置列表，计算行号（从1开始）"""
    if not line_starts:
        return 1

    # 使用二分查找
    left, right = 0, len(line_starts) - 1
    line_number = 1

    while left <= right:
        mid = (left + right) // 2
        if line_starts[mid] <= pos:
            line_number = mid + 1
            left = mid + 1
        else:
            right = mid - 1

    return line_number


def _split_sentences_with_formatting(text: str) -> List[str]:
    """保留格式的句子切分（考虑Markdown格式）"""
    lines = text.splitlines(keepends=True)
    sentences = []
    current_sentence = []
    in_quote = False
    quote_char = None

    for line_idx, line in enumerate(lines):
        # 检查是否是标题或列表项
        is_title = _is_markdown_title(line)
        is_list_item = _is_list_item(line)
        is_empty_line = not line.strip()

        # 如果遇到空行，且当前句子不为空，则切分
        if is_empty_line and current_sentence:
            sentence = ''.join(current_sentence).strip()
            if sentence:
                sentences.append(sentence)
            current_sentence = []
            continue

        # 处理标题：标题本身作为一句，即使没有标点
        if is_title:
            if current_sentence:
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []
            sentences.append(line.rstrip())
            continue

        # 处理列表项：列表项末尾可能没有标点，但遇到空行或新列表项时切分
        if is_list_item:
            # 如果当前句子不为空，先保存
            if current_sentence:
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []

            # 检查列表项内容是否以句末标点结尾
            list_content = _extract_list_content(line)
            if list_content and _ends_with_sentence_punct(list_content):
                sentences.append(line.rstrip())
            else:
                # 列表项没有句末标点，先暂存，等待后续内容或空行
                current_sentence.append(line)
            continue

        # 普通文本行：逐字符处理
        i = 0
        while i < len(line):
            char = line[i]
            current_sentence.append(char)

            # 处理引号状态
            if char in ['“', '”', '‘', '’', '「', '」', '『', '』']:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char or (char in ['“', '”'] and quote_char in ['“', '”']):
                    in_quote = False
                    quote_char = None

            # 检查是否是句子结尾（不在引号内）
            if not in_quote:
                end_pos = _get_sentence_end_pos_in_line(line, i)
                if end_pos > i:
                    # 收集从当前位置+1到句子结尾的所有字符（当前位置已添加）
                    for j in range(i + 1, end_pos):
                        if j < len(line):
                            current_sentence.append(line[j])
                    sentence = ''.join(current_sentence).strip()
                    if sentence:
                        sentences.append(sentence)
                    current_sentence = []
                    i = end_pos
                    continue

            i += 1

        # 如果当前行以列表项或标题结尾，且下一行是空行或新列表项/标题，则切分
        if current_sentence and line_idx < len(lines) - 1:
            next_line = lines[line_idx + 1]
            if (not next_line.strip() or
                _is_markdown_title(next_line) or
                _is_list_item(next_line)):
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []

    # 处理最后一句
    if current_sentence:
        sentence = ''.join(current_sentence).strip()
        if sentence:
            sentences.append(sentence)

    return sentences


def _split_sentences_with_formatting_with_lines(text: str) -> List[Tuple[str, int, int]]:
    """保留格式的句子切分（考虑Markdown格式），带行号跟踪"""
    lines = text.splitlines(keepends=True)
    sentences = []
    current_sentence = []
    sentence_start_line = 1  # 当前句子开始的行号（从1开始）
    in_quote = False
    quote_char = None

    for line_idx, line in enumerate(lines):
        current_line_number = line_idx + 1  # 当前行号（从1开始）

        # 检查是否是标题或列表项
        is_title = _is_markdown_title(line)
        is_list_item = _is_list_item(line)
        is_empty_line = not line.strip()

        # 如果遇到空行，且当前句子不为空，则切分
        if is_empty_line and current_sentence:
            sentence = ''.join(current_sentence).strip()
            if sentence:
                # 句子结束行是上一行（空行之前）
                end_line = current_line_number - 1 if current_line_number > 1 else 1
                sentences.append((sentence, sentence_start_line, end_line))
            current_sentence = []
            continue

        # 处理标题：标题本身作为一句，即使没有标点
        if is_title:
            if current_sentence:
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    # 句子结束行是上一行（标题之前）
                    end_line = current_line_number - 1 if current_line_number > 1 else 1
                    sentences.append((sentence, sentence_start_line, end_line))
                current_sentence = []
            # 标题本身作为一句
            title_text = line.rstrip()
            if title_text:
                sentences.append((title_text, current_line_number, current_line_number))
            continue

        # 处理列表项：列表项末尾可能没有标点，但遇到空行或新列表项时切分
        if is_list_item:
            # 如果当前句子不为空，先保存
            if current_sentence:
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    # 句子结束行是上一行（列表项之前）
                    end_line = current_line_number - 1 if current_line_number > 1 else 1
                    sentences.append((sentence, sentence_start_line, end_line))
                current_sentence = []
                sentence_start_line = current_line_number

            # 检查列表项内容是否以句末标点结尾
            list_content = _extract_list_content(line)
            if list_content and _ends_with_sentence_punct(list_content):
                list_text = line.rstrip()
                if list_text:
                    sentences.append((list_text, current_line_number, current_line_number))
            else:
                # 列表项没有句末标点，先暂存，等待后续内容或空行
                if not current_sentence:
                    sentence_start_line = current_line_number
                current_sentence.append(line)
            continue

        # 普通文本行：逐字符处理
        if not current_sentence:
            sentence_start_line = current_line_number

        i = 0
        while i < len(line):
            char = line[i]
            current_sentence.append(char)

            # 处理引号状态
            if char in ['"', '"', ''', ''', '「', '」', '『', '』']:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char or (char in ['"', '"'] and quote_char in ['"', '"']):
                    in_quote = False
                    quote_char = None

            # 检查是否是句子结尾（不在引号内）
            if not in_quote:
                end_pos = _get_sentence_end_pos_in_line(line, i)
                if end_pos > i:
                    # 收集从当前位置+1到句子结尾的所有字符（当前位置已添加）
                    for j in range(i + 1, end_pos):
                        if j < len(line):
                            current_sentence.append(line[j])

                    # 检查句号后面的内容
                    # 注意：_get_sentence_end_pos_in_line已经跳过了句号后的引号/括号
                    # 所以remaining_in_line不会包含这些引号/括号
                    remaining_in_line = line[end_pos:]
                    remaining_stripped = remaining_in_line.strip()

                    # 判断是否应该切分
                    should_split = False

                    if not remaining_stripped:
                        # 句号后面只有空格或换行，应该切分
                        should_split = True
                    else:
                        # 句号后面有文本
                        # 检查句号后是否有空格，或者后面是否是新句子（中文、大写字母等）
                        if remaining_in_line.startswith((' ', '\t')):
                            # 句号后面是空格，应该切分（新句子开始）
                            should_split = True
                        else:
                            # 句号后面直接跟文本（无空格，且_get_sentence_end_pos_in_line已跳过引号）
                            # 检查是否可能是新句子：中文、大写字母、数字等
                            first_char = remaining_stripped[0] if remaining_stripped else ''
                            # 如果是中文、大写字母、数字，可能是新句子，应该切分
                            if (first_char and (
                                '\u4e00' <= first_char <= '\u9fff' or  # 中文
                                first_char.isupper() or  # 大写字母
                                first_char.isdigit()  # 数字
                            )):
                                should_split = True
                            else:
                                # 其他情况（小写字母等），可能是同一句子，不切分
                                should_split = False

                    if should_split:
                        sentence = ''.join(current_sentence).strip()
                        if sentence:
                            sentences.append((sentence, sentence_start_line, current_line_number))
                        current_sentence = []
                        i = end_pos
                        continue
                    # 如果不切分，继续处理剩余内容
                    # 将剩余内容添加到current_sentence
                    for j in range(end_pos, len(line)):
                        current_sentence.append(line[j])
                    i = len(line)
                    break  # 跳出while循环，继续下一行

            i += 1

        # 检查行尾：如果当前行以句号结尾（后面只有空格），且下一行不是空行，应该切分
        if current_sentence and line_idx < len(lines) - 1:
            next_line = lines[line_idx + 1]

            # 检查当前行是否以句号结尾（后面只有空格）
            line_stripped = line.rstrip()
            if line_stripped and line_stripped[-1] in ['。', '！', '？', '…']:
                # 当前行以句号结尾，且下一行不是空行，应该切分
                if next_line.strip() and not _is_markdown_title(next_line) and not _is_list_item(next_line):
                    sentence = ''.join(current_sentence).strip()
                    if sentence:
                        sentences.append((sentence, sentence_start_line, current_line_number))
                    current_sentence = []

            # 如果当前行以列表项或标题结尾，且下一行是空行或新列表项/标题，则切分
            elif (not next_line.strip() or
                  _is_markdown_title(next_line) or
                  _is_list_item(next_line)):
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append((sentence, sentence_start_line, current_line_number))
                current_sentence = []

    # 处理最后一句
    if current_sentence:
        sentence = ''.join(current_sentence).strip()
        if sentence:
            # 最后一句结束行是最后一行
            last_line_number = len(lines)
            sentences.append((sentence, sentence_start_line, last_line_number))

    return sentences


def _get_sentence_end_pos(text: str, pos: int) -> int:
    """获取句子结尾的完整结束位置（包括所有连续的句末标点和后续的引号/括号）

    Returns:
        int: 句子结尾的结束位置（不包含），如果不是句子结尾则返回pos
    """
    if pos >= len(text):
        return pos

    char = text[pos]

    # 基本句末标点
    if char in ['。', '！', '？', '…']:
        # 先收集所有连续的句末标点（允许多个连用，如 ？！！、……………………）
        end_pos = pos + 1
        while end_pos < len(text) and text[end_pos] in ['。', '！', '？', '…']:
            end_pos += 1

        # 然后检查后面是否跟引号、括号等
        while end_pos < len(text) and text[end_pos] in ['"', '”', "'", '’', '）', ']', '】', '》', '」', '』']:
            end_pos += 1

        return end_pos

    # 英文句号（需要判断上下文）
    if char == '.':
        # 如果前后都是数字，可能是小数点
        if pos > 0 and pos < len(text) - 1:
            if text[pos - 1].isdigit() and text[pos + 1].isdigit():
                return pos  # 不是句子结尾
        # 如果后面跟的是小写字母或数字，可能不是句子结尾
        if pos < len(text) - 1:
            next_char = text[pos + 1]
            if next_char.islower() or next_char.isdigit():
                return pos  # 不是句子结尾
        # 在中文文本中，英文句号也可能是句子结尾
        if pos > 0:
            prev_char = text[pos - 1]
            if '\u4e00' <= prev_char <= '\u9fff':  # 前一个字符是中文
                end_pos = pos + 1
                # 检查后面是否跟引号、括号等
                while end_pos < len(text) and text[end_pos] in ['"', '”', "'", '’', '）', ']', '】', '》', '」', '』']:
                    end_pos += 1
                return end_pos
        # 检查是否是数字后的句号（可能是小数点）
        if char == '.' and pos > 0:
            prev_char = text[pos - 1]
            if prev_char.isdigit() and end_pos < len(text) and text[end_pos].isdigit():
                return pos  # 不是句子结尾

    return pos  # 不是句子结尾


def _get_sentence_end_pos_in_line(line: str, pos: int) -> int:
    """获取行内句子结尾的完整结束位置（包括所有连续的句末标点和后续的引号/括号）

    Returns:
        int: 句子结尾的结束位置（不包含），如果不是句子结尾则返回pos
    """
    if pos >= len(line):
        return pos

    char = line[pos]

    # 基本句末标点
    if char in ['。', '！', '？', '…']:
        # 先收集所有连续的句末标点（允许多个连用，如 ？！！、……………………）
        end_pos = pos + 1
        while end_pos < len(line) and line[end_pos] in ['。', '！', '？', '…']:
            end_pos += 1

        # 然后检查后面是否跟引号、括号等
        while end_pos < len(line) and line[end_pos] in ['"', '”', "'", '’', '）', ']', '】', '》', '」', '』']:
            end_pos += 1

        # 检查是否是数字后的句号
        if char == '。' and pos > 0:
            prev_char = line[pos - 1]
            if prev_char.isdigit() and end_pos < len(line) and line[end_pos].isdigit():
                return pos  # 不是句子结尾

        return end_pos

    # 英文句号
    if char == '.':
        if pos > 0 and pos < len(line) - 1:
            if line[pos - 1].isdigit() and line[pos + 1].isdigit():
                return pos  # 不是句子结尾
        if pos < len(line) - 1:
            next_char = line[pos + 1]
            if next_char.islower() or next_char.isdigit():
                return pos  # 不是句子结尾
        if pos > 0:
            prev_char = line[pos - 1]
            if '\u4e00' <= prev_char <= '\u9fff':
                end_pos = pos + 1
                # 检查后面是否跟引号、括号等
                while end_pos < len(line) and line[end_pos] in ['"', '”', "'", '’', '）', ']', '】', '》', '」', '』']:
                    end_pos += 1
                return end_pos

    return pos  # 不是句子结尾


def _is_sentence_end(text: str, pos: int) -> bool:
    """判断位置pos是否是句子结尾"""
    end_pos = _get_sentence_end_pos(text, pos)
    return end_pos > pos


def _is_sentence_end_in_line(line: str, pos: int) -> bool:
    """判断行内位置是否是句子结尾（考虑行尾情况）"""
    end_pos = _get_sentence_end_pos_in_line(line, pos)
    return end_pos > pos


def _is_markdown_title(line: str) -> bool:
    """判断是否是Markdown标题"""
    stripped = line.lstrip()
    if not stripped.startswith('#'):
        return False
    # 检查格式：## 标题 或 ## 标题（多个#号）
    if len(stripped) > 1:
        return stripped[1] == ' ' or stripped[1] == '#'
    return False


def _is_list_item(line: str) -> bool:
    """判断是否是列表项"""
    stripped = line.lstrip()
    # 无序列表：-、*、+
    if stripped.startswith(('- ', '* ', '+ ')):
        return True
    # 有序列表：数字. 或 数字)
    if re.match(r'^\d+[.)]\s+', stripped):
        return True
    return False


def _extract_list_content(line: str) -> str:
    """提取列表项的内容部分（去除标记）"""
    stripped = line.lstrip()
    # 无序列表
    if stripped.startswith(('- ', '* ', '+ ')):
        return stripped[2:].strip()
    # 有序列表
    match = re.match(r'^\d+[.)]\s+(.+)', stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _ends_with_sentence_punct(text: str) -> bool:
    """判断文本是否以句末标点结尾"""
    if not text:
        return False
    # 去除末尾可能的引号、括号等
    text = text.rstrip('"\'”’）]】》」』')
    if not text:
        return False
    return text[-1] in ['。', '！', '？', '…', '.', '!', '?']


def split_chinese_sentences_simple(text: str) -> List[str]:
    """
    简化版中文句子切分（仅按句末标点切分，不考虑格式）

    适用于纯文本，不考虑Markdown格式、列表项等特殊情况。

    Args:
        text (str): 要切分的文本

    Returns:
        List[str]: 切分后的句子列表
    """
    # 句子结尾模式：[。！？…]+ 后面可能跟引号、括号等
    # 也考虑英文句号（但需要排除小数点等情况）
    pattern = r'([。！？…]+["\'”’）\]】》」』]*)|([.!?]+["\'”’）\]】》」』]*)'

    sentences = []
    last_end = 0

    for match in re.finditer(pattern, text):
        end_pos = match.end()

        # 检查是否是小数点或缩写
        if match.group(2):  # 英文标点
            # 检查前后是否是数字
            if end_pos < len(text) and text[end_pos - 1] == '.':
                prev_pos = match.start() - 1
                if prev_pos >= 0 and text[prev_pos].isdigit():
                    if end_pos < len(text) and text[end_pos].isdigit():
                        continue  # 是小数点，跳过

        # 提取句子
        sentence = text[last_end:end_pos].strip()
        if sentence:
            sentences.append(sentence)
        last_end = end_pos

    # 添加最后一句
    if last_end < len(text):
        sentence = text[last_end:].strip()
        if sentence:
            sentences.append(sentence)

    return sentences


if __name__ == "__main__":

    pass

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

def split_markdown_by_title(text: str, levels: list[int]=[2]) -> List[str]:
    """
    将markdown文本按标题级别切分

    Args:
        text (str): markdown文本
        levels (list[int]): 要切分的标题级别列表

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

def split_markdown_by_title_and_length_with_context(text: str, levels: list[int]=[2], cut_by: int=600) -> List[dict]:
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

def split_markdown_by_title_and_length_and_merge(text: str, levels: list[int]=[2], threshold: int=1000, cut_by: int=800, min_length: int=120) -> List[dict]:
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
        if char in ['"', '"', ''', ''', '「', '」', '『', '』']:
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char or (char in ['"', '"'] and quote_char in ['"', '"']):
                in_quote = False
                quote_char = None

        # 检查是否是句子结尾（不在引号内）
        if not in_quote and _is_sentence_end(text, i):
            sentence = ''.join(current_sentence).strip()
            if sentence:
                sentences.append(sentence)
            current_sentence = []

        i += 1

    # 处理最后一句
    if current_sentence:
        sentence = ''.join(current_sentence).strip()
        if sentence:
            sentences.append(sentence)

    return sentences


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
            if char in ['"', '"', ''', ''', '「', '」', '『', '』']:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char or (char in ['"', '"'] and quote_char in ['"', '"']):
                    in_quote = False
                    quote_char = None

            # 检查是否是句子结尾（不在引号内）
            if not in_quote and _is_sentence_end_in_line(line, i):
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []

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


def _is_sentence_end(text: str, pos: int) -> bool:
    """判断位置pos是否是句子结尾"""
    if pos >= len(text):
        return False

    char = text[pos]

    # 基本句末标点
    if char in ['。', '！', '？', '…']:
        # 检查后面是否跟引号、括号等
        next_pos = pos + 1
        while next_pos < len(text) and text[next_pos] in ['"', '"', ''', ''', '）', ']', '】', '》', '」', '』']:
            next_pos += 1

        # 检查是否是数字后的句号（可能是小数点）
        if char == '。' and pos > 0:
            prev_char = text[pos - 1]
            if prev_char.isdigit() and next_pos < len(text) and text[next_pos].isdigit():
                return False

        return True

    # 英文句号（需要判断上下文）
    if char == '.':
        # 如果前后都是数字，可能是小数点
        if pos > 0 and pos < len(text) - 1:
            if text[pos - 1].isdigit() and text[pos + 1].isdigit():
                return False
        # 如果后面跟的是小写字母或数字，可能不是句子结尾
        if pos < len(text) - 1:
            next_char = text[pos + 1]
            if next_char.islower() or next_char.isdigit():
                return False
        # 在中文文本中，英文句号也可能是句子结尾
        if pos > 0:
            prev_char = text[pos - 1]
            if '\u4e00' <= prev_char <= '\u9fff':  # 前一个字符是中文
                return True

    return False


def _is_sentence_end_in_line(line: str, pos: int) -> bool:
    """判断行内位置是否是句子结尾（考虑行尾情况）"""
    if pos >= len(line):
        return False

    char = line[pos]

    # 基本句末标点
    if char in ['。', '！', '？', '…']:
        # 检查后面是否跟引号、括号等
        next_pos = pos + 1
        while next_pos < len(line) and line[next_pos] in ['"', '"', ''', ''', '）', ']', '】', '》', '」', '』']:
            next_pos += 1

        # 检查是否是数字后的句号
        if char == '。' and pos > 0:
            prev_char = line[pos - 1]
            if prev_char.isdigit() and next_pos < len(line) and line[next_pos].isdigit():
                return False

        return True

    # 英文句号
    if char == '.':
        if pos > 0 and pos < len(line) - 1:
            if line[pos - 1].isdigit() and line[pos + 1].isdigit():
                return False
        if pos < len(line) - 1:
            next_char = line[pos + 1]
            if next_char.islower() or next_char.isdigit():
                return False
        if pos > 0:
            prev_char = line[pos - 1]
            if '\u4e00' <= prev_char <= '\u9fff':
                return True

    return False


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
    text = text.rstrip('"\'"\'）]】》」』')
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
    pattern = r'([。！？…]+["\'"\'）\]】》」』]*)|([.!?]+["\'"\'）\]】》」』]*)'

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

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

def split_chinese_sentences_simple(text: str) -> List[str]:
    """
    简化版中文句子切分（按句末标点和连续换行切分，保留所有空白字符）

    适用于纯文本，不考虑Markdown格式、列表项等特殊情况。
    连续两个以上的换行（忽略行中空白字符）视作句子结束标记。

    Args:
        text (str): 要切分的文本

    Returns:
        List[str]: 切分后的句子列表（保留所有空白字符，包括首尾换行符）
    """
    # 句子结尾模式：
    # 1. 句末标点：[。！？…]+ 后面可能跟引号、括号等
    # 2. 英文句号（需要排除小数点等情况）
    # 3. 连续两个以上的换行（忽略行中空白字符）：\n[\s]*\n+
    pattern = r'([。！？…]+[”’）\]】」』]*)|([.!?]+[”’"\'）\]】」』]*)|(\n(\s*\n)+)'

    sentences = []
    last_end = 0

    for match in re.finditer(pattern, text):
        end_pos = match.end()

        # 检查是否是小数点、列表序号或缩写
        if match.group(2):  # 英文标点
            if end_pos < len(text) and text[end_pos - 1] == '.':
                prev_pos = match.start() - 1
                if prev_pos >= 0 and text[prev_pos].isdigit():
                    # 前一个是数字：可能是小数点，也可能是列表序号 1. 2.
                    if end_pos < len(text) and text[end_pos].isdigit():
                        continue  # 后也是数字，是小数点，跳过
                    # 后不是数字（空格、换行、汉字等），视为列表序号，不在句号处切分
                    continue

        # 如果是句末标点（不是连续换行），需要包含后面的换行符和空行
        # 直到遇到下一个非空行
        if match.group(1) or match.group(2):  # 句末标点
            # 从end_pos开始，查找后面的换行符和空行
            trailing_pos = end_pos
            while trailing_pos < len(text):
                # 检查当前位置是否是换行符
                if text[trailing_pos] == '\n':
                    trailing_pos += 1
                    # 检查后面是否还有空行（只包含空白字符的行）
                    # 查找下一个换行符或非空白字符
                    temp_pos = trailing_pos
                    while temp_pos < len(text) and text[temp_pos] in ' \t':
                        temp_pos += 1
                    # 如果下一个字符是换行符，说明是空行，继续包含
                    if temp_pos < len(text) and text[temp_pos] == '\n':
                        trailing_pos = temp_pos + 1
                        continue
                    # 如果下一个字符是非空白字符，停止
                    elif temp_pos < len(text) and not text[temp_pos].isspace():
                        break
                    # 如果到达文本末尾，停止
                    else:
                        break
                else:
                    # 不是换行符，停止
                    break

            # 更新end_pos以包含后面的换行符和空行
            end_pos = trailing_pos

        # 提取句子
        sentence = text[last_end:end_pos]
        if sentence:
            sentences.append(sentence)
        last_end = end_pos

    # 添加最后一句
    if last_end < len(text):
        sentence = text[last_end:]
        if sentence:
            sentences.append(sentence)

    return sentences

def split_chinese_sentences(text: str) -> List[str]:
    """
    将中文文本按句子切分（基于split_chinese_sentences_simple，增加Markdown特殊处理）

    特殊处理：
    1. Markdown标题作为一句，不切分
    2. Markdown列表中每一项作为一句，不切分
    3. 其他文本使用split_chinese_sentences_simple进行切分
    4. 保留所有空白字符（包括首尾换行符），任何时候都保持原文不变

    Args:
        text (str): 要切分的文本

    Returns:
        List[str]: 切分后的句子列表（保留所有空白字符）
    """
    if not text.strip():
        return []

    # 按行分割，保留换行符
    lines = text.splitlines(keepends=True)
    sentences = []
    current_text = []  # 收集普通文本（非标题、非列表项）

    i = 0
    while i < len(lines):
        line = lines[i]
        is_title = _is_markdown_title(line)
        is_list_item = _is_list_item(line)

        # 处理Markdown标题：作为完整句子
        if is_title:
            # 先处理之前收集的普通文本
            if current_text:
                text_chunk = ''.join(current_text)
                chunk_sentences = split_chinese_sentences_simple(text_chunk)
                sentences.extend(chunk_sentences)
                current_text = []

            # 标题本身作为一句，包含后面的空行
            title_sentence = line
            # 检查后面的行是否是空行，如果是，包含它们
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # 如果下一行是空行（只包含空白字符），包含它
                if not next_line.strip():
                    title_sentence += next_line
                    j += 1
                else:
                    # 遇到非空行，停止
                    break
            sentences.append(title_sentence)
            i = j  # 跳过已处理的行
            continue

        # 处理Markdown列表项：每一项作为完整句子
        if is_list_item:
            # 先处理之前收集的普通文本
            if current_text:
                text_chunk = ''.join(current_text)
                chunk_sentences = split_chinese_sentences_simple(text_chunk)
                sentences.extend(chunk_sentences)
                current_text = []

            # 列表项本身作为一句，包含后面的空行
            list_sentence = line
            # 检查后面的行是否是空行，如果是，包含它们
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # 如果下一行是空行（只包含空白字符），包含它
                if not next_line.strip():
                    list_sentence += next_line
                    j += 1
                else:
                    # 遇到非空行，停止
                    break
            sentences.append(list_sentence)
            i = j  # 跳过已处理的行
            continue

        # 普通文本：收集起来，稍后统一处理
        current_text.append(line)
        i += 1

    # 处理剩余的普通文本
    if current_text:
        text_chunk = ''.join(current_text)
        chunk_sentences = split_chinese_sentences_simple(text_chunk)
        sentences.extend(chunk_sentences)

    # 过滤空句子（但保留只包含空白字符的句子）
    return [s for s in sentences if s]


def split_chinese_sentences_with_line_numbers(text: str, use_simple: bool = False) -> List[Tuple[str, int, int]]:
    """
    将中文文本按句子切分，并跟踪每个句子在原始文本中的行号

    基于 split_chinese_sentences 或 split_chinese_sentences_simple 的结果，
    然后在原文中查找每个句子的位置并计算行号。

    Args:
        text (str): 要切分的文本
        use_simple (bool): 是否使用 split_chinese_sentences_simple，默认False

    Returns:
        List[Tuple[str, int, int]]: 切分后的句子列表，每个元素为 (sentence, start_line, end_line)
        - sentence: 切分后的句子文本
        - start_line: 句子开头所在的行号（从1开始）
        - end_line: 句子结尾所在的行号（从1开始）
    """
    if not text.strip():
        return []

    # 先获取句子列表
    if use_simple:
        sentences = split_chinese_sentences_simple(text)
    else:
        sentences = split_chinese_sentences(text)

    if not sentences:
        return []

    # 在原文中查找每个句子的位置并计算行号
    return _find_sentence_positions(text, sentences)




def _find_sentence_positions(text: str, sentences: List[str]) -> List[Tuple[str, int, int]]:
    """
    在原文中查找每个句子的位置并计算行号

    Args:
        text (str): 原始文本
        sentences (List[str]): 句子列表（按顺序）

    Returns:
        List[Tuple[str, int, int]]: (sentence, start_line, end_line) 列表
    """
    # 预先计算每行的起始字符位置
    lines = text.split('\n')
    line_starts = []  # 每行在原始文本中的起始字符位置
    current_pos = 0
    for line in lines:
        line_starts.append(current_pos)
        current_pos += len(line) + 1  # +1 for the newline character

    result = []
    search_start = 0  # 从上次找到的位置之后开始搜索

    for sentence in sentences:
        if not sentence:
            continue

        # 在原文中查找句子（从search_start位置开始）
        pos = text.find(sentence, search_start)

        if pos == -1:
            # 如果找不到，尝试去掉首尾空白字符再找
            sentence_stripped = sentence.strip()
            if sentence_stripped:
                pos = text.find(sentence_stripped, search_start)
                if pos != -1:
                    # 找到了，但需要调整位置以匹配原始句子（包含空白字符）
                    # 这里简化处理：使用找到的位置
                    pass

        if pos == -1:
            # 仍然找不到，跳过这个句子（或使用默认值）
            # 为了健壮性，尝试在整个文本中查找
            pos = text.find(sentence)
            if pos == -1:
                # 如果还是找不到，跳过
                continue

        # 计算行号：使用句子中第一个非空白字符的位置
        # 因为句子开头可能包含前导换行符，这些换行符属于前一行
        # 我们需要找到句子中第一个非空白字符来确定句子真正开始的行号
        sentence_start_pos = pos
        for i, char in enumerate(sentence):
            if not char.isspace():  # 找到第一个非空白字符
                sentence_start_pos = pos + i
                break
        # 如果句子只包含空白字符，sentence_start_pos 保持为 pos（句子开头的位置）

        # 计算行号
        start_line = _get_line_number(sentence_start_pos, line_starts)
        end_pos = pos + len(sentence) - 1
        end_line = _get_line_number(end_pos, line_starts)

        result.append((sentence, start_line, end_line))

        # 更新搜索起始位置（从当前句子结束位置之后开始）
        search_start = pos + len(sentence)

    return result


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



if __name__ == "__main__":

    pass

"""
用于分拆markdown文件的工具模块
"""

from typing import List
import json

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

def split_markdown_by_title_and_length_with_context(text: str, levels: list[int]=[2], cut_by: int=600) -> List[str]:
    """
    1. 将markdown文本按标题级别切分;
    2. 再按cut_by字符切分，添加target标签；
    3. 并在头部添加完整上下文，添加context标签；
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
            piece = f'<context>\n{paragraph}\n</context>\n\n<target>\n{piece}\n</target>'
            new_pieces.append(piece)
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

def split_markdown_by_title_and_length_and_merge(text: str, levels: list[int]=[2], threshold: int=1000, cut_by: int=800, min_length: int=120) -> List[str]:
    """
    1. 将markdown文本按标题级别切分，
    2. 然后按cut_by字符进一步切分，
    3. 合并不足min_length字符的零碎段落
    4. 添加target标签
    """
    # 1. 按指定的标题级别拆分
    text_list = split_markdown_by_title(text, levels=levels)

    # 2. 进一步将超threshold字符的长段落按cut_by字符尝试切分
    text_list = cut_text_in_list_by_length(text_list, threshold=threshold, cut_by=cut_by)

    # 3. 合并不足min_length字符的零碎段落
    text_list = merge_short_paragraphs(text_list, min_length=min_length)
    # 如果仍有超长段落，可在原文上手动设置伪标题和空行

    # 添加target标签
    text_list = [f'<target>\n{x}\n</target>' for x in text_list if x.strip()]

    return text_list

if __name__ == "__main__":

    pass

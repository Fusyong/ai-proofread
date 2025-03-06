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


if __name__ == "__main__":
    # 示例文件路径
    root_dir = "13本传统文化/清洗后md/"
    file_names = [
        '1.21 先秦诗',
        '1.21 汉魏晋六朝（上）',
        '1.21 汉魏晋六朝（下册）',
        '1.21 唐诗上册',
        '1.21 唐诗中册',
        '1.21 唐诗下册',
        '1.21 宋诗',
        '1.21 宋词上（未转曲）',
        '1.21 宋词中',
        '1.21 宋词下',
        '1.21 题画诗',
        '1.21 元散曲',
        '1.21 元杂剧',
    ]
    for file_name in file_names:
        FILE_INPUT = f"{root_dir}/{file_name}.clean.md"
        FILE_JSON = f"{root_dir}/{file_name}.clean.json"
        FILE_JSON_MD = f"{root_dir}/{file_name}.clean.json.md"

        # 先将markdown切分为json
        # 并手动加标题以控制长度
        with open(FILE_INPUT, "r", encoding="utf-8") as f:
            text = f.read()  # 读取整个文件内容

            text_list = split_markdown_by_title(text, levels=[1,2,3,4,5])

            # 1. 将超长段落切分为多个短段落
            text_list = cut_text_in_list_by_length(text_list, threshold=1000, cut_by=800)

            # 2. 合并短段落
            text_list = merge_short_paragraphs(text_list, min_length=120)
            # 如果仍有超长段落，可在原文上手动设置伪标题和空行

            # 打印长度供检查
            for i, j in enumerate(text_list):
                length = len(j)
                print(f"No.{i+1}\t{length}\t{j.strip()[:15].splitlines()[0]}")

            # 写出json
            with open(FILE_JSON, "w", encoding="utf-8") as f:
                json.dump(text_list, f, ensure_ascii=False, indent=2)

            # 写出md供核对
            with open(FILE_JSON_MD, "w", encoding="utf-8") as f:
                text = "\n".join(text_list)
                f.write(text)
"""
替换文本中与给定文本相似的片段
"""
from typing import List, Dict, Tuple
from rapidfuzz import fuzz

def find_best_match(
        text: str,
        fragment: str,
        len_offset: int = 3,
        modified: str | None = None,
        ) -> Dict:
    """
    在文本中查找与给定文本最相似的一个片段

    Args:
        text (str): 需要处理的原始文本
        fragment (str): 原始文本片段(可能用少量错误)
        len_offset (int): 允许的长度偏差，默认为3
        modified (str | None): 替换文本，默认为None
    """
    # 初始化最佳匹配信息
    best_match = {
        'fragment_text': fragment,
        'modified_text': modified,
        'real_text': None,
        'location': None,
        'ratio': 0
        }

    # 使用滑动窗口在原文中查找，窗口大小有±offset字符的弹性
    base_window_size = len(fragment)
    for window_size in range(base_window_size - len_offset, base_window_size + len_offset):
        if window_size <= 0:
            continue
        for i in range(len(text) - window_size + 1):
            substring = text[i:i+window_size]
            ratio = fuzz.ratio(fragment, substring)

            if ratio > best_match['ratio']:
                best_match.update({
                    'real_text': substring,
                    'location': (i, i+window_size),
                    'ratio': ratio
                })

    return best_match

def find_best_match_list(
        text: str,
        replacements: List[Tuple[str, str]] | List[str]
        ) -> List[Dict]:
    """
    在文本中查找与给定文本相似的片段，返回详细信息

    Args:
        text (str): 需要处理的原始文本
        replacements (list): 包含`(原文, 替换文) | 原文`的列表
        len_offset (int, optional): 滑动窗口长度偏移量，默认为3

    Returns:
        List[Dict]: 包含每个替换项详细信息的列表，每项包含：
            - fragment_text: 输入的原始文本
            - modified_text: 输入的替换文本
            - real_text: 实际找到的最相似文本
            - location: (开始位置, 结束位置)的元组
            - ratio: 相似度
    """
    results = []

    for fragment, modified in replacements:
        best_match = find_best_match(text, fragment, modified=modified)
        results.append(best_match)

    return results

def apply_replacements(text: str,
                     replacement_info: List[Dict],
                     similarity_threshold: int = 80) -> str:
    """
    根据查找到的相似文本信息执行替换

    Args:
        text (str): 原始文本
        replacement_info (List[Dict]): find_similar_segments函数的输出

    Returns:
        str: 替换后的文本
    """
    result_text = text

    # 从后向前替换，避免位置变化影响后续替换
    for info in sorted(replacement_info,
                      key=lambda x: x['location'][0] if x['location'] else -1,
                      reverse=True):
        if info['real_text'] and info['location'] and info['ratio'] >= similarity_threshold:
            if info['real_text'] in result_text:
                result_text = result_text.replace(info['real_text'], info['modified_text'])
            else:
                print(f"替换失败: 未找到文本 '{info['real_text']}'")

    return result_text


if __name__ == '__main__':
    # 示例用法
    ORIGINAL_TEXT = """
    输出修改后的文本，用文本原有的格式，原文的空行、原文换行、分段等格式保持不变，不要给出任何额外的说明。
    """

    fragment_and_modified = [
        ("输出修改后的文字，", "输出修改好的文本,"),
        ("原文空行", "原文的位置"),
        ("原文", "啤酒"),
    ]

    # 先查找相似文本
    similar_segments = find_best_match_list(ORIGINAL_TEXT, fragment_and_modified)

    # 打印查找结果
    for segment in similar_segments:
        print(f"原文: {segment['fragment_text']}")
        print(f"替换为: {segment['modified_text']}")
        print(f"找到的文本: {segment['real_text']}")
        print(f"位置: {segment['location']}")
        print(f"相似度: {segment['ratio']}")
        print("-" * 50)

    # 执行替换
    RESULT = apply_replacements(ORIGINAL_TEXT, similar_segments)
    print("替换后的文本:")
    print(RESULT)

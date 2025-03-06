"""合并json为markdown
"""

import json
from typing import List


# 示例文件路径
root_dir = "13本传统文化/清洗后md/"
file_names = [
    '1.21 先秦诗',
    # '1.21 汉魏晋六朝（上）',
    # '1.21 汉魏晋六朝（下册）',
    # '1.21 唐诗上册',
    # '1.21 唐诗中册',
    # '1.21 唐诗下册',
    # '1.21 宋诗',
    # '1.21 宋词上（未转曲）',
    # '1.21 宋词中',
    # '1.21 宋词下',
    # '1.21 题画诗',
    # '1.21 元散曲',
    # '1.21 元杂剧',
]
for file_name in file_names:

    FILE_PROOFREAD_JSON = f"{root_dir}/{file_name}.clean.proofread.json"
    FILE_PROOFREAD_MD = f"{root_dir}/{file_name}.clean.proofread.md"

    paragraphs: List[str] = []
    with open(FILE_PROOFREAD_JSON, "r", encoding="utf-8") as f:
        paragraphs = json.load(f)
        paragraphs = [p for p in paragraphs if p is not None]

    with open(FILE_PROOFREAD_MD, "w", encoding="utf-8") as f:
        f.write("\n\n".join(paragraphs))


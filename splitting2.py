"""
1. 将markdown按标题切分；
2. 进一步切分为指定长度的小段；
3. 合并太短的段落到后一段；
4. 添加校对标签（target）

这有利于避免一次生成过长的文本，降低校对质量和请求错误，又不至于过于零碎；
本方法消耗token少，但无法保持上下文连贯性。
"""
import json

from src.markdown_splitter import split_markdown_by_title_and_length_and_merge



# 文件所在路径（以项目根目录为当前目录）
ROOT_DIR = "example"
# 文件名列表（不含后缀`.md`）
file_names = [
    'your_markdown',
    # '1.21 先秦诗.clean',
    # '1.21 汉魏晋六朝（上）.clean',
    # '1.21 汉魏晋六朝（下册）.clean',
    # '1.21 唐诗上册.clean',
    # '1.21 唐诗中册.clean',
    # '1.21 唐诗下册.clean',
    # '1.21 宋诗.clean',
    # '1.21 宋词上（未转曲）.clean',
    # '1.21 宋词中.clean',
    # '1.21 宋词下.clean',
    # '1.21 题画诗.clean',
    # '1.21 元散曲.clean',
    # '1.21 元杂剧.clean',
]
for file_name in file_names:

    FILE_INPUT = f"{ROOT_DIR}/{file_name}.md"
    FILE_JSON = f"{ROOT_DIR}/{file_name}.json"
    FILE_JSON_MD = f"{ROOT_DIR}/{file_name}.json.md"

    # 先将markdown切分为json
    # 并手动加标题以控制长度
    with open(FILE_INPUT, "r", encoding="utf-8") as f:
        text = f.read()  # 读取整个文件内容

        ############################################
        # # 按标题切分，并添加text_for_proofreading标签，并合并短段落到后一段
        text_list = split_markdown_by_title_and_length_and_merge(text, levels=[1], threshold=1000, cut_by=600, min_length=120)
        ############################################

        # 写出json
        with open(FILE_JSON, "w", encoding="utf-8") as f:
            json.dump(text_list, f, ensure_ascii=False, indent=2)

        # 写出md供核对
        with open(FILE_JSON_MD, "w", encoding="utf-8") as f:
            text = "\n".join(text_list)
            f.write(text)

        # 打印长度供检查
        print(f"片段号\t字符数\t起始文字\n{'-'*40}")
        for i, j in enumerate(text_list):
            j = j.replace("<target>", "")
            length = len(j)
            print(f"No.{i+1}\t{length}\t{j.strip()[:15].splitlines()[0]}")

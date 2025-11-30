"""将标题下的文字切分为带上下文的片段

1. 将markdown按标题级别切分；
2. 进一步切分为指定长度的小段（target），同时准备好完整的上下文（context）；

添加完整上下文有利于提高校对质量，同时避免一次生成过长的文本。
TODO 还可以进一步添加参考资料（reference）
"""

import json
from src.splitter import split_markdown_by_title_and_length_with_context

# 文件所在路径（从项目根目录开始算，根目录用`.`表示）
ROOT_DIR = "./example"
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
        # levels: 切分标题级别，比如[1,2]表示按一级标题和二级标题切分
        # cut_by: 切分长度
        text_list = split_markdown_by_title_and_length_with_context(text, levels=[1,2], cut_by=200)
        ############################################

        # 写出json
        with open(FILE_JSON, "w", encoding="utf-8") as f:
            json.dump(text_list, f, ensure_ascii=False, indent=2)

        # 写出md供核对
        with open(FILE_JSON_MD, "w", encoding="utf-8") as f:
            TEXT = "\n---\n".join([x["target"] for x in text_list])
            f.write(TEXT)

        # 打印切片数据供检查
        print(f"片段号\t片长\t段长\t起始文字\n{'-'*40}")
        TOTAL_TARGET_LENGTH = 0
        TOTAL_CONTEXT_LENGTH = 0
        for i, j in enumerate(text_list):
            target_length = len(j['target'].strip())
            context_length = len(j['context'].strip())
            print(f"No.{i+1}\t{target_length}\t{context_length}\t{j['target'].strip()[:15].splitlines()[0]}")
            TOTAL_TARGET_LENGTH += target_length
            TOTAL_CONTEXT_LENGTH += context_length
        print(f"合计\t{TOTAL_TARGET_LENGTH}\t{TOTAL_CONTEXT_LENGTH}\t总计{TOTAL_TARGET_LENGTH+TOTAL_CONTEXT_LENGTH}")

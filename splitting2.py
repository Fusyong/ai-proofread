"""按标题切分后，进一步处理过长和过短的片段

1. 将markdown按标题切分；
2. 进一步切分为指定长度的小段；
3. 合并太短的段落到后一段；

这有利于避免一次生成过长的文本，降低校对质量，引发请求错误，同时又不至于过于零碎；
本方法消耗token少，但无法保持上下文连贯性。
"""
import json

from src.splitter import split_markdown_by_title_and_length_and_merge


# 文件所在路径（从项目根目录开始算，根目录用`.`表示）
ROOT_DIR = "./example"
# 文件名列表（不含后缀`.md`）
file_names = [
    '1',
    # 'your_markdown',
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
        # threshold: 切分阈值，比如500表示当段落长度超过500时切分
        # cut_by: 切分长度，比如300表示每段切分为300字符
        # min_length: 最小长度，比如120表示长度小于120字符的段落会被合并到后一段
        text_list = split_markdown_by_title_and_length_and_merge(text, levels=[2], threshold=500, cut_by=300, min_length=120)
        ############################################

        # 写出json供校对
        with open(FILE_JSON, "w", encoding="utf-8") as f:
            json.dump(text_list, f, ensure_ascii=False, indent=2)

        # 写出md供核对, `---`表示切分线
        with open(FILE_JSON_MD, "w", encoding="utf-8") as f:
            TEXT = "\n---\n".join([x["target"] for x in text_list])
            f.write(TEXT)

        # 打印长度供评估
        print(f"片段号\t字符数\t起始文字\n{'-'*40}")
        TOTAL_LENGTH = 0
        for i, j in enumerate(text_list):
            length = len(j['target'].strip())
            print(f"No.{i+1}\t{length}\t{j['target'].strip()[:15].splitlines()[0]}")
            TOTAL_LENGTH += length
        print(f"合计\t{TOTAL_LENGTH}")

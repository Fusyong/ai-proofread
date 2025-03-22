"""一般校对用例

输入切分好的JSON文件（可以含上下文和参考文献），输出校对后的JSON文件
"""
import os
import json
import asyncio
from src.proofreader import process_paragraphs_async

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
    # 切分好的JSON文件
    FILE_IN_JSON = f"{ROOT_DIR}/{file_name}.json"
    # 将生成的文件
    FILE_PROOFREAD_JSON = f"{ROOT_DIR}/{file_name}.proofread.json"

    # 确保输入文件存在
    if not os.path.exists(FILE_IN_JSON):
        print(f"错误：输入文件 {FILE_IN_JSON} 不存在")
        exit(1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(FILE_PROOFREAD_JSON), exist_ok=True)

    # 处理文本
    try:
        asyncio.run(process_paragraphs_async(FILE_IN_JSON, FILE_PROOFREAD_JSON, start_count=1, model="deepseek-chat", rpm=15, max_concurrent=3))
    except Exception as e:
        print(f"处理文本时出错: {str(e)}")
        exit(1)

    # 输出处理进度统计
    try:
        with open(FILE_IN_JSON, "r", encoding="utf-8") as f:
            input_paragraphs = json.load(f)

        with open(FILE_PROOFREAD_JSON, "r", encoding="utf-8") as f:
            output_paragraphs = json.load(f)

        processed_count = sum(1 for p in output_paragraphs if p is not None)
        total_count = len(input_paragraphs)
        processed_length = sum(len(p) for p in output_paragraphs if p is not None)
        total_length = sum(len(p) for p in input_paragraphs)

        print(f"\n【{file_name}】处理进度统计:")
        print(f"总段落数: {total_count}")
        print(f"已处理段落数、字数: {processed_count} ({processed_count/total_count*100:.2f}%), {processed_length} ({processed_length/total_length*100:.2f}%)")
        print(f"未处理段落数: {total_count - processed_count} ({(total_count-processed_count)/total_count*100:.2f}%)")
        for i, paragraph in enumerate(input_paragraphs):
            if output_paragraphs[i] is None:
                print(f"No.{i+1} \n {paragraph.strip().splitlines()[0][:20]}...\n")
    except Exception as e:
        print(f"统计处理进度时出错: {str(e)}")

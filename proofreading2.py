"""每次处理一个文件

可添加上下文和参考资料，以提高校对质量。
"""
from src.proofreader import deepseek

# 文件所在路径（以项目根目录为当前目录）
ROOT_DIR = "example2"
# 要校对的文件
FILE_NAME = f'{ROOT_DIR}/your_markdown.md'
# 上下文文件
CONTEXT_FILE_NAME = f'{ROOT_DIR}/your_markdown_context.md'
# 参考资料文件
REFERENCE_FILE_NAME = f'{ROOT_DIR}/your_markdown_reference.md'
# 校对结果文件
RESULT_FILE_NAME = f'{ROOT_DIR}/your_markdown_proofread.md'

TARGET = ""
with open(FILE_NAME, "r", encoding="utf-8") as f:
    TARGET = f.read()
    TARGET = f'<target>\n{TARGET}\n</target>'

CONTEXT = ""
with open(CONTEXT_FILE_NAME, "r", encoding="utf-8") as f:
    CONTEXT = f.read()
    if CONTEXT:
        CONTEXT = f'<context>\n{CONTEXT}\n</context>'

REFERENCE = ""
with open(REFERENCE_FILE_NAME, "r", encoding="utf-8") as f:
    REFERENCE = f.read()
    if REFERENCE:
        REFERENCE = f'<reference>\n{REFERENCE}\n</reference>'

# 以下两种方式的优劣有待测试  TODO
if 1:
    # 将上下文添加到参考文献后提交
    REFERENCE = f"{REFERENCE}\n\n{CONTEXT}"
else:
    # 将上下文添加到校对文本前提交
    TARGET = f"{CONTEXT}\n\n{TARGET}"

result = deepseek(TARGET, REFERENCE)
if result:
    with open(RESULT_FILE_NAME, "w", encoding="utf-8") as f:
        f.write(result)
else:
    print("校对失败")

"""比较11.md和22.md的差异，并生成html文件"""

import difflib

from typing import List
from splitter import split_markdown_by_title
from clear_pdf_book_txt_to_md import clean_title


def split_md_text(text1, text2,  levels:List[int]|None=None):
    """
    将校对前后的两个md文本按标题分割成多个部分，并检查一致性

    Args:
        text1: 第一个md文本
        text2: 第二个md文本
        levels: 分割的标题级别，默认2级标题

    Returns:
        list: 分割后的md文本列表
        bool: 是否一致

    """
    # 如果levels为None，则默认分割2级标题
    if levels is None:
        levels = [2]

    # 分割文本
    split_text1 = split_markdown_by_title(text1, levels=levels)
    split_text2 = split_markdown_by_title(text2, levels=levels)

    # 检查一致性
    title_list1 = [clean_title(x.strip().split('\n')[0]) for x in split_text1]
    title_list2 = [clean_title(x.strip().split('\n')[0]) for x in split_text2]

    # 比较标题
    title_pair_list = list(zip(title_list1, title_list2))

    return split_text1, split_text2, title_pair_list

def diff_md_text(lines_list_1, lines_list_2, context=False, numlines=3):
    """
    使用difflib比较两个文件的差异并生成HTML格式的比较结果

    Args:
        text1: 第一个md文本
        text2: 第二个md文本
        context: 是否显示上下文，默认False显示全文
        numlines: 显示的上下文行数，默认3行
    """
    # 预处理文本，统一处理空行和换行
    def preprocess_lines(lines):
        processed = []
        for line in lines:
            # 去除行尾空白字符
            line = line.rstrip()
            # 如果行不为空，则保留
            if line:
                processed.append(line)
            # 如果行为空，则添加一个空行（避免连续空行）
            elif processed and processed[-1] != '':
                processed.append('')
        return processed

    # 预处理两个文本
    processed_lines1 = preprocess_lines(lines_list_1)
    processed_lines2 = preprocess_lines(lines_list_2)

    # 创建HTML差异对比
    # 设置更宽松的比较参数
    diff = difflib.HtmlDiff(
        wrapcolumn=33,
        linejunk=None,  # 不忽略任何行
        charjunk=None,  # 不忽略任何字符
        tabsize=4      # 设置制表符大小
    )

    # 使用预处理后的文本生成差异
    html_content = diff.make_file(
        processed_lines1,
        processed_lines2,
        "原稿",
        "校后稿",
        context=context,
        numlines=numlines
    )

    # 添加宋体字体样式，使用更具体的CSS选择器和!important
    html_content = html_content.replace(
        '</head>',
        '''<style>
        body, table, tr, td {
            font-family: "SimSun", "宋体" !important;
            font-size: 14px !important;
        }
        /* 添加一些样式来优化显示效果 */
        .diff_header {
            background-color: #f0f0f0;
        }
        .diff_add {
            text-decoration: underline;
        }
        .diff_chg {
            text-decoration: overline underline;
        }
        .diff_sub {
            text-decoration: overline;
        }
        </style></head>'''
    )

    return html_content

def jsdiff_md_text(path, file_name_a, file_name_b, diff_path=None):
    """
    使用jsdiff比较两个md文本的差异

    Args:
        path: 文件路径
        file_name_a: 文件名a
        file_name_b: 文件名b
        diff_path: 差异路径，默认None
    """

    if diff_path is None:
        diff_path = f'{path}/{".".join(file_name_b.split(".")[:-1])}_diff.html'

    # 读取文件 TODO 转义
    with open(f'{path}/{file_name_a}', 'r', encoding='utf-8') as f:
        text1 = f.read()

    with open(f'{path}/{file_name_b}', 'r', encoding='utf-8') as f:
        text2 = f.read()

    with open('src/jsdiff.html', 'r', encoding='utf-8') as f:
        content = f.read()
        # 替换<title>Diff</title>中的名称
        content = content.replace(r'<title>Diff</title>', f'<title>{file_name_a} vs {file_name_b}</title>')
        # 替换a-text
        content = content.replace(r'<script type="text/plain" id="a-text">这里是你的长文本内容a...可以包含多行</script>', f'<script type="text/plain" id="a-text">{text1}</script>')
        # 替换b-text
        content = content.replace(r'<script type="text/plain" id="b-text">这里是你的长文本内容b...可以包含多行</script>', f'<script type="text/plain" id="b-text">{text2}</script>')
        with open(diff_path, 'w', encoding='utf-8') as f:
            f.write(content)


if __name__ == '__main__':

    ROOT_DIR = "example"

    file_list = [
        'your_markdown',
        # '1.21 汉魏晋六朝（上）.clean',
        # '1.21 汉魏晋六朝（下册）.clean',
        # '1.21 宋词上（未转曲）.clean',
        # '1.21 宋词下.clean',
        # '1.21 宋词中.clean',
        # '1.21 宋诗.clean',
        # '1.21 唐诗上册.clean',
        # '1.21 唐诗下册.clean',
        # '1.21 唐诗中册.clean',
        # '1.21 题画诗.clean',
        # '1.21 先秦诗.clean',
        # '1.21 元散曲.clean',
        # '1.21 元杂剧.clean',
    ]


    ###########
    # jsdiff
    ###########
    for name in file_list:
        file1 = f'{name}.md'
        file2 = f'{name}.proofread.json.md'
        jsdiff_md_text(ROOT_DIR, file1, file2)

    ###########
    # difflib单文件比较
    ###########
    # for file in file_list:
    #     text11 = open(f'{root_dir}/{file}.clean.md', 'r', encoding='utf-8').readlines()
    #     text22 = open(f'{root_dir}/{file}.clean.proofread.json.md', 'r', encoding='utf-8').readlines()

    #     html_content = diff_md_text(text11, text22, context=False, numlines=3)
    #     with open(f'{root_dir}/{file}.diff.html', 'w', encoding='utf-8') as f:
    #         f.write(html_content)

    ###########
    # 批量分段后比较
    ###########
    # for file in file_list:
    #     text1 = open(f'{root_dir}/{file}.clean.md', 'r', encoding='utf-8').read()
    #     text2 = open(f'{root_dir}/{file}.clean.proofread.json.md', 'r', encoding='utf-8').read()
    #     split_text1, split_text2, title_pair_list = split_md_text(text1, text2, levels=[1])
    #     # 检查标题是否一致
    #     is_consistent = True
    #     print(f'检查标题是否一致：')
    #     for title1, title2 in title_pair_list:
    #         # 比较标题
    #         print(f'{title1} == {title2}')
    #         if title1 != title2:
    #             print(f'{title1} != {title2}')
    #             is_consistent = False
    #             print(f'标题不一致，请处理文件')
    #             break
    #     if is_consistent:
    #         for i, (text1, text2) in enumerate(zip(split_text1, split_text2)):
    #             diff_file_a_name = f'{root_dir}/{file}.{i}{title_pair_list[i][0]}'
    #             with open(f'{diff_file_a_name}_a.md', 'w', encoding='utf-8') as f:
    #                 f.write(text1)
    #             with open(f'{diff_file_a_name}_b.md', 'w', encoding='utf-8') as f:
    #                 f.write(text2)
    #             print(f'{diff_file_a_name}_a.md 和 {diff_file_a_name}_b.md 保存成功')

    #             # diff效果不好，常常找不到对应行（直接用text.splitlines()一样）
    #             # with open(f'{diff_file_a_name}_a.md', 'r', encoding='utf-8') as f:
    #             #     text1 = f.readlines()
    #             # with open(f'{diff_file_a_name}_b.md', 'r', encoding='utf-8') as f:
    #             #     text2 = f.readlines()
    #             # html_content = diff_md_text(text1, text2, context=False, numlines=3)
    #             # with open(f'{diff_file_a_name}_diff.html', 'w', encoding='utf-8') as f:
    #             #     f.write(html_content)
    #             #     print(f'{diff_file_a_name}_diff.html 保存成功')

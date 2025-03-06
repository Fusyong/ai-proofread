"""比较11.md和22.md的差异，并生成html文件"""

import difflib
import os
import shutil
# import webbrowser

from typing import List
from markdown_splitter import split_markdown_by_title
from clear_pdf_book_txt_to_md import clean_title


def split_md_text(text1, text2,  levels:List[int]=[2]):
    """
    将md文本按标题分割成多个部分，并检查一致性

    Args:
        text1: 第一个md文本
        text2: 第二个md文本
        levels: 分割的标题级别，默认2级标题

    Returns:
        list: 分割后的md文本列表
        bool: 是否一致

    """

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
    比较两个文件的差异并生成HTML格式的比较结果

    Args:
        text1: 第一个md文本
        text2: 第二个md文本
        context: 是否显示上下文，默认False显示全文
        numlines: 显示的上下文行数，默认3行
    """

    # 创建HTML差异对比
    # 设置 charjunk=None 以显示所有字符级别的差异
    diff = difflib.HtmlDiff(wrapcolumn=33, charjunk=None)
    html_content = diff.make_file( # make_table
        lines_list_1,
        lines_list_2,
        "原稿",
        "校后稿",
        context=context, # 显示上下文，默认False显示全文
        numlines=numlines # 显示3行上下文，默认5
    )

    # 添加宋体字体样式，使用更具体的CSS选择器和!important
    html_content = html_content.replace(
        '</head>',
        '''<style>
        body, table, tr, td {
            font-family: "SimSun", "宋体" !important;
            font-size: 14px !important;
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
        diff_path = f'{path}/{".".join(file_name_a.split(".")[:-1])}_diff/'

    # 确保路径存在
    os.makedirs(diff_path, exist_ok=True)

    # 读取文件 TODO 转义
    with open(f'{path}/{file_name_a}', 'r', encoding='utf-8') as f:
        text1 = f.read()
        with open(f'{diff_path}/a.js', 'w', encoding='utf-8') as f:
            f.write(f'a = `{text1}`')

    with open(f'{path}/{file_name_b}', 'r', encoding='utf-8') as f:
        text2 = f.read()
        with open(f'{diff_path}/b.js', 'w', encoding='utf-8') as f:
            f.write(f'b = `{text2}`')

    # 复制jsdiff.js
    shutil.copy(f'jsdiff/diff.js', f'{diff_path}/diff.js')
    # 复制并修改index.html
    with open(f'jsdiff/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
        # 替换<title>Diff</title>中的名称
        content = content.replace(r'<title>Diff</title>', f'<title>{file_name_a} vs {file_name_b}</title>')
        with open(f'{diff_path}/index.html', 'w', encoding='utf-8') as f:
            f.write(content)


if __name__ == '__main__':

    root_dir = '13本传统文化/清洗后校对'

    file_list = [
        # '1.21 汉魏晋六朝（上）',
        # '1.21 汉魏晋六朝（下册）',
        # '1.21 宋词上（未转曲）',
        # '1.21 宋词下',
        # '1.21 宋词中',
        # '1.21 宋诗',
        # '1.21 唐诗上册',
        # '1.21 唐诗下册',
        # '1.21 唐诗中册',
        # '1.21 题画诗',
        '1.21 先秦诗',
        # '1.21 元散曲',
        # '1.21 元杂剧',
    ]


    ###########
    # jsdiff
    ###########
    for name in file_list:
        file1 = f'{name}.clean.md'
        file2 = f'{name}.clean.proofread.json.md'
        jsdiff_md_text(root_dir, file1, file2)

    ###########
    # 单文件比较
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

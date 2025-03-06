"""批处理
"""
import os

root_dir = '13本传统文化'

file_list = [
    '1.21 汉魏晋六朝（上）',
    '1.21 汉魏晋六朝（下册）',
    '1.21 宋词上（未转曲）',
    '1.21 宋词下',
    '1.21 宋词中',
    '1.21 宋诗',
    '1.21 唐诗上册',
    '1.21 唐诗下册',
    '1.21 唐诗中册',
    '1.21 题画诗',
    '1.21 先秦诗',
    '1.21 元散曲',
    '1.21 元杂剧',
]

# 批量转换html为md
for file in file_list:
    c = f'pandoc -f html -t markdown-smart+pipe_tables+footnotes --wrap=none --toc  "{root_dir}\\{file}.html" -o "{root_dir}\\{file}.md"'
    print(c)
    os.system(c)

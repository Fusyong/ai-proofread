"""整理pdf书本txt文件为md文件

1. 根据目录表在正文中标出标题
"""
import re
import copy

def delete_image(text):
    """
    删除图像链接，用空格替代

    # `!\[image\](.+?)\{.+?\}`替换我`  `
    """

    # 替换图片
    text = re.sub(r'!\[image\](.+?)\{.+?\}', r'  ', text)

    return text



def mark_style(text, code_replace_pattern_map, default_replace_pattern=None):
    """
    处理样式文本如`[text]{.s16}`

    文本为空时原位插入两个空格

    Returns:
        tuple: (处理后的文本, 替换记录列表[(原文本, 替换后文本), ...])
    """

    # 存储替换记录
    replacements = []

    def replace_style(match):
        original_text = match.group(0)
        content = match.group(1).strip()
        style_code = int(match.group(2))

        replacement = original_text  # 默认保持原样

        # 如果内容为空，插入两个空格
        if not content:
            replacement = "  "
        # 查找页码对应的样式类型
        elif style_code in code_replace_pattern_map:
            # 获取替换模式并替换$1为实际内容
            pattern_template = code_replace_pattern_map[style_code]
            replacement = pattern_template.replace("$1", content)
        elif default_replace_pattern:
            # 使用默认替换
            replacement = default_replace_pattern.replace("$1", content)

        # 记录替换
        if replacement != original_text:
            replacements.append((original_text, replacement))

        return replacement

    # 应用替换
    result = re.sub(r'\[([^\[\]]*)\]\{.s(\d+)( [^\{\}]*)?\}', replace_style, text)
    return result, replacements


def clean_title(title:str):
    """
    清理标题，以便比较是否一致
    """
    return re.sub(r'[\s\da-zA-Z\[\]\{\}\.\^]', '', title.strip())

def parse_toc(content, indent_level=4, base_level=1):
    """
    解析用户提供的目录列表，提取目录项及其层级结构

    Args:
        file_path: 目录文件的路径

    Returns:
        list: 包含目录项信息的列表，每项为字典，包含'name'和'level'键
    """
    lines = content.split('\n')
    toc_items = []

    for line in lines:
        line_striped = line.strip()
        if not line_striped:
            continue

        # 计算缩进级别
        level = 0
        start_char = line_striped[0]
        if start_char in ['*', '-', '+']: # 目录项
            # 计算星号前的空格数来确定级别
            leading_spaces = len(line) - len(line.lstrip())
            level = leading_spaces // indent_level + base_level

            # 去除目录项的符号
            name_part = line_striped.lstrip(start_char).lstrip(' ')

            # 去除最后的阿拉伯数字（一或多位）
            # name_part = re.sub(r'\d+$', '', name_part)
            name_part = clean_title(name_part)

            # 去除省略号、空格、点号等忽略符号
            omit_chars = [' ', '…', '.'] # 忽略的符号
            name_part = ''.join([char for char in name_part if char not in omit_chars])

            if name_part.strip():
                toc_items.append({
                    'name': name_part.strip(),
                    'level': level
                })
    # print(toc_items)
    return toc_items


def mark_titles(text:list[str], toc_items:list[dict]):
    """
    根据目录列表在文本文件中标记标题，并返回前后的目录

    Args:
        file_path: 文本文件路径
        toc_items: 目录项列表，每项为包含'name'和'level'的字典

    Returns:
        tuple: (完整标记文件路径, 仅标题文件路径, 未找到的目录项列表)
    """

    # 创建一个新的列表来存储标记后的行
    marked_lines = copy.deepcopy(text)
    not_found = []

    # 标记标题
    for item in toc_items:
        item_name = item['name']
        item_level = item['level']
        found = False

        for i, line in enumerate(text):
            # 移除空格、拼音、括号以便比较 TODO 需要完善
            cleaned_line = clean_title(line.strip())

            if item_name == cleaned_line:
                # 使用目录项的级别作为标题级别
                marked_lines[i] = f"{'#' * item_level} {line.strip()}"
                found = True

        if not found:
            not_found.append(item)


    return marked_lines, not_found

def mark_footnotes_from_list(marked_lines: list[str]) -> list[str]:
    """
    把数字列表转换为a-z1-9脚注，并使整个列表号码连贯有序
    【如果数字列表不想转换，请手动假标记】
    使脚注行头编码连续（不处理正文中的编码）

    比如：
    1. 注释
    2. 注释
2. 注释
    [^d] 注释
    [^k] 注释

    转换为：
[^a]: 注释
[^b]: 注释
[^c]: 注释
[^d]: 注释
[^e]: 注释

    Returns:
        list: 处理后的行列表
    """
    # 正则表达式匹配数字列表项和已有脚注行
    list_item_pattern = re.compile(r'^(\s*)(\d+)\.(\s+.+)$')
    footnote_pattern = re.compile(r'^(\s*)\[\^([a-zA-Z0-9]+)\]:(.+)$')

    # 用于跟踪当前脚注字母
    current_footnote_index = 0
    footnote_letters = 'abcdefghijklmnopqrstuvwxyz'

    # 生成脚注键的函数
    def get_footnote_key(index):
        # 简单方案：使用数字作为超出字母范围的标识符
        if index < len(footnote_letters):
            return footnote_letters[index]
        else:
            # 超出26个字母时，直接使用数字
            return str(index - len(footnote_letters) + 1)

    # 第一步：识别列表项和已有脚注行，并转换为连续的脚注格式
    for i, line in enumerate(marked_lines):
        # 忽略空行
        if not line.strip():
            continue

        # 检查是否是数字列表项，是否是已有脚注行
        list_match = list_item_pattern.match(line)
        footnote_match = footnote_pattern.match(line)
        if list_match:
            content = list_match.group(3)  # 列表项内容

            # 获取当前脚注字母
            footnote_key = get_footnote_key(current_footnote_index)
            current_footnote_index += 1

            # 将列表项转换为脚注格式
            marked_lines[i] = f"[^{footnote_key}]:{content}\n"
            continue
        elif footnote_match:
            indent = footnote_match.group(1)
            content = footnote_match.group(3)

            # 获取当前脚注字母
            footnote_key = get_footnote_key(current_footnote_index)
            current_footnote_index += 1

            # 更新脚注行，保持原有内容
            marked_lines[i] = f"{indent}[^{footnote_key}]:{content}\n"
        else:
            current_footnote_index = 0

    return marked_lines

def mark_footnotes_from_abc(marked_lines):
    """
    整理文本中的脚注标记为markdown格式

    文中脚注字符集：a-z（先排除括注的拼音）
    脚注行标记为：a　 於（wū）：赞叹词。
    """
    pinyin = re.compile(r"[（\(][a-zA-Z'āáǎàōóǒòêê̄ếê̌ềēéěèīíǐìūúǔùüǖǘǚǜm̄ḿm̀ńňǹẑĉŝŋĀÁǍÀŌÓǑÒÊÊ̄ẾÊ̌ỀĒÉĚÈĪÍǏÌŪÚǓÙÜǕǗǙǛM̄ḾM̀ŃŇǸẐĈŜŊ]+[\）)]")
    footnotes_line = re.compile(r"^(\s*)([a-zA-Z])(\s+.+)$")

    # 创建一个字典来存储脚注
    footnotes = {}
    footnote_lines_indices = []

    # 第一步：识别脚注行并提取脚注内容
    for i, line in enumerate(marked_lines):
        match = footnotes_line.match(line)
        if match:
            indent = match.group(1)
            footnote_key = match.group(2)
            content = match.group(3)
            footnotes[footnote_key] = content
            footnote_lines_indices.append(i)
            # 将脚注行转换为Markdown格式
            marked_lines[i] = f"[^{footnote_key}]:{content}\n"

    # 处理正文中的脚注引用
    for i, line in enumerate(marked_lines):
        if i in footnote_lines_indices:
            continue  # 跳过脚注行

        # 临时存储处理后的行
        processed_line = line

        # 先找出所有拼音部分，避免处理它们
        pinyin_matches = list(pinyin.finditer(processed_line))
        pinyin_positions = []

        for match in pinyin_matches:
            start, end = match.span()
            pinyin_positions.extend(range(start, end))

        # 查找并替换脚注标记，但避开拼音部分
        for key in footnotes.keys():
            # 使用正则表达式查找独立的脚注标记
            pattern = re.compile(f"(^|[^a-zA-Z])({key})($|[^a-zA-Z])")

            # 查找所有匹配
            matches = list(pattern.finditer(processed_line))

            # 从后向前替换，避免位置变化
            for match in reversed(matches):
                start, end = match.span(2)  # 只获取脚注字符的位置

                # 检查是否在拼音范围内
                if not any(pos in pinyin_positions for pos in range(start, end)):
                    # 替换为Markdown脚注格式
                    processed_line = (
                        processed_line[:start] +
                        f"[^{key}]" +
                        processed_line[end:]
                    )

        marked_lines[i] = processed_line

    return marked_lines

def make_three_files_name(file_path):
    """
    构建一套文件名
    """
    file_name_parts = file_path.rsplit('.', 1)
    if len(file_name_parts) > 1:
        new_file_path = f"{file_name_parts[0]}.marked.{file_name_parts[1]}"
        titles_only_path = f"{file_name_parts[0]}.titles_marked.{file_name_parts[1]}"
        titles_original_path = f"{file_name_parts[0]}.titles_original.{file_name_parts[1]}"
    else:
        new_file_path = f"{file_path}.marked"
        titles_only_path = f"{file_path}.titles_marked"
        titles_original_path = f"{file_path}.titles_original"
    return new_file_path, titles_only_path, titles_original_path

def delete_blank_lines(text, max_blank_lines=1):
    """
    删除文本中的空行
    """
    # 删除纯空格行
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(fr'\n{"\n"*max_blank_lines}\n+', fr'\n{"\n"*max_blank_lines}\n', text)

    return text

import re
def delete_wrong_split(text: str) -> str:
    """
    删除错误分段

    条件是：
    1. 一行不少于30字符，最后一个是汉字，
    2. 下一行（忽略空行）开头也是汉字
    """
    # 使用多行模式 re.MULTILINE (re.M)，使 ^ 和 $ 匹配每一行的开头和结尾
    text = re.sub(r'(.{30,}[\u4e00-\u9fff])\n{1,2}([\u4e00-\u9fff])', r'\1\2', text, flags=re.MULTILINE)
    return text

def join_lines(text: str) -> str:
    """
    连接一段错误分段处

    条件是：
    1. 一行不少于30字符，最后一个是汉字，
    2. 下一行（忽略空行）开头也是汉字
    """
    lines = text.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        current_line = lines[i]

        # 检查当前行是否满足条件1：不少于30字符且最后一个字符是汉字
        if len(current_line) >= 30 and re.match(r'[\u4e00-\u9fff]', current_line[-1]):
            # 寻找下一个非空行
            next_non_empty_idx = i + 1
            while next_non_empty_idx < len(lines) and not lines[next_non_empty_idx].strip():
                next_non_empty_idx += 1

            # 检查是否找到了下一个非空行，并且它的第一个字符是汉字
            if (next_non_empty_idx < len(lines) and
                lines[next_non_empty_idx].strip() and
                re.match(r'[\u4e00-\u9fff]', lines[next_non_empty_idx][0])):

                # 连接当前行和下一个非空行
                result_lines.append(current_line + lines[next_non_empty_idx])

                # 跳过已经连接的行
                i = next_non_empty_idx + 1
                continue

        # 如果不满足连接条件，直接添加当前行
        result_lines.append(current_line)
        i += 1

    return '\n'.join(result_lines)

if __name__ == "__main__":

    # 处理样式文本如`[text]{.s16}`
    style_dic = {
        '1.21 汉魏晋六朝（上）':[(19,"zhuzm"),(20,"zhuzm"),(24,"daodu"),(25,"zhutm"),(27,"zhuzm"),(37,"zhuzm"),(38,"zhutm"),(43,"zhuzm"),],
        '1.21 汉魏晋六朝（下册）':[(19,"zhuzm"),(20,"zhuzm"),(29,"daodu"),(30,"zhutm"),(32,"zhuzm"),(33,"zhuzm"),(40,"zhuzm"),],
        '1.21 宋词上（未转曲）':[(20,"zhuzm"),(26,"daodu"),(28,"zhutm"),(30,"zhuzm"),(32,"zhuzm"),(35,"zhuzm"),(36,"zhuzm"),],
        '1.21 宋词中':[(19,"zhuzm"),(20,"zhutm"),(24,"daodu"),(28,"zhuzm"),(32,"zhuzm"),(34,"zhuzm"),(37,"zhutm"),],
        '1.21 宋词下':[(17,"zhuzm"),(25,"zhutm"),(31,"zhuzm"),(35,"zhuzm"),],
        '1.21 宋诗':[(15,"zhuzm"),(20,"zhutm"),(23,"daodu"),(24,"zhuzm"),(27,"zhuzm"),(28,"zhuzm"),(35,"zhuzm"),],
        '1.21 唐诗上册':[(17,"zhuzm"),(22,"zhuzm"),(25,"daodu"),(32,"zhuzm"),(33,"zhuzm"),(35,"zhuzm"),(36,"zhuzm"),(37,"zhuzm"),],
        '1.21 唐诗中册':[(19,"zhuzm"),(23,"zhuzm"),(25,"daodu"),(26,"zhutm"),(29,"zhuzm"),(33,"zhuzm"),(36,"zhuzm"),(37,"zhuzm"),(39,"zhuzm"),],
        '1.21 唐诗下册':[(19,"zhuzm"),(20,"zhuzm"),(21,"zhuzm"),(23,"zhuzm"),(25,"zhutm"),(28,"daodu"),(30,"zhuzm"),(34,"zhuzm"),(35,"zhuzm"),(40,"zhuzm"),],
        '1.21 题画诗':[(18,"zhuzm"),(20,"zhutm"),(21,"zhuzm"),(25,"daodu"),(29,"zhuzm"),(33,"zhuzm"),],
        '1.21 先秦诗':[(19,"zhuzm"),(21,"zhutm"),(28,"daodu"),(31,"zhuzm"),(38,"zhuzm"),(39,"zhutm"),(43,"zhutm"),(47,"zhuzm"),],
        '1.21 元散曲':[(9,"zhuzm"),(10,"zhuzm"),(20,"zhuzm"),(23,"daodu"),(39,"zhuzm"),],
        '1.21 元杂剧':[(16,"zhuzm"),(17,"zhuzm"),(19,"zhutm"),(27,"daodu"),],
    }

    # 示例文件路径
    root_path = '13本传统文化/HTML转md及整理目录'
    file_names = [
        '1.21 先秦诗',
        '1.21 汉魏晋六朝（上）',
        '1.21 汉魏晋六朝（下册）',
        '1.21 唐诗上册',
        '1.21 唐诗中册',
        '1.21 唐诗下册',
        '1.21 宋诗',
        '1.21 宋词上（未转曲）',
        '1.21 宋词中',
        '1.21 宋词下',
        '1.21 题画诗',
        '1.21 元散曲',
        '1.21 元杂剧',
    ]
    for file_name in file_names:

        file_path = f'{root_path}/{file_name}.md'
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()

        # 删除图像链接
        text = delete_image(text)

        # 替换样式
        # 定义替换模板，使用$1作为内容占位符
        style_replace_pattern = {
            "zhuzm": "[^$1]",
            "zhutm": "\n\n[^$1]: ",
            "daodu": "【$1】"
        }
        # 创建样式码到替换模式的映射
        code_replace_pattern_map = {x[0]: style_replace_pattern[x[1]] for x in style_dic[file_name]}
        text, replacement_records = mark_style(text, code_replace_pattern_map, default_replace_pattern="$1")
        print(replacement_records)

        # 标记脚注
        lines = mark_footnotes_from_list(text.split('\n'))

        # 删除行头空格
        lines = [line.lstrip() for line in lines]
        # 删除空行
        text = delete_blank_lines("\n".join(lines))
        # 连接前言和目录行
        text = re.sub(r'\n前\n\n言\n', r'\n前言\n',text)
        text = re.sub(r'\n目\n\n录\n', r'\n目录\n',text)

        # # 标记标题
        # 整理好的目录列表
        with open(f'{root_path}/{file_name}.目录.md', 'r', encoding='utf-8') as file:
            content = file.read()
        toc_items = parse_toc(content)
        lines, not_found = mark_titles(text.split('\n'), toc_items)
        if not_found:
            print("\n未找到的目录项:")
            for item in not_found:
                print(f"- {item['name']} (级别: {item['level']})")

        # 删除错误分段
        text = delete_wrong_split("\n".join(lines))

        with open(f'{root_path}/{file_name}.clean.md', 'w', encoding='utf-8') as file:
            file.writelines(text)
"""
高级HTML优化脚本 - 更激进的压缩策略
"""
import re
from pathlib import Path
from html import escape, unescape


def remove_duplicate_text_in_data_attrs(content):
    """移除data-text属性中与显示内容完全相同的文本（仅对完全匹配的行）"""
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', content, flags=re.DOTALL)
    if not tbody_match:
        return content

    tbody_content = tbody_match.group(1)

    # 匹配每一行
    def optimize_row(match):
        row_html = match.group(0)

        # 检查是否是完全匹配（similarity=1.0000）
        if 'data-similarity="1.0000"' not in row_html:
            return row_html  # 不完全匹配，保留data-text用于diff

        # 提取data-text-a和data-text-b
        text_a_match = re.search(r'data-text-a="([^"]*)"', row_html)
        text_b_match = re.search(r'data-text-b="([^"]*)"', row_html)

        if not text_a_match or not text_b_match:
            return row_html

        text_a = unescape(text_a_match.group(1))
        text_b = unescape(text_b_match.group(1))

        # 提取显示内容
        cell_a_match = re.search(r'<span class="sentence-a">(.*?)</span>', row_html, re.DOTALL)
        cell_b_match = re.search(r'<span class="sentence-b">(.*?)</span>', row_html, re.DOTALL)

        if cell_a_match and cell_b_match:
            display_a = unescape(cell_a_match.group(1).strip())
            display_b = unescape(cell_b_match.group(1).strip())

            # 如果data-text与显示内容完全相同，移除data-text（保留空字符串）
            if text_a == display_a:
                row_html = re.sub(r'data-text-a="[^"]*"', 'data-text-a=""', row_html)
            if text_b == display_b:
                row_html = re.sub(r'data-text-b="[^"]*"', 'data-text-b=""', row_html)

        return row_html

    # 匹配所有tr行
    tbody_content = re.sub(
        r'<tr[^>]*>.*?</tr>',
        optimize_row,
        tbody_content,
        flags=re.DOTALL
    )

    return content.replace(tbody_match.group(0), f'<tbody>{tbody_content}</tbody>')


def compress_attributes(content):
    """压缩HTML属性：移除默认值、简化布尔属性"""
    # 移除data-diff-mode="false"（这是默认值）
    content = re.sub(r'\s+data-diff-mode="false"', '', content)

    # 简化class属性（去重）
    def simplify_class(match):
        classes = match.group(1).split()
        unique_classes = sorted(set(classes))
        return f'class="{" ".join(unique_classes)}"'

    content = re.sub(r'class="([^"]+)"', simplify_class, content)

    return content


def minify_html(content):
    """最小化HTML：去除所有不必要的空白"""
    # 移除HTML注释（保留条件注释）
    content = re.sub(r'<!--(?!\[if)[\s\S]*?-->', '', content)

    # 压缩script和style内的空白（但保留必要的换行）
    def compress_inner(match):
        tag = match.group(1)
        inner = match.group(2)
        # 压缩多个空格为单个空格
        inner = re.sub(r'[ \t]+', ' ', inner)
        # 移除多余换行
        inner = re.sub(r'\n\s*\n+', '\n', inner)
        # 移除行首行尾空白
        inner = re.sub(r'^\s+|\s+$', '', inner, flags=re.MULTILINE)
        return f'<{tag}>{inner}</{tag}>'

    content = re.sub(r'<(script|style)>(.*?)</\1>', compress_inner, content, flags=re.DOTALL)

    # 压缩标签之间的空白
    content = re.sub(r'>\s+<', '><', content)

    # 移除行首行尾空白
    content = re.sub(r'^\s+|\s+$', '', content, flags=re.MULTILINE)

    return content


def optimize_table_cells(content):
    """优化表格单元格：简化重复的结构"""
    # 对于完全匹配的行，可以简化结构
    # 但为了保持功能，这里只做轻微优化

    # 移除空的title属性
    content = re.sub(r'\s+title="备注内容无法保存"', '', content)

    # 简化placeholder（如果不需要）
    # content = re.sub(r'placeholder="备注"', '', content)

    return content


def main():
    input_file = Path('a1.alignment.html')
    if not input_file.exists():
        print(f"错误：找不到文件 {input_file}")
        return

    print(f"读取文件: {input_file}")
    original_content = input_file.read_text(encoding='utf-8')
    original_size = len(original_content)
    print(f"原始大小: {original_size:,} 字符 ({original_size/1024:.1f} KB)\n")

    optimized_content = original_content

    # 应用所有优化
    print("应用优化策略...")
    print("1. 压缩HTML属性...")
    optimized_content = compress_attributes(optimized_content)

    print("2. 优化表格单元格...")
    optimized_content = optimize_table_cells(optimized_content)

    print("3. 移除完全匹配行的重复data-text...")
    optimized_content = remove_duplicate_text_in_data_attrs(optimized_content)

    print("4. 最小化HTML（去除空白）...")
    optimized_content = minify_html(optimized_content)

    # 保存
    output_file = input_file.parent / f"{input_file.stem}.minified.html"
    output_file.write_text(optimized_content, encoding='utf-8')

    optimized_size = len(optimized_content)
    reduction = original_size - optimized_size
    reduction_percent = (reduction / original_size) * 100

    print(f"\n优化完成！")
    print(f"原始大小: {original_size:,} 字符 ({original_size/1024:.1f} KB)")
    print(f"优化后:   {optimized_size:,} 字符 ({optimized_size/1024:.1f} KB)")
    print(f"减少:     {reduction:,} 字符 ({reduction/1024:.1f} KB, {reduction_percent:.1f}%)")
    print(f"输出文件: {output_file}")

    # 验证文件是否仍然有效
    if '<html' in optimized_content and '</html>' in optimized_content:
        print("\n[OK] 文件结构验证通过")
    else:
        print("\n[WARNING] 警告：文件结构可能有问题")


if __name__ == '__main__':
    main()

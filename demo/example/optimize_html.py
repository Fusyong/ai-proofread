"""
HTML文件优化脚本
通过多种方式减小HTML文件大小
"""
import re
import html
from pathlib import Path


def compress_html(content):
    """压缩HTML：去除多余空白、压缩属性"""
    # 移除HTML注释（保留条件注释）
    content = re.sub(r'<!--(?!\[if)[\s\S]*?-->', '', content)

    # 压缩script和style标签内的空白（保留必要的换行）
    def compress_script_style(match):
        tag = match.group(1)
        inner = match.group(2)
        # 压缩空白但保留换行
        inner = re.sub(r'[ \t]+', ' ', inner)
        inner = re.sub(r'\n\s*\n', '\n', inner)
        return f'<{tag}>{inner}</{tag}>'

    content = re.sub(r'<(script|style)>(.*?)</\1>', compress_script_style, content, flags=re.DOTALL)

    # 压缩HTML标签之间的空白
    content = re.sub(r'>\s+<', '><', content)
    # 压缩行首行尾空白
    content = re.sub(r'^\s+|\s+$', '', content, flags=re.MULTILINE)

    return content


def optimize_table_structure(content):
    """优化表格结构：简化重复的HTML标签"""
    # 提取tbody内容
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', content, flags=re.DOTALL)
    if not tbody_match:
        return content

    tbody_content = tbody_match.group(1)

    # 优化：移除不必要的data-diff-mode="false"（默认值）
    tbody_content = re.sub(r'\s+data-diff-mode="false"', '', tbody_content)

    # 优化：简化class属性（移除重复的class）
    def simplify_class(match):
        classes = match.group(1).split()
        # 去重并排序
        unique_classes = sorted(set(classes))
        return f'class="{" ".join(unique_classes)}"'

    tbody_content = re.sub(r'class="([^"]+)"', simplify_class, tbody_content)

    # 替换回tbody
    content = content.replace(tbody_match.group(0), f'<tbody>{tbody_content}</tbody>')

    return content


def extract_external_resources(content, output_dir='.'):
    """将CSS和JavaScript提取到外部文件"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # 提取CSS
    css_match = re.search(r'<style>(.*?)</style>', content, flags=re.DOTALL)
    if css_match:
        css_content = css_match.group(1).strip()
        css_file = output_dir / 'alignment.css'
        css_file.write_text(css_content, encoding='utf-8')
        # 替换为外部链接
        content = content.replace(
            css_match.group(0),
            f'<link rel="stylesheet" href="{css_file.name}">'
        )

    # 提取JavaScript
    script_match = re.search(r'<script>(.*?)</script>', content, flags=re.DOTALL)
    if script_match and 'src=' not in script_match.group(0):
        js_content = script_match.group(1).strip()
        js_file = output_dir / 'alignment.js'
        js_file.write_text(js_content, encoding='utf-8')
        # 替换为外部链接
        content = content.replace(
            script_match.group(0),
            f'<script src="{js_file.name}"></script>'
        )

    return content


def remove_redundant_data_attributes(content):
    """移除冗余的data属性：如果显示内容与data-text相同，可以只保留一个"""
    # 这个优化需要更仔细的处理，因为data-text用于diff对比
    # 暂时保留，但可以优化格式
    return content


def main():
    input_file = Path('a1.alignment.html')
    if not input_file.exists():
        print(f"错误：找不到文件 {input_file}")
        return

    print(f"读取文件: {input_file}")
    original_content = input_file.read_text(encoding='utf-8')
    original_size = len(original_content)
    print(f"原始大小: {original_size:,} 字符 ({original_size/1024:.1f} KB)")

    # 应用优化
    optimized_content = original_content

    # 1. 优化表格结构
    print("\n1. 优化表格结构...")
    optimized_content = optimize_table_structure(optimized_content)

    # 2. 压缩HTML
    print("2. 压缩HTML（去除多余空白）...")
    optimized_content = compress_html(optimized_content)

    # 3. 提取外部资源（默认不提取，保持单文件）
    extract_external = False  # 改为False以保持单文件，或True以提取外部资源
    if extract_external:
        print("3. 提取CSS和JavaScript到外部文件...")
        optimized_content = extract_external_resources(optimized_content)

    # 保存优化后的文件
    output_file = input_file.parent / f"{input_file.stem}.optimized.html"
    output_file.write_text(optimized_content, encoding='utf-8')

    optimized_size = len(optimized_content)
    reduction = original_size - optimized_size
    reduction_percent = (reduction / original_size) * 100

    print(f"\n优化完成！")
    print(f"原始大小: {original_size:,} 字符 ({original_size/1024:.1f} KB)")
    print(f"优化后:   {optimized_size:,} 字符 ({optimized_size/1024:.1f} KB)")
    print(f"减少:     {reduction:,} 字符 ({reduction/1024:.1f} KB, {reduction_percent:.1f}%)")
    print(f"输出文件: {output_file}")


if __name__ == '__main__':
    main()

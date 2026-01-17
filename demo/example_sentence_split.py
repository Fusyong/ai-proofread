"""
中文句子切分功能使用示例

展示 split_chinese_sentences() 函数的使用方法和各种边界情况的处理
"""

from src.splitter import split_chinese_sentences, split_chinese_sentences_simple

def example_1_basic():
    """示例1：基本句子切分"""
    print("=" * 60)
    print("示例1：基本句子切分")
    print("=" * 60)

    text = "这是第一句话。这是第二句话！这是第三句话？"
    sentences = split_chinese_sentences_simple(text)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def example_2_with_quotes():
    """示例2：带引号的句子"""
    print("=" * 60)
    print("示例2：带引号的句子（引号内的句号不切分）")
    print("=" * 60)

    text = '他说："你好。"然后离开了。'
    sentences = split_chinese_sentences_simple(text)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def example_3_decimal():
    """示例3：小数点识别"""
    print("=" * 60)
    print("示例3：小数点识别（3.14中的.不是句子结尾）")
    print("=" * 60)

    text = "圆周率是3.14。这是正常句子。"
    sentences = split_chinese_sentences_simple(text)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def example_4_markdown():
    """示例4：Markdown格式文本"""
    print("=" * 60)
    print("示例4：Markdown格式文本（标题、列表项等）")
    print("=" * 60)

    text = """# 一级标题

这是第一段的第一句话。这是第一段的第二句话！

## 二级标题

这是第二段的内容。这是第二段的另一句话？

- 列表项一，有标点。
- 列表项二，没有标点
- 列表项三。

1. 有序列表一
2. 有序列表二。
3. 有序列表三

这是普通段落。这是另一句话！"""

    sentences = split_chinese_sentences(text, preserve_formatting=True)

    for i, s in enumerate(sentences, 1):
        # 只显示前80个字符
        display = s[:80] + "..." if len(s) > 80 else s
        print(f"{i}. {display}")
    print()

def example_5_special_cases():
    """示例5：特殊情况"""
    print("=" * 60)
    print("示例5：特殊情况处理")
    print("=" * 60)

    text = """数字3.14是圆周率。这是正常句子。
他说："这是引号内的内容。"
（注：这是注释内容。）
列表项没有标点
但这也是一个句子。"""

    sentences = split_chinese_sentences(text)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def example_6_ellipsis():
    """示例6：省略号处理"""
    print("=" * 60)
    print("示例6：省略号处理")
    print("=" * 60)

    text = "他说了很多话…然后离开了。还有……这样的情况。"
    sentences = split_chinese_sentences_simple(text)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

if __name__ == "__main__":
    example_1_basic()
    example_2_with_quotes()
    example_3_decimal()
    example_4_markdown()
    example_5_special_cases()
    example_6_ellipsis()

    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


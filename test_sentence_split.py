"""
测试中文句子切分功能
"""

from src.splitter import split_chinese_sentences, split_chinese_sentences_simple

def test_basic_sentences():
    """测试基本句子切分"""
    text = "这是第一句话。这是第二句话！这是第三句话？"
    sentences = split_chinese_sentences_simple(text)
    print("基本句子测试:")
    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def test_with_quotes():
    """测试带引号的句子"""
    text = '他说："你好。"然后离开了。'
    sentences = split_chinese_sentences_simple(text)
    print("带引号句子测试:")
    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

def test_markdown_formatting():
    """测试Markdown格式文本"""
    text = """# 一级标题

这是第一段的第一句话。这是第一段的第二句话！

## 二级标题

这是第二段的内容。这是第二段的另一句话？

- 列表项一
- 列表项二，没有标点
- 列表项三。

1. 有序列表一
2. 有序列表二。
3. 有序列表三

这是普通段落。这是另一句话！"""

    sentences = split_chinese_sentences(text, preserve_formatting=True)
    print("Markdown格式句子测试:")
    for i, s in enumerate(sentences, 1):
        print(f"{i}. {repr(s[:50])}...")
    print()

def test_special_cases():
    """测试特殊情况"""
    text = """数字3.14是圆周率。这是正常句子。
他说："这是引号内的内容。"
（注：这是注释内容。）
列表项没有标点
但这也是一个句子。"""

    sentences = split_chinese_sentences(text, preserve_formatting=True)
    print("特殊情况测试:")
    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
    print()

if __name__ == "__main__":
    test_basic_sentences()
    test_with_quotes()
    test_markdown_formatting()
    test_special_cases()


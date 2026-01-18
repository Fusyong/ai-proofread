"""
详细测试句子切分逻辑，特别是行末句号的情况
"""
import re
from src.splitter import split_chinese_sentences_simple

# 创建一个简单的测试文本
test_text = """1 第一句话。这是第二句话。
2 第三句话。
3 第四句话。

4 第五句话。"""

print("=" * 80)
print("测试文本：")
print("=" * 80)
for i, line in enumerate(test_text.split('\n'), 1):
    print(f"{i}: {repr(line)}")

print("\n" + "=" * 80)
print("切分结果：")
print("=" * 80)

sentences = split_chinese_sentences_simple(test_text)
for i, sentence in enumerate(sentences, 1):
    print(f"\n句子 {i}:")
    print(f"  内容: {repr(sentence)}")
    print(f"  长度: {len(sentence)}")
    print(f"  包含换行符: {'\\n' in sentence}")
    
    # 检查在原文中的位置
    pos = test_text.find(sentence)
    if pos >= 0:
        print(f"  位置: {pos}")
        # 显示该位置前后的文本
        start = max(0, pos - 10)
        end = min(len(test_text), pos + len(sentence) + 10)
        context = test_text[start:end]
        print(f"  上下文: {repr(context)}")
        
        # 检查句子后面是什么
        after_pos = pos + len(sentence)
        if after_pos < len(test_text):
            after_text = test_text[after_pos:after_pos+10]
            print(f"  句子后的内容: {repr(after_text)}")

# 测试正则表达式
print("\n" + "=" * 80)
print("正则表达式匹配测试：")
print("=" * 80)
pattern = r'([。！？…]+[”'）\]】」』]*)|([.!?]+["'"'）\]】」』]*)|(\n(\s*\n)+)'
for match in re.finditer(pattern, test_text):
    print(f"匹配位置: {match.start()}-{match.end()}, 内容: {repr(test_text[match.start():match.end()])}")

# 临时测试文件
import sys
sys.path.insert(0, '.')

from src.splitter import split_chinese_sentences

test_text = '明入道之要也。始条理者'
result = split_chinese_sentences(test_text, True)

print('测试文本:', test_text)
print('Python结果:', result)
print('句子数量:', len(result))
print('预期: 应该切分为2个句子')
print('实际:', '✓ 通过' if len(result) == 2 else '✗ 失败')

if len(result) == 2:
    print('句子1:', result[0])
    print('句子2:', result[1])
    print('预期句子1: 明入道之要也。')
    print('预期句子2: 始条理者')
    print('句子1匹配:', '✓' if result[0] == '明入道之要也。' else '✗')
    print('句子2匹配:', '✓' if result[1] == '始条理者' else '✗')

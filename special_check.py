"""专项检查用例"""

from src.special_checker import check_to_cscc

# 测试通用规范汉字表检查
results = check_to_cscc("""
鼕
囯
鍾
钟
鈡
锺
鐘
""")
for result in results:
    print(f"类型: {result.error_type}")
    print(f"位置: {result.location}")
    print(f"原文: {result.original_text}")
    print(f"提示: {result.suggestion}")
    # print(f"置信度: {result.confidence}")
    print("---")

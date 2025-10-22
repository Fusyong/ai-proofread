"""专项检查用例"""

from src.special_checker import check_to_cscc

# 测试通用规范汉字表检查
with open("E:/语文出版社/2025/蒙学经典古今读/稿件/20251008养正图解-标点/20251008养正图解.proofread.json.md","r", encoding="utf-8") as f:
    text = f.read()
    results = check_to_cscc(text)
    with open("special_check_result.csv", "w", encoding="utf-16") as out_f:
        for result in results:
            out_f.write(f"{result.original_text},{result.error_type},{result.suggestion}\n")

# results = check_to_cscc("""
# 鼕
# 囯
# 鍾
# 钟
# 鈡
# 锺
# 鐘
# """)
# for result in results:
#     print(f"类型: {result.error_type}")
#     print(f"位置: {result.location}")
#     print(f"原文: {result.original_text}")
#     print(f"提示: {result.suggestion}")
#     # print(f"置信度: {result.confidence}")
#     print("---")

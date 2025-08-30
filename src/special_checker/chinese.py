

def is_chinese_character(char: str) -> bool:
    """判断是否是中文字符 TODO 有待于扩展字符集

    """
    return '\u4e00' <= char <= '\u9fff'

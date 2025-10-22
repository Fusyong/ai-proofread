"""结构化序列标记检查工具。

包含：规则加载、匹配扫描、重叠消解、树构建、连续性校验与报告渲染。
"""

__all__ = [
    "check_text_with_rules",
]

def check_text_with_rules(*args, **kwargs):  # noqa: D401
    """转调到核心实现。"""
    from .check_structure import check_text_with_rules as _impl
    return _impl(*args, **kwargs)



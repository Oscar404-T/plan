"""工具函数模块

包含一些常用的工具函数
"""


def calculate_size(length: float, width: float) -> float:
    """根据长度和宽度计算尺寸（英寸）
    
    公式：sqrt(length^2 + width^2) / 25.4
    """
    return (length ** 2 + width ** 2) ** 0.5 / 25.4


def calculate_required_input(quantity: int, yield_rate: float) -> int:
    """根据数量和良率计算所需投入量
    
    投入量 = 出货数量 / (估计良率/100)
    """
    if yield_rate and yield_rate > 0:
        return int(quantity / (yield_rate / 100.0))
    return quantity


def format_datetime_chinese(dt) -> str:
    """将日期时间格式化为中文显示格式"""
    if dt:
        return dt.strftime('%Y年%m月%d日 %H:%M')
    return '—'


def format_duration_hours(td) -> str:
    """将时间差格式化为小时数"""
    if td:
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        return f"{hours}小时"
    return '—'
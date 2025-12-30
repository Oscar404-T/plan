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


def calculate_max_cutting_count(original_length: float, original_width: float, product_length: float, product_width: float) -> int:
    """计算最大切数
    
    根据原玻尺寸和产品尺寸计算最大切数，考虑：
    - 叠层点胶偏移：单边4mm
    - 辅助裂片：单边2mm
    - 考虑产品旋转90度的情况以获得更大切数
    """
    if not original_length or not original_width or not product_length or not product_width:
        return 0
    
    # 实际可用尺寸 = 原玻尺寸 - (叠层点胶偏移4mm * 2 + 辅助裂片2mm * 2)
    available_length = original_length - (4 + 2) * 2  # 减去双边偏移和裂片
    available_width = original_width - (4 + 2) * 2
    
    # 验证可用尺寸是否合理
    if available_length <= 0 or available_width <= 0:
        return 0

    # 计算正常方向的切数
    cuts_along_length_normal = int(available_length / product_length)
    cuts_along_width_normal = int(available_width / product_width)
    max_cutting_count_normal = cuts_along_length_normal * cuts_along_width_normal
    
    # 计算旋转90度方向的切数（产品长度和宽度交换）
    cuts_along_length_rotated = int(available_length / product_width)
    cuts_along_width_rotated = int(available_width / product_length)
    max_cutting_count_rotated = cuts_along_length_rotated * cuts_along_width_rotated
    
    # 返回两个方向中较大的切数
    max_cutting_count = max(max_cutting_count_normal, max_cutting_count_rotated)
    
    return max(max_cutting_count, 0)  # 确保返回非负数


def calculate_layers(thickness: float) -> str:
    """根据板厚计算叠数，满足公式：
    8μm * (叠数 + 1) + 板厚μm * 叠数 + 0.8mm <= 1.3mm
    """
    if not thickness or thickness <= 0:
        return "N/A"
    
    # 转换单位到微米，使公式中的单位一致
    # 8μm * (layers + 1) + thickness*μm * layers + 0.8mm <= 1.3mm
    # 转换为相同单位：0.8mm = 800μm, 1.3mm = 1300μm
    base_thickness_micron = 800  # 0.8mm = 800微米
    max_thickness_micron = 1300  # 1.3mm = 1300微米
    spacing_micron = 8  # 8微米
    
    # 公式：spacing * (layers + 1) + thickness * layers + base_thickness <= max_thickness
    # 展开：spacing * layers + spacing + thickness * layers + base_thickness <= max_thickness
    # 合并：(spacing + thickness) * layers <= max_thickness - spacing - base_thickness
    # 求解：layers <= (max_thickness - spacing - base_thickness) / (spacing + thickness)
    
    numerator = max_thickness_micron - spacing_micron - base_thickness_micron
    denominator = spacing_micron + thickness
    
    if denominator <= 0:
        return "N/A"
    
    max_layers = numerator / denominator
    
    # 如果计算结果为负数，说明条件无法满足
    if max_layers < 0:
        return "0"
    
    # 返回整数部分，确保不超过最大允许叠数
    return f"{int(max_layers)}"

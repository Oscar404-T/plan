"""班次枚举定义"""

from enum import Enum

class ShiftEnum(str, Enum):
    day = "day"
    night = "night"
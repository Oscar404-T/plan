"""CRUD模块初始化"""

from .crud import (
    get_user,
    get_user_by_email,
    create_user,
    create_capacity,
    list_capacities,
    get_capacity_by_shift,
    create_operation,
    list_operations,
    create_admin,
    get_admin_by_username,
    verify_admin_credentials,
    create_order,
    get_order,
    get_order_operations,
    list_orders,
)

# 导出所有函数以供外部模块使用
__all__ = [
    "get_user",
    "get_user_by_email",
    "create_user",
    "create_capacity",
    "list_capacities",
    "get_capacity_by_shift",
    "create_operation",
    "list_operations",
    "create_admin",
    "get_admin_by_username",
    "verify_admin_credentials",
    "create_order",
    "get_order",
    "get_order_operations",
    "list_orders",
]
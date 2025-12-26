"""排程核心逻辑

根据订单需求和产能约束，计算最优排程方案。
支持小时、班次、天三种时间粒度的排程和可视化。
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from .. import models
from sqlalchemy.orm import Session
from ..db import get_db
import math


def get_shift_for_hour(dt) -> str:
    """根据datetime对象判断班次"""
    if isinstance(dt, datetime):
        hour = dt.hour
    else:
        hour = dt
    if 8 <= hour < 20:
        return "白班"
    else:
        return "夜班"


def get_capacity_by_shift(db: Session, shift: str):
    """根据班次获取产能"""
    from ..crud import list_capacities
    capacities = list_capacities(db)
    for cap in capacities:
        if shift in cap.description or cap.shift == shift:
            return cap
    # 如果没有找到特定班次的产能，则返回默认值
    return type('obj', (object,), {
        'shift': shift,
        'pieces_per_hour': 10,
        'description': f'{shift} 默认产能'
    })()


def schedule_order_operations(start: datetime, due: datetime, length: float, width: float, required_input: int, operations: list, capacity_lookup):
    """计算订单工序排程 - 旧接口，用于兼容现有调用"""
    # 如果没有工序，返回空的分配列表
    if not operations:
        return {
            "allocations": [],
            "total_allocated": 0,
            "meets_due": True,
            "expected_completion": start,
            "meets_due_estimate": True
        }
    
    # 流水线排程：每个工序可以并行处理不同批次的产品
    allocations = []
    
    # 为每个工序维护一个开始时间
    current_times = [start] * len(operations)
    
    # 计算每个工序的产能（pieces per hour）
    op_capacities = []
    for op_info in operations:
        op_name = op_info["name"]
        
        # 检查capacity_lookup是否是函数（需要两个参数）还是字典
        if callable(capacity_lookup):
            # 如果是函数，尝试调用它获取产能信息
            # 这里使用current_time作为时间参数
            try:
                # 首先尝试使用两个参数调用（op_name, dt）
                capacity_info = capacity_lookup(op_name, start)
                # 如果返回的是一个数字，说明是pieces_per_hour
                if isinstance(capacity_info, (int, float)):
                    pieces_per_hour = capacity_info
                # 否则假设返回的是一个字典
                else:
                    pieces_per_hour = capacity_info.get('pieces_per_hour', 10) if isinstance(capacity_info, dict) else 10
            except TypeError:
                # 如果调用失败（参数错误），说明函数只需要一个参数
                capacity_info = capacity_lookup(op_name)
                pieces_per_hour = capacity_info.get('pieces_per_hour', 10) if isinstance(capacity_info, dict) else 10
        else:
            # 如果是字典，直接使用.get()方法
            capacity_info = capacity_lookup.get(op_name, {})
            pieces_per_hour = capacity_info.get('pieces_per_hour', 10)
        
        # 确保pieces_per_hour不为0，避免除零错误
        if pieces_per_hour <= 0:
            pieces_per_hour = 10  # 使用默认值
        
        op_capacities.append(pieces_per_hour)
    
    # 分批处理，每次处理一个批次
    batch_size = 100  # 每批处理100个产品
    processed = 0
    
    while processed < required_input:
        batch = min(batch_size, required_input - processed)
        
        # 处理当前批次的每个工序
        for i, op_info in enumerate(operations):
            op_name = op_info["name"]
            pieces_per_hour = op_capacities[i]
            
            # 计算完成当前批次所需的时间
            hours_needed = math.ceil(batch / pieces_per_hour)
            start_time = current_times[i]
            end_time = start_time + timedelta(hours=hours_needed)
            
            # 确定班次
            shift_type = get_shift_for_hour(start_time)
            
            # 将分配信息添加到列表中，格式为 (start, end, shift, op_name, allocated)
            allocations.append((start_time, end_time, shift_type, op_name, batch))
            
            # 更新该工序的下一批次开始时间
            current_times[i] = end_time
        
        processed += batch
    
    # 计算总分配量
    total_allocated = sum(item[4] for item in allocations)
    
    # 确保current_times不为空
    final_completion_time = current_times[-1] if current_times else start
    
    # 返回字典格式，与原来的实现兼容
    # 包含allocations元组列表，以及统计信息
    return {
        "allocations": allocations,
        "total_allocated": total_allocated,
        "meets_due": final_completion_time <= due,  # 最后一个工序的结束时间
        "expected_completion": final_completion_time if final_completion_time <= due else None,
        "meets_due_estimate": final_completion_time <= due
    }


def calculate_order_schedule(db: Session, order_id: int):
    """计算订单工序排程 - 新接口，用于数据库订单"""
    # 获取订单和工序信息
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    operations = db.query(models.OrderOperation).filter(
        models.OrderOperation.order_id == order_id
    ).order_by(models.OrderOperation.seq).all()
    
    if not operations:
        return []
    
    # 获取工序详情
    operation_details = []
    for op in operations:
        op_model = db.query(models.Operation).filter(models.Operation.id == op.operation_id).first()
        operation_details.append({
            'id': op.id,
            'name': op_model.name,
            'pieces_per_hour': op.pieces_per_hour or op_model.default_pieces_per_hour or 10,
            'seq': op.seq,
            'total_pieces': order.quantity  # 总件数
        })
    
    # 计算每道工序的开始时间和持续时间
    schedule_items = []
    current_time = datetime.combine(order.due_datetime.date(), datetime.min.time())
    
    for op_detail in operation_details:
        # 计算完成该工序所需的时间（小时）
        required_hours = math.ceil(op_detail['total_pieces'] / op_detail['pieces_per_hour'])
        
        # 创建排程项
        start_time = current_time
        end_time = current_time + timedelta(hours=required_hours)
        
        # 计算经过的班次
        shift_count = 0
        temp_time = start_time
        while temp_time < end_time:
            if 8 <= temp_time.hour < 20:
                shift_type = "白班"
            else:
                shift_type = "夜班"
            
            # 计算当前班次剩余时间
            if shift_type == "白班":
                shift_end = temp_time.replace(hour=20, minute=0, second=0, microsecond=0)
            else:
                if temp_time.hour < 8:
                    shift_end = temp_time.replace(hour=8, minute=0, second=0, microsecond=0)
                else:
                    shift_end = (temp_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            
            if shift_end > end_time:
                shift_end = end_time
            
            # 计算该班次内的产能
            shift_duration = (shift_end - temp_time).total_seconds() / 3600
            shift_capacity = op_detail['pieces_per_hour'] * shift_duration
            
            schedule_items.append({
                'operation_id': op_detail['id'],
                'operation_name': op_detail['name'],
                'start_time': temp_time,
                'end_time': shift_end,
                'shift_type': shift_type,
                'shift_date': temp_time.date(),
                'shift_capacity': shift_capacity,
                'total_pieces': op_detail['total_pieces'],
                'remaining_pieces': max(0, op_detail['total_pieces'] - sum([item['shift_capacity'] for item in schedule_items if item['operation_name'] == op_detail['name']])),
                'order_id': order_id,
                'order_name': f"{order.internal_model or '订单'}-{order.id}"
            })
            
            temp_time = shift_end
        
        # 更新当前时间到下一道工序的开始时间
        current_time = end_time
    
    # 按时间顺序排序
    schedule_items.sort(key=lambda x: (x['start_time'], x['operation_name']))
    
    return schedule_items


def get_detailed_schedule_data(db: Session, order_id: int, time_granularity: str = 'hour'):
    """获取用于甘特图的详细数据"""
    schedule_items = calculate_order_schedule(db, order_id)
    
    # 根据时间粒度调整数据格式
    if time_granularity == 'hour':
        return _format_hourly_data(schedule_items)
    elif time_granularity == 'shift':
        return _format_shift_data(schedule_items)
    elif time_granularity == 'day':
        return _format_daily_data(schedule_items)
    else:
        return schedule_items


def _format_hourly_data(schedule_items: List[Dict]) -> Dict:
    """格式化小时级数据"""
    # 为每个小时创建详细的时间节点
    hourly_data = []
    for item in schedule_items:
        start = item['start_time']
        end = item['end_time']
        duration = (end - start).total_seconds() / 3600  # 持续小时数
        current = start
        hour_count = 0
        
        while current < end:
            next_hour = current + timedelta(hours=1)
            if next_hour > end:
                next_hour = end
            
            hour_data = item.copy()
            hour_data['start_time'] = current
            hour_data['end_time'] = next_hour
            hour_data['time_label'] = current.strftime('%m-%d %H:%M')
            hour_data['duration'] = (next_hour - current).total_seconds() / 3600
            hour_data['hour_index'] = hour_count
            hour_data['shift_type'] = get_shift_for_hour(current)
            
            hourly_data.append(hour_data)
            current = next_hour
            hour_count += 1
    
    return {
        'items': hourly_data,
        'time_labels': [item['time_label'] for item in hourly_data],
        'x_axis_type': 'time',
        'x_axis_format': 'hourly'
    }


def _format_shift_data(schedule_items: List[Dict]) -> Dict:
    """格式化班次级数据"""
    shift_data = []
    processed_shifts = set()
    
    for item in schedule_items:
        shift_key = (item['shift_date'], item['shift_type'])
        if shift_key not in processed_shifts:
            # 找到该班次的所有工序
            shift_items = [i for i in schedule_items 
                          if (i['shift_date'] == item['shift_date'] and 
                              i['shift_type'] == item['shift_type'])]
            
            for shift_item in shift_items:
                shift_item_copy = shift_item.copy()
                shift_item_copy['time_label'] = f"{shift_item['shift_date'].strftime('%m-%d')} {shift_item['shift_type']}"
                shift_item_copy['shift_key'] = f"{shift_item['shift_date']}-{shift_item['shift_type']}"
                shift_data.append(shift_item_copy)
            
            processed_shifts.add(shift_key)
    
    return {
        'items': shift_data,
        'time_labels': [f"{item['shift_date'].strftime('%m-%d')} {item['shift_type']}" 
                       for item in shift_data],
        'x_axis_type': 'shift',
        'x_axis_format': 'shiftly'
    }


def _format_daily_data(schedule_items: List[Dict]) -> Dict:
    """格式化天级数据"""
    daily_data = []
    processed_days = set()
    
    for item in schedule_items:
        day = item['shift_date']
        if day not in processed_days:
            # 找到该天的所有工序
            day_items = [i for i in schedule_items if i['shift_date'] == day]
            
            for day_item in day_items:
                day_item_copy = day_item.copy()
                day_item_copy['time_label'] = day_item['shift_date'].strftime('%m-%d')
                day_item_copy['day_key'] = day_item['shift_date'].strftime('%Y-%m-%d')
                daily_data.append(day_item_copy)
            
            processed_days.add(day)
    
    return {
        'items': daily_data,
        'time_labels': [item['time_label'] for item in daily_data],
        'x_axis_type': 'day',
        'x_axis_format': 'daily'
    }

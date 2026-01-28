"""
任务黑板模块 - 用于角色间的任务发布和认领
支持协作机制，允许角色发布任务供其他角色认领
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 待认领
    CLAIMED = "claimed"      # 已认领
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


@dataclass
class BlackboardTask:
    """黑板任务结构"""
    task_id: str
    task_type: str  # "Cook", "Transport", "Craft" 等
    description: str
    priority: TaskPriority
    
    # 任务发布者
    publisher: str
    
    # 任务认领者（可选）
    claimer: Optional[str] = None
    
    # 任务状态
    status: TaskStatus = TaskStatus.PENDING
    
    # 任务参数
    item_id: Optional[int] = None
    item_count: Optional[int] = None
    target_location: Optional[str] = None
    recipe_id: Optional[int] = None
    
    # 时间戳
    created_time: float = field(default_factory=time.time)
    claimed_time: Optional[float] = None
    completed_time: Optional[float] = None
    
    # 额外信息
    metadata: Dict = field(default_factory=dict)


class TaskBlackboard:
    """
    任务黑板系统
    用于管理角色间的协作任务
    """
    
    def __init__(self):
        self.tasks: Dict[str, BlackboardTask] = {}
        self.task_counter = 0
        
    def _generate_task_id(self) -> str:
        """生成唯一任务ID"""
        self.task_counter += 1
        return f"TASK_{self.task_counter}_{int(time.time() * 1000)}"
    
    def publish_task(
        self,
        publisher: str,
        task_type: str,
        description: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> str:
        """
        发布新任务到黑板
        
        Args:
            publisher: 发布者名称
            task_type: 任务类型
            description: 任务描述
            priority: 任务优先级
            **kwargs: 其他任务参数
            
        Returns:
            task_id: 任务ID
        """
        task_id = self._generate_task_id()
        task = BlackboardTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            priority=priority,
            publisher=publisher,
            **kwargs
        )
        self.tasks[task_id] = task
        print(f"[TaskBlackboard] {publisher} 发布任务: {description} (ID: {task_id})")
        return task_id
    
    def claim_task(self, task_id: str, claimer: str) -> bool:
        """
        认领任务
        
        Args:
            task_id: 任务ID
            claimer: 认领者名称
            
        Returns:
            bool: 是否认领成功
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.PENDING:
            return False
        
        task.claimer = claimer
        task.status = TaskStatus.CLAIMED
        task.claimed_time = time.time()
        print(f"[TaskBlackboard] {claimer} 认领任务: {task.description} (ID: {task_id})")
        return True
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status == TaskStatus.CLAIMED:
            task.status = TaskStatus.IN_PROGRESS
            return True
        return False
    
    def complete_task(self, task_id: str) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功完成
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_time = time.time()
        print(f"[TaskBlackboard] 任务完成: {task.description} (ID: {task_id})")
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = TaskStatus.CANCELLED
        print(f"[TaskBlackboard] 任务取消: {task.description} (ID: {task_id})")
        return True
    
    def get_available_tasks(
        self,
        character_name: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> List[BlackboardTask]:
        """
        获取可认领的任务列表
        
        Args:
            character_name: 角色名称（用于过滤自己发布的任务）
            task_type: 任务类型过滤
            
        Returns:
            List[BlackboardTask]: 可用任务列表
        """
        available = []
        for task in self.tasks.values():
            # 只返回待认领的任务
            if task.status != TaskStatus.PENDING:
                continue
            
            # 排除自己发布的任务
            if character_name and task.publisher == character_name:
                continue
            
            # 类型过滤
            if task_type and task.task_type != task_type:
                continue
            
            available.append(task)
        
        # 按优先级排序
        available.sort(key=lambda t: t.priority.value, reverse=True)
        return available
    
    def get_task(self, task_id: str) -> Optional[BlackboardTask]:
        """获取指定任务"""
        return self.tasks.get(task_id)
    
    def get_my_published_tasks(self, character_name: str) -> List[BlackboardTask]:
        """获取自己发布的任务"""
        return [
            task for task in self.tasks.values()
            if task.publisher == character_name
        ]
    
    def get_my_claimed_tasks(self, character_name: str) -> List[BlackboardTask]:
        """获取自己认领的任务"""
        return [
            task for task in self.tasks.values()
            if task.claimer == character_name and task.status in [TaskStatus.CLAIMED, TaskStatus.IN_PROGRESS]
        ]
    
    def cleanup_old_tasks(self, max_age_seconds: float = 3600):
        """清理旧任务"""
        current_time = time.time()
        to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                if current_time - task.created_time > max_age_seconds:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        if to_remove:
            print(f"[TaskBlackboard] 清理了 {len(to_remove)} 个旧任务")
    
    def get_summary(self) -> Dict:
        """获取黑板摘要（用于LLM）"""
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "type": task.task_type,
                    "description": task.description,
                    "priority": task.priority.name,
                    "status": task.status.value,
                    "publisher": task.publisher,
                    "claimer": task.claimer,
                    "item_id": task.item_id,
                    "item_count": task.item_count,
                    "target_location": task.target_location
                }
                for task in self.tasks.values()
                if task.status != TaskStatus.COMPLETED
            ]
        }

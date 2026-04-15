from astrbot.api import logger

from .task_database import task_database, Task
from typing import Optional, Dict, Any

class secretariat:
    ROOT_WHITELIST = [1727287294,3085866728,2739876438]

    ADMIN_WHITELIST = [1727287294,3085866728,2739876438,2437535903,2867990695,1357325271,481373196,2502251941,2656596171,3143313694,1989222166,1452745119,3524668574,2240502552,3119373459]
    
    DEPARTMENT_CONTACTS = {
        "技术部": '',
        "宣传部": '',
        "组织部": '',
        "学术部": '',
        "外联部": ''
    }
    
    SECRETARIAT_GROUP_ID = ''

    NOTICE_GROUP_ID = ''
    
    @staticmethod
    def _check_root_permission(qq_number: int) -> bool:
        return qq_number in secretariat.ROOT_WHITELIST

    @staticmethod
    def _check_permission(qq_number: int) -> bool:
        return qq_number in secretariat.ADMIN_WHITELIST
    
    @staticmethod
    def _get_contact_by_department(department: str) -> Optional[int]:
        return secretariat.DEPARTMENT_CONTACTS.get(department)
    
    @staticmethod
    def create_task(qq_number: int, content: str, deadline: str, department: str) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足，只有管理员可以创建任务"}
        
        try:
            task_id = task_database.create_task(content, deadline, department)
            
            if not task_id:
                return {"success": False, "message": "创建任务失败"}
            
            result = {
                "success": True,
                "task_id": task_id
            }
            
            return result
            
        except Exception as e:
            return {"success": False, "message": f"创建任务时发生错误: {str(e)}"}
    
    @staticmethod
    def _generate_send_info(qq_number: int, task_id: int, message_type: str, task_type: str) -> Optional[Dict[str, Any]]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "发送任务失败：权限不足"}
        
        task = task_database.get_task_by_id(task_id)
        if not task:
            return None
        
        at_id = secretariat._get_contact_by_department(task.department)
        
        # task_type 通知 更新 完结
        message_content = (
            f"【任务{task_type}】\n"
            f"任务ID: {task.id}\n"
            f"任务内容: {task.content}\n"
            f"截止时间: {task.deadline}\n"
            f"接收部门: {task.department}\n"
            f"发布时间: {task.created_time}\n\n"
            f"请回复'/收到 <任务ID>'确认任务"
            f"当然，把'收到'换成'1'也可以哦"
        )
        
        send_info = {
            "success": True,
            "content": message_content,
            "at_id": at_id,
            "message_type": message_type,
            "group_id": secretariat.NOTICE_GROUP_ID
        }
        
        return send_info
    
    @staticmethod
    def get_all_tasks(qq_number: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        tasks = task_database.get_all_tasks()
        return {
            "success": True,
            "count": len(tasks),
            "tasks": '\n\n'.join([secretariat._task_to_str(task) for task in tasks])
        }
    
    @staticmethod
    def get_pending_tasks(qq_number: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        tasks = task_database.get_pending_tasks()
        return {
            "success": True,
            "count": len(tasks),
            "tasks": '\n\n'.join([secretariat._task_to_str(task) for task in tasks])
        }
    
    @staticmethod
    def get_completed_tasks(qq_number: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        tasks = task_database.get_completed_tasks()
        return {
            "success": True,
            "count": len(tasks),
            "tasks": '\n\n'.join([secretariat._task_to_str(task) for task in tasks])
        }
    
    @staticmethod
    def get_tasks_by_department(qq_number: int, department: str) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        tasks = task_database.get_tasks_by_department(department)
        return {
            "success": True,
            "department": department,
            "count": len(tasks),
            "tasks": '\n\n'.join([secretariat._task_to_str(task) for task in tasks])
        }
    
    @staticmethod
    def get_task_by_id(qq_number: int, task_id: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        task = task_database.get_task_by_id(task_id)
        if not task:
            return {"success": False, "message": f"任务 #{task_id} 不存在"}
        
        return {
            "success": True,
            "task": secretariat._task_to_str(task)
        }
    
    @staticmethod
    def _task_to_str(task: Task) -> str:
        status_display = {
            "pending": "进行中 🔄",
            "completed": "已完成 ✅"
        }
        response_display = "已收到" if task.response_received else "未收到"
        
        return (
            f"📋 任务详情\n"
            f"━━━━━━━━━━━━━━\n"
            f"🔢 任务ID: {task.id}\n"
            f"📝 任务内容: {task.content}\n"
            f"⏰ 截止时间: {task.deadline}\n"
            f"🏢 接收部门: {task.department}\n"
            f"📊 任务状态: {status_display.get(task.status, task.status)}\n"
            f"📨 回复状态: {response_display}\n"
            f"📅 创建时间: {task.created_time}\n"
            f"✏️  最后更新: {task.updated_time}\n"
            f"✅ 完成时间: {task.completion_time}\n"
            f"━━━━━━━━━━━━━━"
        )
    
    @staticmethod
    def update_task(qq_number: int, task_id: int, **kwargs) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}

        update_fields = {}
        if 'content' in kwargs:
            update_fields['content'] = kwargs['content']
        if 'deadline' in kwargs:
            update_fields['deadline'] = kwargs['deadline']
        if 'department' in kwargs:
            update_fields['department'] = kwargs['department']
        
        if not update_fields:
            return {"success": False, "message": "没有提供可更新的字段"}
        
        success = task_database.update_task(
            task_id,
            content=update_fields.get('content'),
            deadline=update_fields.get('deadline'),
            department=update_fields.get('department')
        )
        
        if success:
            return {
                "success": True,
                "message": f"任务 #{task_id} 更新成功",
                "updated_fields": list(update_fields.keys())
            }
        else:
            return {"success": False, "message": f"任务 #{task_id} 更新失败"}
    
    @staticmethod
    def mark_response_received(qq_number: int, task_id: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        success = task_database.mark_response_received(task_id)
        if success:
            return {"success": True, "message": f"任务 #{task_id} 已标记为收到回复"}
        else:
            return {"success": False, "message": f"标记任务 #{task_id} 回复失败"}
    
    @staticmethod
    def complete_task(qq_number: int, task_id: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        success = task_database.complete_task(task_id)
        if success:
            return {
                "success": True,
                "message": f"任务 #{task_id} 已完结",
            }
        else:
            return {"success": False, "message": f"完结任务 #{task_id} 失败"}
    
    @staticmethod
    def delete_task(qq_number: int, task_id: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        success = task_database.delete_task(task_id)
        if success:
            return {"success": True, "message": f"任务 #{task_id} 已删除"}
        else:
            return {"success": False, "message": f"删除任务 #{task_id} 失败"}
    
    @staticmethod
    def get_statistics(qq_number: int) -> Dict[str, Any]:
        if not secretariat._check_permission(qq_number):
            return {"success": False, "message": "权限不足"}
        
        stats = task_database.get_statistics()
        return {
            "success": True,
            "statistics": stats
        }
    
    @staticmethod
    def is_valid_department(department_str: str) -> bool:
        if not isinstance(department_str, str):
            return False

        cleaned_str = department_str.strip()

        return cleaned_str in secretariat.DEPARTMENT_CONTACTS

    @staticmethod
    def get_department_list() -> list[str]:
        return list(secretariat.DEPARTMENT_CONTACTS.keys())
    
from astrbot.api import logger

import sqlite3
import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class Task:
    id: int
    content: str
    deadline: str
    department: str
    status: str  # 'pending'=未完成, 'completed'=已完成
    created_time: str
    updated_time: str
    completion_time: str
    response_received: bool

class task_database:
    db = sqlite3.connect('data/plugins/astrbot_plugin_mma_secretariat/database/task_database.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    @staticmethod
    def init_table():
        task_database.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            deadline TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_time TEXT NOT NULL,
            updated_time TEXT NOT NULL,
            completion_time TEXT,
            response_received BOOLEAN NOT NULL DEFAULT 0
        )
        ''')
        
        task_database.db.commit()

    @staticmethod
    def _get_current_time() -> str:
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def create_task(content: str, deadline: str, department: str) -> int:
        try:
            current_time = task_database._get_current_time()
            
            task_database.cursor.execute('''
            INSERT INTO tasks (content, deadline, department, status, created_time, updated_time, completion_time, response_received)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, 0)
            ''', (content, deadline, department, current_time, current_time, '未完结'))
            
            task_id = task_database.cursor.lastrowid
            
            task_database.db.commit()
            logger.info(f"成功创建任务 #{task_id} - {department}: {content[:50]}...")
            return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return None
    
    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row['id'],
            content=row['content'],
            deadline=row['deadline'],
            department=row['department'],
            status=row['status'],
            created_time=row['created_time'],
            updated_time=row['updated_time'],
            completion_time=row['completion_time'],
            response_received=bool(row['response_received'])
        )

    @staticmethod
    def get_all_tasks() -> list[Task]:
        try:
            task_database.cursor.execute('''
            SELECT * FROM tasks ORDER BY created_time DESC
            ''')
            rows = task_database.cursor.fetchall()
            return [task_database._row_to_task(row) for row in rows]
        except Exception as e:
            logger.error(f"获取所有任务失败: {e}")
            return []
    
    @staticmethod
    def get_pending_tasks() -> list[Task]:
        try:
            task_database.cursor.execute('''
            SELECT * FROM tasks WHERE status = 'pending' ORDER BY deadline ASC
            ''')
            rows = task_database.cursor.fetchall()
            return [task_database._row_to_task(row) for row in rows]
        except Exception as e:
            logger.error(f"获取未完成任务失败: {e}")
            return []

    @staticmethod
    def get_completed_tasks() -> list[Task]:
        try:
            task_database.cursor.execute('''
            SELECT * FROM tasks WHERE status = 'completed' ORDER BY completion_time DESC
            ''')
            rows = task_database.cursor.fetchall()
            return [task_database._row_to_task(row) for row in rows]
        except Exception as e:
            logger.error(f"获取已完成任务失败: {e}")
            return []

    @staticmethod
    def get_tasks_by_department(department: str) -> list[Task]:
        try:
            task_database.cursor.execute('''
            SELECT * FROM tasks WHERE department = ? ORDER BY deadline ASC
            ''', (department,))
            rows = task_database.cursor.fetchall()
            return [task_database._row_to_task(row) for row in rows]
        except Exception as e:
            logger.error(f"获取{department}部门任务失败: {e}")
            return []

    @staticmethod
    def get_task_by_id(task_id: int) -> Optional[Task]:
        try:
            task_database.cursor.execute('''
            SELECT * FROM tasks WHERE id = ?
            ''', (task_id,))
            row = task_database.cursor.fetchone()
            
            if row:
                return task_database._row_to_task(row)
            return None
        except Exception as e:
            logger.error(f"获取任务 #{task_id} 失败: {e}")
            return None

    @staticmethod
    def update_task(task_id: int, content: str = None, deadline: str = None, department: str = None) -> bool:
        try:
            task = task_database.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务 #{task_id} 不存在")
                return False
            
            current_time = task_database._get_current_time()
            updates = []
            params = []
            
            if content:
                updates.append("content = ?")
                params.append(content)
            
            if deadline:
                updates.append("deadline = ?")
                params.append(deadline)
            
            if department:
                updates.append("department = ?")
                params.append(department)
            
            if not updates:
                return True
                
            updates.append("updated_time = ?")
            params.append(current_time)
            params.append(task_id)
            
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            task_database.cursor.execute(query, params)
            
            task_database.db.commit()
            logger.info(f"成功更新任务 #{task_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务 #{task_id} 失败: {e}")
            return False
    
    @staticmethod
    def mark_response_received(task_id: int) -> bool:
        try:
            task = task_database.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务 #{task_id} 不存在")
                return False
            
            current_time = task_database._get_current_time()
            
            task_database.cursor.execute('''
            UPDATE tasks 
            SET response_received = 1, updated_time = ? 
            WHERE id = ?
            ''', (current_time, task_id))
            
            task_database.db.commit()
            logger.info(f"任务 #{task_id} 标记为已收到回复")
            return True
            
        except Exception as e:
            logger.error(f"标记任务回复失败: {e}")
            return False

    @staticmethod
    def complete_task(task_id: int) -> bool:
        try:
            task = task_database.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务 #{task_id} 不存在")
                return False
            
            if task.status == 'completed':
                logger.info(f"任务 #{task_id} 已经是完成状态")
                return True
            
            current_time = task_database._get_current_time()
            
            task_database.cursor.execute('''
            UPDATE tasks 
            SET status = 'completed', completion_time = ?, updated_time = ? 
            WHERE id = ?
            ''', (current_time, current_time, task_id))

            task_database.db.commit()
            logger.info(f"任务 #{task_id} 已完结")
            return True
            
        except Exception as e:
            logger.error(f"完结任务 #{task_id} 失败: {e}")
            return False

    @staticmethod
    def delete_task(task_id: int) -> bool:
        try:
            task = task_database.get_task_by_id(task_id)
            if not task:
                return False, f"任务 #{task_id} 不存在"

            task_database.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            
            deleted_rows = task_database.cursor.rowcount
            
            task_database.cursor.execute("COMMIT")
            
            if deleted_rows == 0:
                return False
            
            logger.info(f"已从数据库删除任务 #{task_id}")
            return True
            
        except Exception as e:
            task_database.cursor.execute("ROLLBACK")
            logger.error(f"删除任务 #{task_id} 失败: {e}")
            return False
    
    @staticmethod
    def get_statistics() -> dict:
        try:
            task_database.cursor.execute('SELECT COUNT(*) FROM tasks')
            total_tasks = task_database.cursor.fetchone()[0]
            
            task_database.cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "pending"')
            pending_tasks = task_database.cursor.fetchone()[0]
            
            task_database.cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
            completed_tasks = task_database.cursor.fetchone()[0]
            
            task_database.cursor.execute('''
            SELECT department, COUNT(*) as count 
            FROM tasks 
            GROUP BY department
            ''')
            dept_stats = {row['department']: row['count'] for row in task_database.cursor.fetchall()}
            
            return {
                'total': total_tasks,
                'pending': pending_tasks,
                'completed': completed_tasks,
                'by_department': dept_stats
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
# task_database.init_table()
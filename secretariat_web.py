from astrbot.api.event import MessageChain

import json
import re
from typing import Optional, Dict, Any
from aiohttp import web

from .secretariat import *
from .datetime_validator import *


class SecretariatWeb:
    def __init__(self, config: Dict[str, Any], context: Any = None):
        self.config = config
        self.context = context
        secretariat.NOTICE_GROUP_ID = config.get('notice_group_id', '')
        secretariat.SECRETARIAT_GROUP_ID = config.get('secretariat_group_id', '')
        for department in config.get('department_contacts', {}).keys():
            secretariat.DEPARTMENT_CONTACTS[department] = config['department_contacts'][department]

    async def handle_request(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({'success': False, 'message': 'Invalid JSON'}, status=400)

        messages = data.get('messages', '')
        user_id = data.get('user_id', '')

        if not messages:
            return web.json_response({'success': False, 'message': 'No messages provided'}, status=400)

        parts = messages.split()
        if not parts:
            return web.json_response({'success': False, 'message': 'Empty message'}, status=400)

        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        result = await self.route_command(command, args, user_id)

        return web.json_response(result)

    async def route_command(self, command: str, args: list, user_id: str) -> Dict[str, Any]:
        command_map = {
            'create_task': self.create_task,
            '创建任务': self.create_task,
            'send_task': self.send_task,
            '发送任务': self.send_task,
            'update_task': self.update_task,
            '更新任务': self.update_task,
            'delete_task': self.delete_task,
            '删除任务': self.delete_task,
            'complete_task': self.complete_task,
            '完结任务': self.complete_task,
            'mark_received': self.mark_received,
            '标记回复': self.mark_received,
            'receive_task': self.receive_task,
            '收到': self.receive_task,
            '1': self.receive_task_short,
            'receive_task_short': self.receive_task_short,
            'view_tasks': self.view_tasks,
            '查看任务': self.view_tasks,
            'task_detail': self.task_detail,
            '任务详情': self.task_detail,
            'task_stats': self.task_stats,
            '任务统计': self.task_stats,
            'set_notice_group': self.set_notice_group,
            '设置通知群聊': self.set_notice_group,
            'set_secretariat_group': self.set_secretariat_group,
            '设置秘书处群聊': self.set_secretariat_group,
            'set_department_contact': self.set_department_contact,
            '设置部门联系': self.set_department_contact,
            'departments': self.departments,
            '部门参数说明': self.departments,
            'time_arg': self.time_arg,
            '时间参数说明': self.time_arg,
            'help_secretariat': self.help_secretariat,
            '秘书处帮助': self.help_secretariat,
        }

        handler = command_map.get(command)
        if handler:
            return await handler(args, user_id)
        else:
            return {'success': False, 'message': f'Unknown command: {command}'}

    async def create_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 3:
            return {'success': False, 'message': '参数不足，需要: 内容 截止时间 部门'}

        content = args[0]
        deadline = args[1]
        department = args[2]

        is_valid, deadline = datetime_validator.validate_and_convert(deadline)
        if not is_valid:
            return {'success': False, 'message': '时间格式错误'}

        if not secretariat.is_valid_department(department):
            return {'success': False, 'message': '部门格式错误'}

        create_task_result = secretariat.create_task(user_id, content, deadline, department)
        if create_task_result['success']:
            task_id = create_task_result['task_id']
            get_task_by_id_result = secretariat.get_task_by_id(user_id, task_id)
            if get_task_by_id_result['success']:
                return {'success': True, 'message': f"创建任务成功\n{get_task_by_id_result['task']}"}
            else:
                return {'success': False, 'message': get_task_by_id_result['message']}
        else:
            return {'success': False, 'message': create_task_result['message']}

    async def send_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 2:
            return {'success': False, 'message': '参数不足，需要: 任务ID 任务类型(通知/更新/完结)'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        task_type = args[1]
        message_type = 'group'

        if task_type not in ['通知', '更新', '完结']:
            return {'success': False, 'message': '任务类型错误'}

        generate_send_info_result = secretariat._generate_send_info(user_id, task_id, message_type, task_type)
        if generate_send_info_result['success']:
            message_chain = MessageChain().at(qq=re.sub(r'\D', '', generate_send_info_result['at_id']), name="").message(f"\n{generate_send_info_result['content']}")
            if generate_send_info_result['message_type'] == 'group':
                await self.context.send_message(generate_send_info_result['group_id'], message_chain)
            else:
                await self.context.send_message(generate_send_info_result['at_id'], message_chain)
            return {'success': True, 'message': '任务已成功通知'}
        else:
            return {'success': False, 'message': generate_send_info_result['message']}

    async def update_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 4:
            return {'success': False, 'message': '参数不足，需要: 任务ID 内容 截止时间 部门，不想修改的字段用/占位'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        content = args[1]
        deadline = args[2]
        department = args[3]

        if content == '/' and deadline == '/' and department == '/':
            return {'success': False, 'message': '至少需要提供一个要更新的字段\n格式：/更新任务 <任务ID> <内容> <截止时间> <部门>\n不想修改的字段用/占位'}

        update_kwargs = {}

        if content != '/':
            update_kwargs['content'] = content

        if deadline != '/':
            is_valid, deadline = datetime_validator.validate_and_convert(deadline)
            if not is_valid:
                return {'success': False, 'message': '时间格式错误'}
            update_kwargs['deadline'] = deadline

        if department != '/':
            if not secretariat.is_valid_department(department):
                return {'success': False, 'message': '部门格式错误'}
            update_kwargs['department'] = department

        if not update_kwargs:
            return {'success': False, 'message': '没有提供要更新的字段\n不想修改的字段请用/占位，但不能三个都是/'}

        update_result = secretariat.update_task(user_id, task_id, **update_kwargs)

        if update_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                updated_fields = ', '.join(update_result.get('updated_fields', []))
                return {'success': True, 'message': f"任务更新成功！\n更新字段：{updated_fields}\n{task_result['task']}"}
            else:
                return {'success': False, 'message': f"更新成功，但获取任务详情失败: {task_result['message']}"}
        else:
            return {'success': False, 'message': f"更新失败: {update_result['message']}"}

    async def delete_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        task_result = secretariat.get_task_by_id(user_id, task_id)
        if not task_result['success']:
            return {'success': False, 'message': f"任务不存在或无法访问: {task_result['message']}"}

        delete_result = secretariat.delete_task(user_id, task_id)

        if delete_result['success']:
            return {'success': True, 'message': f"任务 #{task_id} 已成功删除"}
        else:
            return {'success': False, 'message': f"删除失败: {delete_result['message']}"}

    async def complete_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        complete_result = secretariat.complete_task(user_id, task_id)

        if complete_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                return {'success': True, 'message': f"任务已标记为完结！\n{task_result['task']}"}
            else:
                return {'success': False, 'message': f"完结成功，但获取任务详情失败: {task_result['message']}"}
        else:
            return {'success': False, 'message': f"完结失败: {complete_result['message']}"}

    async def mark_received(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        mark_result = secretariat.mark_response_received(user_id, task_id)

        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                return {'success': True, 'message': f"任务已标记为已收到回复！\n{task_result['task']}"}
            else:
                return {'success': False, 'message': f"标记成功，但获取任务详情失败: {task_result['message']}"}
        else:
            return {'success': False, 'message': f"标记失败: {mark_result['message']}"}

    async def receive_task(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        mark_result = secretariat.mark_response_received(user_id, task_id)

        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                message_chain = MessageChain().message(f"部门已收到回复！\n{task_result['task']}")
                await self.context.send_message(secretariat.SECRETARIAT_GROUP_ID, message_chain)
                return {'success': True, 'message': f"任务已标记为已收到回复！\n{task_result['task']}"}
            else:
                return {'success': False, 'message': f"标记成功，但获取任务详情失败: {task_result['message']}"}
        else:
            return {'success': False, 'message': f"标记失败: {mark_result['message']}"}

    async def receive_task_short(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        mark_result = secretariat.mark_response_received(user_id, task_id)

        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                message_chain = MessageChain().message(f"部门已收到回复！\n{task_result['task']}")
                await self.context.send_message(secretariat.SECRETARIAT_GROUP_ID, message_chain)
                return {'success': True, 'message': f"任务已标记为已收到回复！\n{task_result['task']}"}
            else:
                return {'success': False, 'message': f"标记成功，但获取任务详情失败: {task_result['message']}"}
        else:
            return {'success': False, 'message': f"标记失败: {mark_result['message']}"}

    async def view_tasks(self, args: list, user_id: str) -> Dict[str, Any]:
        task_type = args[0] if args else "全部"
        department = args[1] if len(args) > 1 else None

        try:
            task_id = int(task_type)
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                return {'success': True, 'message': f"📋 任务详情 (ID: {task_id})\n" + task_result['task']}
            else:
                return {'success': False, 'message': f"获取任务详情失败: {task_result['message']}"}
        except ValueError:
            pass

        task_type = task_type.lower()

        if task_type == "全部":
            tasks_result = secretariat.get_all_tasks(user_id)
            filter_type = "全部任务"
        elif task_type == "进行中":
            tasks_result = secretariat.get_pending_tasks(user_id)
            filter_type = "进行中任务"
        elif task_type == "已完成":
            tasks_result = secretariat.get_completed_tasks(user_id)
            filter_type = "已完成任务"
        elif task_type == "部门":
            if not department:
                return {'success': False, 'message': "请指定部门名称，格式：/查看任务 部门 <部门名>"}
            if not secretariat.is_valid_department(department):
                return {'success': False, 'message': f"部门格式错误，可用部门：{', '.join(secretariat.get_department_list())}"}
            tasks_result = secretariat.get_tasks_by_department(user_id, department)
            filter_type = f"{department}部门任务"
        else:
            help_text = (
                "📋 查看任务命令格式：\n"
                "━━━━━━━━━━━━━━\n"
                "• /查看任务 <任务ID> - 查看指定ID的任务详情\n"
                "• /查看任务 全部 - 查看所有任务\n"
                "• /查看任务 进行中 - 查看进行中的任务\n"
                "• /查看任务 已完成 - 查看已完成的任务\n"
                "• /查看任务 部门 <部门名> - 查看指定部门的任务\n"
                "━━━━━━━━━━━━━━\n"
                f"🏢 可用部门：{', '.join(secretariat.get_department_list())}\n"
                "━━━━━━━━━━━━━━"
            )
            return {'success': True, 'message': help_text}

        if tasks_result['success']:
            if tasks_result['count'] == 0:
                no_result_messages = {
                    "全部任务": "暂无任何任务记录",
                    "进行中任务": "暂无进行中的任务",
                    "已完成任务": "暂无已完成的任务",
                    f"{department}部门任务": f"暂无{department}部门的任务记录"
                }
                message = no_result_messages.get(filter_type, "没有找到符合条件的任务")
                return {'success': True, 'message': f"📋 {filter_type}\n━━━━━━━━━━━━━━\n{message}"}
            else:
                header = f"📋 任务列表 - {filter_type}\n"
                header += "━━━━━━━━━━━━━━\n"

                if task_type == "进行中":
                    header += "🔍 状态=进行中 🔄\n"
                elif task_type == "已完成":
                    header += "🔍 状态=已完成 ✅\n"
                elif task_type == "部门" and department:
                    header += f"🔍 部门={department} 🏢\n"
                else:
                    header += "🔍 全部任务\n"

                header += f"📊 数量：{tasks_result['count']} 个任务\n"

                header += "━━━━━━━━━━━━━━\n"

                full_message = header + tasks_result['tasks']

                return {'success': True, 'message': full_message}
        else:
            return {'success': False, 'message': f"📋 任务列表查询失败\n━━━━━━━━━━━━━━\n{tasks_result['message']}"}

    async def task_detail(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 1:
            return {'success': False, 'message': '参数不足，需要: 任务ID'}

        try:
            task_id = int(args[0])
        except ValueError:
            return {'success': False, 'message': '任务ID必须是数字'}

        task_result = secretariat.get_task_by_id(user_id, task_id)

        if task_result['success']:
            return {'success': True, 'message': task_result['task']}
        else:
            return {'success': False, 'message': f"获取任务详情失败: {task_result['message']}"}

    async def task_stats(self, args: list, user_id: str) -> Dict[str, Any]:
        stats_result = secretariat.get_statistics(user_id)

        if stats_result['success']:
            stats = stats_result['statistics']

            stats_message = (
                "📊 任务统计报表\n"
                "━━━━━━━━━━━━━━\n"
                f"📋 总任务数: {stats['total']}\n"
                f"🔄 进行中: {stats['pending']}\n"
                f"✅ 已完成: {stats['completed']}\n"
                f"📈 完成率: {stats['completed']/stats['total']*100:.1f}% （{stats['completed']}/{stats['total']}）\n"
                "━━━━━━━━━━━━━━\n"
                "🏢 部门任务分布:\n"
            )

            for dept, count in stats['by_department'].items():
                stats_message += f"  • {dept}: {count} 个\n"

            stats_message += "━━━━━━━━━━━━━━"

            return {'success': True, 'message': stats_message}
        else:
            return {'success': False, 'message': f"获取统计信息失败: {stats_result['message']}"}

    async def set_notice_group(self, args: list, user_id: str) -> Dict[str, Any]:
        if not secretariat._check_root_permission(user_id):
            return {'success': False, 'message': '权限不足，需要最高权限'}

        self.config['notice_group_id'] = args[0] if args else ''
        secretariat.NOTICE_GROUP_ID = self.config['notice_group_id']
        return {'success': True, 'message': '通知群聊 设置成功✅'}

    async def set_secretariat_group(self, args: list, user_id: str) -> Dict[str, Any]:
        if not secretariat._check_root_permission(user_id):
            return {'success': False, 'message': '权限不足，需要最高权限'}

        self.config['secretariat_group_id'] = args[0] if args else ''
        secretariat.SECRETARIAT_GROUP_ID = self.config['secretariat_group_id']
        return {'success': True, 'message': '秘书处群聊 设置成功✅'}

    async def set_department_contact(self, args: list, user_id: str) -> Dict[str, Any]:
        if len(args) < 2:
            return {'success': False, 'message': '参数不足，需要: 部门 群号/QQ号'}

        if not secretariat._check_root_permission(user_id):
            return {'success': False, 'message': '权限不足，需要最高权限'}

        department = args[0]
        contact_id = args[1]

        if not secretariat.is_valid_department(department):
            return {'success': False, 'message': '部门名称无效，可用部门'}

        self.config['department_contacts'][department] = contact_id

        secretariat.DEPARTMENT_CONTACTS[department] = self.config['department_contacts'][department]

        return {'success': True, 'message': f'{department}联系 设置成功✅'}

    async def departments(self, args: list, user_id: str) -> Dict[str, Any]:
        if not secretariat._check_permission(user_id):
            return {'success': False, 'message': '部门参数说明查询失败：权限不足'}

        dept_list = secretariat.get_department_list()

        if dept_list:
            help_message = (
                "🏢 部门格式说明\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📝 使用提示：\n"
                "• 部门参数必须是完整名称，不能缩写\n"
                "• 例如：必须写「技术部」，不能只写「技术」\n"
                "• 必须写「组织部」，不能只写「组织」\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📋 完整的部门列表：\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "1. 秘书部\n"
            )

            for i, dept in enumerate(dept_list, 2):
                help_message += f"{i}. {dept}\n"

            help_message += (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 使用示例：\n"
                "• /创建任务 完成活动策划 2026-12-31T23:59:00 组织部 ✅\n"
                "• /创建任务 完成活动策划 2026-12-31T23:59:00 组织 ❌\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )

            return {'success': True, 'message': help_message}
        else:
            return {'success': True, 'message': '暂无部门信息'}

    async def time_arg(self, args: list, user_id: str) -> Dict[str, Any]:
        if not secretariat._check_permission(user_id):
            return {'success': False, 'message': '时间参数说明查询失败：权限不足'}

        return {'success': True, 'message': datetime_validator.get_formats_examples()}

    async def help_secretariat(self, args: list, user_id: str) -> Dict[str, Any]:
        if not secretariat._check_permission(user_id):
            return {'success': False, 'message': '秘书处帮助查询失败：权限不足'}

        help_message = (
            "🤖 数学建模协会秘书处机器人 - 命令速查\n"
            "━━━━━━━━━━━━━━\n"

            "悄悄告诉你，私聊的话可以不用加/斜杠开头哦\n\n"

            "📋 核心命令:\n"
            "• /创建任务 <内容> <截止时间> <部门>\n"
            "• /发送任务 <ID> <通知/更新/完结>\n"
            "• /更新任务 <ID> <内容> <截止时间> <部门> - 不需要更改的参数使用/占位\n"
            "• /完结任务 <ID>\n"
            "• /删除任务 <ID>\n"
            "• /标记回复 <ID>\n\n"

            "📝 部门回复:\n"
            "• /收到 <ID> 或 /1 <ID>\n\n"

            "👁️ 查看任务:\n"
            "• /查看任务 <ID> - 查看单个任务\n"
            "• /查看任务 全部 - 所有任务\n"
            "• /查看任务 进行中 - 进行中任务\n"
            "• /查看任务 已完成 - 已完成任务\n"
            "• /查看任务 部门 <部门> - 部门任务\n"
            "• /任务详情 <ID> - 详细信息\n"
            "• /任务统计 - 统计数据\n\n"

            "🔧 系统设置 (仅最高权限) :\n"
            "• /设置通知群聊 - 设置任务通知发送的群聊\n"
            "• /设置秘书处群聊 - 设置秘书处内部群聊\n"
            "• /设置部门联系 <部门> - 设置部门联系（私聊形式）\n\n"

            "🏢 其他命令:\n"
            "• /部门参数说明 - 查看部门参数使用说明\n"
            "• /时间参数说明 - 查看时间参数使用说明\n"
            "• /秘书处帮助 - 显示此帮助\n\n"

            "📅 时间格式示例:\n"
            "• 2024-12-31T23:59:00\n"

            "🏢 可用部门:\n"
            f"秘书处，{', '.join(secretariat.get_department_list())}\n\n"

            "💡 使用示例:\n"
            "• /创建任务 完成活动策划 2026-12-31T23:59:00 组织部\n"
            "• /发送任务 1 通知\n"
            "• /查看任务 进行中\n"
            "• /收到 1 (部门确认)\n"
            "━━━━━━━━━━━━━━"
        )

        return {'success': True, 'message': help_message}


async def create_app(config: Dict[str, Any]) -> web.Application:
    secretariat_web = SecretariatWeb(config)
    app = web.Application()
    app.router.add_post('/webhook', secretariat_web.handle_request)
    return app

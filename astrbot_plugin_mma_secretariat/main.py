from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

import re

from .secretariat import *
from .datetime_validator import *

@register("astrbot_plugin_mma_secretariat", "dreamDust", "数学建模协会小数秘书处模块", "1.0.0")
class MMASecretariatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        secretariat.NOTICE_GROUP_ID = self.config['notice_group_id']
        secretariat.SECRETARIAT_GROUP_ID = self.config['secretariat_group_id']
        for department in self.config['department_contacts'].keys():
            secretariat.DEPARTMENT_CONTACTS[department] = self.config['department_contacts'][department]

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.command("create_task", alias={'创建任务'}, priority=1)
    async def create_task(self, event: AstrMessageEvent, content: str, deadline: str, department: str):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        is_valid, deadline = datetime_validator.validate_and_convert(deadline)
        if not is_valid:
            yield event.plain_result("时间格式错误")
            return
        if not secretariat.is_valid_department(department):
            yield event.plain_result("部门格式错误")
            return
        create_task_result = secretariat.create_task(user_id, content, deadline, department)
        if create_task_result['success']:
            task_id = create_task_result['task_id']
            get_task_by_id_result = secretariat.get_task_by_id(user_id, task_id)
            if get_task_by_id_result['success']:
                yield event.plain_result(f"创建任务成功\n{get_task_by_id_result['task']}")
            else:
                yield event.plain_result(f"{get_task_by_id_result['message']}")
        else:
            yield event.plain_result(f"{create_task_result['message']}")

    @filter.command("send_task", alias={'发送任务'}, priority=1)
    async def send_task(self, event: AstrMessageEvent, task_id: int, task_type: str):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        message_type = 'group'
        if task_type not in ['通知','更新','完结']:
            yield event.plain_result("任务类型错误")
            return
        generate_send_info_result = secretariat._generate_send_info(user_id, task_id, message_type, task_type)
        if generate_send_info_result['success']:
            message_chain = MessageChain().at(qq=re.sub(r'\D', '', generate_send_info_result['at_id']),name="").message(f"\n{generate_send_info_result['content']}")
            if generate_send_info_result['message_type'] == 'group':
                await self.context.send_message(generate_send_info_result['group_id'], message_chain)
            else:
                await self.context.send_message(generate_send_info_result['at_id'], message_chain)
            yield event.plain_result("任务已成功通知")
        else:
            yield event.plain_result(f"{generate_send_info_result['message']}")


    @filter.command("update_task", alias={'更新任务'}, priority=1)
    async def update_task(self, event: AstrMessageEvent, task_id: int, content: str, deadline: str, department: str):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if content == '/' and deadline == '/' and department == '/':
            yield event.plain_result("至少需要提供一个要更新的字段\n格式：/更新任务 <任务ID> <内容> <截止时间> <部门>\n不想修改的字段用/占位")
            return
        
        update_kwargs = {}

        if content != '/':
            update_kwargs['content'] = content

        if deadline != '/':
            is_valid, deadline = datetime_validator.validate_and_convert(deadline)
            if not is_valid:
                yield event.plain_result("时间格式错误")
                return
            update_kwargs['deadline'] = deadline
        
        if department != '/':
            if not secretariat.is_valid_department(department):
                yield event.plain_result("部门格式错误")
                return
            update_kwargs['department'] = department
        
        if not update_kwargs:
            yield event.plain_result("没有提供要更新的字段\n不想修改的字段请用/占位，但不能三个都是/")
            return
        
        update_result = secretariat.update_task(user_id, task_id, **update_kwargs)
        
        if update_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                updated_fields = ', '.join(update_result.get('updated_fields', []))
                yield event.plain_result(f"任务更新成功！\n更新字段：{updated_fields}\n{task_result['task']}")
            else:
                yield event.plain_result(f"更新成功，但获取任务详情失败: {task_result['message']}")
        else:
            yield event.plain_result(f"更新失败: {update_result['message']}")

    @filter.command("delete_task", alias={'删除任务'}, priority=1)
    async def delete_task(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        task_result = secretariat.get_task_by_id(user_id, task_id)
        if not task_result['success']:
            yield event.plain_result(f"任务不存在或无法访问: {task_result['message']}")
            return

        delete_result = secretariat.delete_task(user_id, task_id)
        
        if delete_result['success']:
            yield event.plain_result(f"任务 #{task_id} 已成功删除")
        else:
            yield event.plain_result(f"删除失败: {delete_result['message']}")

    @filter.command("complete_task", alias={'完结任务'}, priority=1)
    async def complete_task(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        complete_result = secretariat.complete_task(user_id, task_id)
        
        if complete_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                yield event.plain_result(f"任务已标记为完结！\n{task_result['task']}")
            else:
                yield event.plain_result(f"完结成功，但获取任务详情失败: {task_result['message']}")
        else:
            yield event.plain_result(f"完结失败: {complete_result['message']}")

    @filter.command("mark_received", alias={'标记回复'}, priority=1)
    async def mark_received(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        mark_result = secretariat.mark_response_received(user_id, task_id)
        
        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                yield event.plain_result(f"任务已标记为已收到回复！\n{task_result['task']}")
            else:
                yield event.plain_result(f"标记成功，但获取任务详情失败: {task_result['message']}")
        else:
            yield event.plain_result(f"标记失败: {mark_result['message']}")

    @filter.command("receive_task", alias={'收到'}, priority=1)
    async def receive_task(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        mark_result = secretariat.mark_response_received(user_id, task_id)
        
        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                yield event.plain_result(f"任务已标记为已收到回复！\n{task_result['task']}")
                message_chain = MessageChain().message(f"部门已收到回复！\n{task_result['task']}")
                await self.context.send_message(secretariat.SECRETARIAT_GROUP_ID, message_chain)
            else:
                yield event.plain_result(f"标记成功，但获取任务详情失败: {task_result['message']}")
        else:
            yield event.plain_result(f"标记失败: {mark_result['message']}")
    
    @filter.command("receive_task_short", alias={'1'}, priority=1)
    async def receive_task_short(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        mark_result = secretariat.mark_response_received(user_id, task_id)
        
        if mark_result['success']:
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                yield event.plain_result(f"任务已标记为已收到回复！\n{task_result['task']}")
                message_chain = MessageChain().message(f"部门已收到回复！\n{task_result['task']}")
                await self.context.send_message(secretariat.SECRETARIAT_GROUP_ID, message_chain)
            else:
                yield event.plain_result(f"标记成功，但获取任务详情失败: {task_result['message']}")
        else:
            yield event.plain_result(f"标记失败: {mark_result['message']}")

    @filter.command("view_tasks", alias={'查看任务'}, priority=1)
    async def view_tasks(self, event: AstrMessageEvent, task_type: str = "全部", department: str = None):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        try:
            task_id = int(task_type)
            task_result = secretariat.get_task_by_id(user_id, task_id)
            if task_result['success']:
                yield event.plain_result(f"📋 任务详情 (ID: {task_id})\n" + task_result['task'])
            else:
                yield event.plain_result(f"获取任务详情失败: {task_result['message']}")
            return
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
                yield event.plain_result("请指定部门名称，格式：/查看任务 部门 <部门名>")
                return
            if not secretariat.is_valid_department(department):
                yield event.plain_result(f"部门格式错误，可用部门：{', '.join(secretariat.get_department_list())}")
                return
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
            yield event.plain_result(help_text)
            return
        
        if tasks_result['success']:
            if tasks_result['count'] == 0:
                no_result_messages = {
                    "全部任务": "暂无任何任务记录",
                    "进行中任务": "暂无进行中的任务",
                    "已完成任务": "暂无已完成的任务",
                    f"{department}部门任务": f"暂无{department}部门的任务记录"
                }
                message = no_result_messages.get(filter_type, "没有找到符合条件的任务")
                yield event.plain_result(f"📋 {filter_type}\n━━━━━━━━━━━━━━\n{message}")
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
                
                yield event.plain_result(full_message)
        else:
            yield event.plain_result(f"📋 任务列表查询失败\n━━━━━━━━━━━━━━\n{tasks_result['message']}")

    @filter.command("task_detail", alias={'任务详情'}, priority=1)
    async def task_detail(self, event: AstrMessageEvent, task_id: int):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
        task_result = secretariat.get_task_by_id(user_id, task_id)
        
        if task_result['success']:
            yield event.plain_result(task_result['task'])
        else:
            yield event.plain_result(f"获取任务详情失败: {task_result['message']}")

    @filter.command("task_stats", alias={'任务统计'}, priority=1)
    async def task_stats(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id
        
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
            
            yield event.plain_result(stats_message)
        else:
            yield event.plain_result(f"获取统计信息失败: {stats_result['message']}")

    @filter.command("set_notice_group", alias={'设置通知群聊'}, priority=1)
    async def set_notice_group(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_root_permission(user_id):
            yield event.plain_result('权限不足，需要最高权限')
            return

        self.config['notice_group_id'] = event.unified_msg_origin
        self.config.save_config()
        secretariat.NOTICE_GROUP_ID = self.config['notice_group_id']
        yield event.plain_result('通知群聊 设置成功✅')

    @filter.command("set_secretariat_group", alias={'设置秘书处群聊'}, priority=1)
    async def set_secretariat_group(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_root_permission(user_id):
            yield event.plain_result('权限不足，需要最高权限')
            return

        self.config['secretariat_group_id'] = event.unified_msg_origin
        self.config.save_config()
        secretariat.SECRETARIAT_GROUP_ID = self.config['secretariat_group_id']
        yield event.plain_result('秘书处群聊 设置成功✅')

    @filter.command("set_department_contact", alias={'设置部门联系'}, priority=1)
    async def set_department_contact(self, event: AstrMessageEvent, department: str):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_root_permission(user_id):
            yield event.plain_result('权限不足，需要最高权限')
            return

        if not secretariat.is_valid_department(department):
            yield event.plain_result('部门名称无效，可用部门')
            return
        
        self.config['department_contacts'][department] = event.unified_msg_origin
        self.config.save_config()

        secretariat.DEPARTMENT_CONTACTS[department] = self.config['department_contacts'][department]
        
        yield event.plain_result(f'{department}联系 设置成功✅')

    @filter.command("departments", alias={'部门参数说明'}, priority=1)
    async def departments(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_permission(user_id):
            yield event.plain_result('部门参数说明查询失败：权限不足')
            return

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
            
            yield event.plain_result(help_message)
        else:
            yield event.plain_result("暂无部门信息")

    @filter.command("time_arg", alias={'时间参数说明'}, priority=1)
    async def time_arg(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_permission(user_id):
            yield event.plain_result('时间参数说明查询失败：权限不足')
            return
        
        yield event.plain_result(datetime_validator.get_formats_examples())
    
    @filter.command("help_secretariat", alias={'秘书处帮助'}, priority=1)
    async def help_secretariat(self, event: AstrMessageEvent):
        raw_message = event.message_obj.raw_message
        user_id = raw_message.user_id

        if not secretariat._check_permission(user_id):
            yield event.plain_result('秘书处帮助查询失败：权限不足')
            return

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
        
        yield event.plain_result(help_message)
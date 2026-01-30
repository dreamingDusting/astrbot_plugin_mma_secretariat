import datetime
from typing import Optional, Tuple

class datetime_validator:
    STANDARD_FORMAT = "%Y-%m-%dT%H:%M:%S"
    
    SUPPORTED_FORMATS = [
        "%Y-%m-%dT%H:%M:%S",        # 标准格式
        "%Y-%m-%dT%H:%M",           # 不带秒
        "%Y/%m/%dT%H:%M:%S",        # 斜杠日期+T+时间
        "%Y年%m月%d日T%H:%M:%S",    # 中文日期+T+时间
        "%Y.%m.%dT%H:%M:%S",        # 点日期+T+时间
        "%m-%dT%H:%M",              # 月日+T+时间（不带秒）
        "%m/%dT%H:%M:%S",           # 月日斜杠+T+时间
        "%m月%d日T%H:%M:%S",        # 月日中文+T+时间
        "%m.%dT%H:%M:%S",           # 月日点+T+时间
        
        # 只有日期的格式（默认时间23:59:00）
        "%Y-%m-%d",                 # 标准日期
        "%Y/%m/%d",                 # 斜杠日期
        "%Y年%m月%d日",             # 中文日期
        "%Y.%m.%d",                 # 点日期
        "%m-%d",                    # 月日
        "%m/%d",                    # 月日斜杠
        "%m月%d日",                 # 月日中文
        "%m.%d",                    # 月日点
    ]
    
    DEFAULT_TIME = "23:59:00"  # 默认时间
    
    @staticmethod
    def validate_and_convert(date_time_str: str) -> Tuple[bool, Optional[str]]:
        if not isinstance(date_time_str, str):
            return False, None
        
        cleaned_str = date_time_str.strip().replace('：', ':')
        
        if not cleaned_str:
            return False, None
        
        try:
            dt = datetime.datetime.strptime(cleaned_str, datetime_validator.STANDARD_FORMAT)
            return True, cleaned_str
        except ValueError:
            pass
        
        parsed_datetime = None
        used_format = None
        
        for fmt in datetime_validator.SUPPORTED_FORMATS:
            try:
                dt = datetime.datetime.strptime(cleaned_str, fmt)
                parsed_datetime = dt
                used_format = fmt
                break
            except ValueError:
                continue
        
        if parsed_datetime is None:
            return False, None

        if used_format and "%Y" not in used_format:
            current_year = datetime.datetime.now().year
            
            try:
                month = parsed_datetime.month
                day = parsed_datetime.day
                
                if any(time_char in fmt for time_char in ['%H', '%M', '%S']):
                    hour = parsed_datetime.hour
                    minute = parsed_datetime.minute
                    second = getattr(parsed_datetime, 'second', 0)
                else:
                    hour = 23
                    minute = 59
                    second = 0
                
                parsed_datetime = datetime.datetime(
                    current_year, month, day, hour, minute, second
                )
            except ValueError as e:
                return False, None

        if used_format and not any(time_char in fmt for time_char in ['%H', '%M', '%S']):
            try:
                default_time = datetime.datetime.strptime(datetime_validator.DEFAULT_TIME, "%H:%M:%S")
                parsed_datetime = parsed_datetime.replace(
                    hour=default_time.hour,
                    minute=default_time.minute,
                    second=default_time.second
                )
            except ValueError:
                pass
        
        standard_str = parsed_datetime.strftime(datetime_validator.STANDARD_FORMAT)
        
        return True, standard_str
    
    @staticmethod
    def is_valid_datetime(date_time_str: str) -> bool:
        is_valid, _ = datetime_validator.validate_and_convert(date_time_str)
        return is_valid
    
    @staticmethod
    def get_formats_examples() -> str:
        examples = []
        now = datetime.datetime.now()

        time_formats_with_names = [
            ("%Y-%m-%dT%H:%M:%S", "标准ISO格式（推荐）"),
            ("%Y-%m-%dT%H:%M", "ISO格式（不带秒）"),
            ("%Y/%m/%dT%H:%M:%S", "斜杠日期+T+时间"),
            ("%Y年%m月%d日T%H:%M:%S", "中文日期+T+时间"),
            ("%Y.%m.%dT%H:%M:%S", "点日期+T+时间"),
            ("%m-%dT%H:%M", "月日+T+时间（不带秒）"),
            ("%m/%dT%H:%M:%S", "月日斜杠+T+时间"),
            ("%m月%d日T%H:%M:%S", "月日中文+T+时间"),
            ("%m.%dT%H:%M:%S", "月日点+T+时间"),
        ]
        
        date_only_formats_with_names = [
            ("%Y-%m-%d", "标准日期（默认23:59:00）"),
            ("%Y/%m/%d", "斜杠日期（默认23:59:00）"),
            ("%Y年%m月%d日", "中文日期（默认23:59:00）"),
            ("%Y.%m.%d", "点日期（默认23:59:00）"),
            ("%m-%d", "月日（默认23:59:00）"),
            ("%m/%d", "月日斜杠（默认23:59:00）"),
            ("%m月%d日", "月日中文（默认23:59:00）"),
            ("%m.%d", "月日点（默认23:59:00）"),
        ]
        
        examples.append("⏰ 带时间的格式：")
        for fmt, name in time_formats_with_names:
            try:
                example = now.strftime(fmt)
                examples.append(f"  • {name}: {example}")
            except:
                examples.append(f"  • {name}: [格式无效]")
        
        examples.append("\n📅 只有日期的格式（自动添加23:59:00）：")
        for fmt, name in date_only_formats_with_names:
            try:
                example = now.strftime(fmt)
                examples.append(f"  • {name}: {example}")
            except:
                examples.append(f"  • {name}: [格式无效]")
        
        explanation = [
            "\n📋 使用说明：",
            "━━━━━━━━━━━━━━━━━━━━",
            "1. 使用大写字母 T 连接日期和时间",
            "2. 日期和时间之间不能有空格",
            "3. 如果只提供日期，默认时间为 23:59:00",
            "4. 推荐格式：2026-02-12T15:10:11",
            "5. 如果只有月日（如02-12），会自动添加当前年份",
            "6. 支持中文冒号（：）和英文冒号（:）\n",
        ]
        
        return "\n".join(explanation + examples)
    
    @staticmethod
    def convert_to_display_format(iso_datetime_str: str) -> str:
        try:
            dt = datetime.datetime.strptime(iso_datetime_str, datetime_validator.STANDARD_FORMAT)
            return dt.strftime("%Y年%m月%d日 %H:%M:%S")
        except ValueError:
            return iso_datetime_str

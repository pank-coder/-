import json

from sqlalchemy import select

from db.database import session
from db.models import News, Event
from services.schedule import get_schedule
from services.teachers import get_teacher
from services.students import get_student_class

TOOLS = [
    {"type": "function", "function": {"name": "get_schedule", "description": "Расписание уроков класса на день недели", "parameters": {"type": "object", "properties": {"class_name": {"type": "string", "description": "Название класса, например 9А"}, "weekday": {"type": "integer", "description": "День недели 1-6 (1 - понедельник)"}, "week_type": {"type": "string", "enum": ["odd", "even", "both"], "description": "Четная/нечетная неделя"}}, "required": ["class_name", "weekday"]}}},
    {"type": "function", "function": {"name": "get_teacher_info", "description": "Информация об учителе по ФИО или предмету", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Часть ФИО или название предмета"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_student_class", "description": "Класс ученика по его имени или username", "parameters": {"type": "object", "properties": {"student_name": {"type": "string"}}, "required": ["student_name"]}}},
    {"type": "function", "function": {"name": "get_news", "description": "Последние новости гимназии", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 5}}, "required": []}}},
    {"type": "function", "function": {"name": "get_events", "description": "Мероприятия гимназии в диапазоне дат", "parameters": {"type": "object", "properties": {"date_from": {"type": "string", "description": "Начало диапазона, формат ГГГГ-ММ-ДД"}, "date_to": {"type": "string", "description": "Конец диапазона, формат ГГГГ-ММ-ДД"}}, "required": ["date_from", "date_to"]}}},
]


async def get_news(limit=5):
    async with session() as s:
        r = await s.execute(select(News).order_by(News.published_at.desc()).limit(int(limit)))
        o = []
        for x in r.scalars().all():
            o.append({"title": x.title, "body": x.body, "published_at": str(x.published_at)})
        return o


async def get_events(date_from, date_to):
    async with session() as s:
        r = await s.execute(select(Event).where(Event.event_date >= str(date_from), Event.event_date <= str(date_to)).order_by(Event.event_date))
        o = []
        for x in r.scalars().all():
            o.append({"title": x.title, "date": x.event_date, "description": x.description})
        return o


async def call_tool(n, a):
    if n == "get_schedule":
        r = await get_schedule(a.get("class_name"), a.get("weekday"), a.get("week_type", "both"))
    elif n == "get_teacher_info":
        r = await get_teacher(a.get("query"))
    elif n == "get_student_class":
        r = await get_student_class(a.get("student_name"))
    elif n == "get_news":
        r = await get_news(a.get("limit", 5))
    elif n == "get_events":
        r = await get_events(a.get("date_from"), a.get("date_to"))
    else:
        r = {"error": "Unknown tool"}
    return json.dumps(r, ensure_ascii=False)

import asyncio

from sqlalchemy import select, func

from auth import hash_pw
from db.database import init_db, session
from db.models import User, Cls, Teacher, Subject, Lesson, News, Event


async def seed():
    async with session() as s:
        n = await s.scalar(select(func.count()).select_from(Cls))
        if n:
            print("seed skipped")
            return
        c1 = Cls(name="5А", level="primary")
        c2 = Cls(name="9А", level="middle")
        c3 = Cls(name="11Ф", level="high")
        s.add_all([c1, c2, c3])
        await s.flush()

        u1 = User(username="ivanova", hashed_password=hash_pw("teacher123"), role="teacher")
        u2 = User(username="petrov", hashed_password=hash_pw("teacher123"), role="teacher")
        u3 = User(username="sidorova", hashed_password=hash_pw("teacher123"), role="teacher")
        u4 = User(username="kuznecov", hashed_password=hash_pw("teacher123"), role="teacher")
        u5 = User(username="orlova", hashed_password=hash_pw("teacher123"), role="teacher")
        u6 = User(username="admin", hashed_password=hash_pw("admin123"), role="admin")
        s.add_all([u1, u2, u3, u4, u5, u6])
        await s.flush()

        t1 = Teacher(user_id=u1.id, full_name="Иванова Мария Ивановна", subjects=["математика"], cabinet="301", email="ivanova@univers-24.ru")
        t2 = Teacher(user_id=u2.id, full_name="Петров Алексей Викторович", subjects=["физика", "астрономия"], cabinet="215", email="petrov@univers-24.ru")
        t3 = Teacher(user_id=u3.id, full_name="Сидорова Елена Петровна", subjects=["русский язык", "литература"], cabinet="108", email="sidorova@univers-24.ru")
        t4 = Teacher(user_id=u4.id, full_name="Кузнецов Дмитрий Сергеевич", subjects=["история", "обществознание"], cabinet="204", email="kuznecov@univers-24.ru")
        t5 = Teacher(user_id=u5.id, full_name="Орлова Анна Николаевна", subjects=["английский язык"], cabinet="412", email="orlova@univers-24.ru")
        s.add_all([t1, t2, t3, t4, t5])
        await s.flush()

        subs = ["математика", "физика", "русский язык", "литература", "история", "английский язык", "информатика", "география", "химия", "биология", "обществознание"]
        sm = {}
        for x in subs:
            r = Subject(name=x)
            s.add(r)
            sm[x] = r
        await s.flush()

        rows = [
            (2, "математика", 1, 1, 1, "301", "both"),
            (2, "русский язык", 3, 2, 1, "108", "both"),
            (2, "английский язык", 5, 3, 1, "412", "both"),
            (2, "физика", 2, 4, 1, "215", "both"),
            (2, "история", 4, 5, 1, "204", "both"),
            (2, "информатика", 1, 6, 1, "305", "odd"),
            (2, "химия", 1, 7, 1, "210", "even"),
            (2, "математика", 1, 1, 2, "301", "both"),
            (2, "физика", 2, 2, 2, "215", "both"),
            (2, "литература", 3, 3, 2, "108", "both"),
            (2, "география", 4, 4, 2, "204", "both"),
            (2, "английский язык", 5, 5, 2, "412", "both"),
            (2, "биология", 1, 6, 2, "209", "both"),
            (2, "математика", 1, 1, 3, "301", "both"),
            (2, "история", 4, 2, 3, "204", "both"),
            (2, "русский язык", 3, 3, 3, "108", "both"),
            (2, "физика", 2, 4, 3, "215", "both"),
            (2, "информатика", 1, 5, 3, "305", "both"),
            (2, "английский язык", 5, 1, 4, "412", "both"),
            (2, "математика", 1, 2, 4, "301", "both"),
            (2, "литература", 3, 3, 4, "108", "both"),
            (2, "химия", 1, 4, 4, "210", "odd"),
            (2, "обществознание", 4, 5, 4, "204", "even"),

            (2, "физика", 2, 1, 5, "215", "both"),
            (2, "русский язык", 3, 2, 5, "108", "both"),
            (2, "география", 4, 3, 5, "204", "both"),
            (2, "биология", 1, 4, 5, "209", "both"),
            (2, "история", 4, 5, 5, "204", "both"),
        ]
        for a, b, t, w, l, cab, wt in rows:
            s.add(Lesson(class_id=a, subject_id=sm[b].id, teacher_id=t, weekday=w, lesson_number=l, cabinet=cab, week_type=wt))

        s.add(News(title="День открытых дверей", body="Приглашаем будущих учеников гимназии «Универс» на день открытых дверей."))
        s.add(News(title="Победа на олимпиаде", body="Ученики 9А класса заняли призовое место на городской олимпиаде по математике."))
        s.add(Event(title="Новогодний концерт", event_date="2026-12-25", description="Актовый зал, начало в 12:00"))
        s.add(Event(title="Шахматный турнир", event_date="2026-12-10", description="Кабинет 101, регистрация у классного руководителя"))
        await s.commit()
        print("seed done")


if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(seed())

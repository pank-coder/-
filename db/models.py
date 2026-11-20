
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)


class Cls(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    level = Column(String, default="high")


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String, nullable=False)
    subjects = Column(JSON, default=list)
    cabinet = Column(String, nullable=True)
    email = Column(String, nullable=True)


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class Lesson(Base):
    __tablename__ = "schedule"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    weekday = Column(Integer)
    lesson_number = Column(Integer)
    cabinet = Column(String, nullable=True)
    week_type = Column(String, default="both")


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    body = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    event_date = Column(String)
    description = Column(Text, nullable=True)


class Msg(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

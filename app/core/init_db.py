from sqlmodel import SQLModel
from app.core.database import engine

# Import all models
from app.models.user import User
from app.models.teacher import Teacher
from app.models.schedule import Schedule
from app.models.course import Course  
from app.models.enrollment import Enrollment 
from app.models.lecture import Lecture
from app.models.resource import Resource


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    create_db_and_tables()
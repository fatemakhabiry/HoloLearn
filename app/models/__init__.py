from app.models.lecture import Lecture
from app.models.resource import Resource
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.schedule import Schedule
from app.models.agent_session import AgentSession
from app.models.lecture_version import LectureVersion
from app.models.generated_content import GeneratedContent
from app.models.user import User, OTPVerification
from app.models.lecture_index import LectureIndex    # ← ADD
from app.models.qa_session import QASession          # ← ADD
from app.models.qa_message import QAMessage          # ← ADD
from app.models.identity_verification import IdentityVerification
from app.models.qa_export import QAExport
# app/models/__init__.py
from app.models.lecture_pipeline import LecturePipeline   # ← may be missing
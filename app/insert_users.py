from passlib.context import CryptContext
from sqlalchemy import create_engine, text

# --------------------
# Database connection
# --------------------
DATABASE_URL = "postgresql+psycopg2://postgres:fatma_1234@localhost:5432/holo_db"

engine = create_engine(DATABASE_URL)

# --------------------
# Password hashing
# --------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# --------------------
# Insert teacher
# --------------------
def insert_teacher(email: str, full_name: str, password: str):
    hashed_password = hash_password(password)

    query = text("""
        INSERT INTO users (email, full_name, role, hashed_password)
        VALUES (:email, :full_name, 'TEACHER', :hashed_password)
    """)

    with engine.begin() as conn:
        conn.execute(
            query,
            {
                "email": email,
                "full_name": full_name,
                "hashed_password": hashed_password
            }
        )

    print("✅ Teacher inserted successfully")

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    insert_teacher(
        email="teacher2@hololearn.com",
        full_name="Mohamed Ali",
        password="teacher123"
    )
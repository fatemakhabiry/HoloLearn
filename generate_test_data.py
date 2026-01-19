from passlib.context import CryptContext
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define accounts with unique passwords
accounts = [
    ("student@test.com", "Ahmed Student", "student", "Student@123"),
    ("student2@test.com", "Sara Ahmed", "student", "Sara@2024"),
    ("mohamed@test.com", "Mohamed Ali", "student", "Mohamed@456"),
    ("teacher@test.com", "Dr. Fatma Hassan", "teacher", "Teacher@789"),
    ("teacher2@test.com", "Prof. Khaled Omar", "teacher", "Khaled@Prof"),
    ("admin@test.com", "Hussin Admin", "admin", "Admin@Hussin"),
    ("superadmin@test.com", "System Administrator", "admin", "SuperAdmin@2024"),
]

print("-- ============================================")
print("-- HoloLearn Test Accounts - UNIQUE PASSWORDS")
print(f"-- Generated: {datetime.datetime.now()}")
print("-- ============================================\n")

print("-- PASSWORD REFERENCE:")
for email, _, _, password in accounts:
    print(f"-- {email:30} => {password}")  # Changed arrow
print("\n")

print("-- ============================================")
print("-- INSERT STATEMENTS")
print("-- ============================================\n")

for i, (email, full_name, role, password) in enumerate(accounts, 1):
    hashed = pwd_context.hash(password)
    
    role_section = {
        'student': 'STUDENT',
        'teacher': 'TEACHER',
        'admin': 'ADMIN'
    }
    
    if i == 1 or accounts[i-2][2] != role:
        print(f"-- ============================================")
        print(f"-- {role_section[role]} ACCOUNTS")
        print(f"-- ============================================\n")
    
    print(f"-- {full_name} (Password: {password})")
    print(f"INSERT INTO users (email, full_name, role, hashed_password)")
    print(f"VALUES (")
    print(f"    '{email}',")
    print(f"    '{full_name}',")
    print(f"    '{role}',")
    print(f"    '{hashed}'")
    print(f");\n")

print("-- ============================================")
print("-- VERIFICATION QUERIES")
print("-- ============================================\n")

print("-- View all test accounts")
print("SELECT user_id, email, full_name, role")
print("FROM users")
print("WHERE email LIKE '%test.com'")
print("ORDER BY role, user_id;\n")

print("-- Count by role")
print("SELECT role, COUNT(*) as total")
print("FROM users")
print("WHERE email LIKE '%test.com'")
print("GROUP BY role;")
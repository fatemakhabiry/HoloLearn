-- ============================================
-- HoloLearn Test Accounts - UNIQUE PASSWORDS
-- Generated: 2026-01-18 21:23:21.113456
-- ============================================

-- PASSWORD REFERENCE:
-- student@test.com               => Student@123
-- student2@test.com              => Sara@2024
-- mohamed@test.com               => Mohamed@456
-- teacher@test.com               => Teacher@789
-- teacher2@test.com              => Khaled@Prof
-- admin@test.com                 => Admin@Hussin
-- superadmin@test.com            => SuperAdmin@2024


-- ============================================
-- INSERT STATEMENTS
-- ============================================

-- ============================================
-- STUDENT ACCOUNTS
-- ============================================

-- Ahmed Student (Password: Student@123)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'student@test.com',
    'Ahmed Student',
    'STUDENT',
    '$2b$12$gQC5wEPmj69hB8kFq3a10u.jVw1zn6wad2HOQld8jT0P.7FJqX2Yu'
);

-- Sara Ahmed (Password: Sara@2024)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'student2@test.com',
    'Sara Ahmed',
    'STUDENT',
    '$2b$12$Hi4ggrjcMLIr.5sfh/sxju7ZS3n/Fa0ka1x1muhyKuoIMuzpM/AFK'
);

-- Mohamed Ali (Password: Mohamed@456)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'mohamed@test.com',
    'Mohamed Ali',
    'STUDENT',
    '$2b$12$/0Yl7fH7nNTkz7AgphtHMuK7ICVSec60QHClV5NDIeZv5p5X.GMfu'
);

-- ============================================
-- TEACHER ACCOUNTS
-- ============================================

-- Dr. Fatma Hassan (Password: Teacher@789)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'teacher@test.com',
    'Dr. Fatma Hassan',
    'TEACHER',
    '$2b$12$jCG1CfFD.JT2QB4vsJfU2OkvYjzq6jJ4LNHILYHf8kxB2pkXT9rim'
);

-- Prof. Khaled Omar (Password: Khaled@Prof)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'teacher2@test.com',
    'Prof. Khaled Omar',
    'TEACHER',
    '$2b$12$v7zJKMrVIXxRdw361hPwsOMpNvzsA11gpK6iY5sdbEcBUfXKBYFDq'
);

-- ============================================
-- ADMIN ACCOUNTS
-- ============================================

-- Hussin Admin (Password: Admin@Hussin)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'admin@test.com',
    'Hussin Admin',
    'ADMIN',
    '$2b$12$xBMg/Wv9pwLsZ6g/x6LSgeR.8KGSNvVlHptUj/atn/buxHMJVLJce'
);

-- System Administrator (Password: SuperAdmin@2024)
INSERT INTO users (email, full_name, role, hashed_password)
VALUES (
    'superadmin@test.com',
    'System Administrator',
    'ADMIN',
    '$2b$12$R3A5wWqQG4e4sg.elAkgf.6p.ZKp82vTCFefunpdoKNd7bQCnWoxa'
);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- View all test accounts
SELECT user_id, email, full_name, role
FROM users
WHERE email LIKE '%test.com'
ORDER BY role, user_id;

-- Count by role
SELECT role, COUNT(*) as total
FROM users
WHERE email LIKE '%test.com'
GROUP BY role;

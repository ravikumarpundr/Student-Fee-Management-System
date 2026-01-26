import sqlite3
from datetime import datetime
import uuid

DB_NAME="institute.db"

def generate_receipt_no():
    # Format: RCP-YYYYMMDD-XXXX
    return f"RCP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def get_connection():
    return sqlite3.connect(DB_NAME)

def initialize_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fee INTEGER,
            duration INTEGER  -- Duration in months
        )
    """)
    conn.commit()
    conn.close()
    
    # create_courses_table()
    create_students_table()
    create_enrollments_table()
    create_payments_table()
    
def create_payments_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enrollment_id INTEGER,
            amount INTEGER,
            receipt_no TEXT UNIQUE,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_course(name, fee, duration):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO courses (name, fee, duration) VALUES (?, ?, ?)", (name, fee, duration))
    conn.commit()
    conn.close()

def get_courses():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, fee, duration FROM courses")
    courses = c.fetchall()
    conn.close()
    return courses

def delete_course(course_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()

def create_students_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            certificate_id TEXT
        )
    """)
    # Add certificate_id column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE students ADD COLUMN certificate_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()
    
def generate_student_id():
    from datetime import datetime
    year = datetime.now().year
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Find the highest existing student_id number for this year
    c.execute("SELECT student_id FROM students WHERE student_id LIKE ? ORDER BY student_id DESC LIMIT 1", (f"STU{year}-%",))
    result = c.fetchone()
    conn.close()
    
    if result:
        # Extract the number from the highest existing ID and increment
        last_id = result[0]
        last_number = int(last_id.split('-')[1])
        new_number = last_number + 1
    else:
        # No existing IDs for this year, start with 1
        new_number = 1
    
    return f"STU{year}-{str(new_number).zfill(4)}"

def add_student(name, phone, email, address):
    student_id = generate_student_id()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO students (student_id, name, phone, email, address)
        VALUES (?, ?, ?, ?, ?)
    ''', (student_id, name, phone, email, address))
    conn.commit()
    conn.close()

def get_students():
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("SELECT id, name, phone, email, address, certificate_id FROM students")
    data = c.fetchall()
    conn.close()
    return data

def delete_student(student_id):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    
def create_enrollments_table():
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            student_name TEXT,
            course_name TEXT,
            course_fee INTEGER,
            course_duration TEXT,
            enrollment_date TEXT
        )
    """)
    conn.commit()
    conn.close()
    
def enroll_student(student_id, student_name, course_name, fee, duration, date):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO enrollments (student_id, student_name, course_name, course_fee, course_duration, enrollment_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, student_name, course_name, fee, duration, date))
    conn.commit()
    conn.close()
    
def get_all_students():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, student_id, name FROM students")
    students = c.fetchall()
    conn.close()
    return students

def get_all_courses():
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("SELECT name, fee, duration FROM courses")
    return c.fetchall()

def get_student_enrollments(student_id):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("SELECT course_name FROM enrollments WHERE student_id = ?", (student_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_enrollments_by_student_identifier(identifier):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("""
        SELECT e.id, e.course_name, e.course_fee,
            IFNULL(SUM(p.amount), 0)
        FROM enrollments e
        LEFT JOIN payments p ON e.id = p.enrollment_id
        WHERE e.student_id = ? OR e.student_name LIKE ?
        GROUP BY e.id
    """, (identifier, f"%{identifier}%"))
    result = c.fetchall()
    conn.close()
    return result

def add_payment(enrollment_id, amount, date):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    receipt_no = generate_receipt_no()
    c.execute("INSERT INTO payments (enrollment_id, amount, date,receipt_no) VALUES (?, ?, ?,?)",
              (enrollment_id, amount, date,receipt_no))
    conn.commit()
    conn.close()
    
    return receipt_no  # return if you want to show it in UI or PDF

def get_total_paid(enrollment_id):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    c.execute("SELECT IFNULL(SUM(amount), 0) FROM payments WHERE enrollment_id = ?", (enrollment_id,))
    total = c.fetchone()[0]
    conn.close()
    return total

def get_payment_history(student_key, course_key=None):
    conn = sqlite3.connect("institute.db")
    c = conn.cursor()
    
    if course_key:
        c.execute("""
            SELECT p.id, p.receipt_no, s.student_id, s.name, e.course_name, p.amount, p.date
            FROM payments p
            JOIN enrollments e ON p.enrollment_id = e.id
            JOIN students s ON e.student_id = s.id
            WHERE (s.name LIKE ? OR s.student_id LIKE ?)
              AND e.course_name LIKE ?
            ORDER BY p.date DESC
        """, (f"%{student_key}%", f"%{student_key}%", f"%{course_key}%"))
    else:
        c.execute("""
            SELECT p.id, p.receipt_no, s.student_id, s.name, e.course_name, p.amount, p.date
            FROM payments p
            JOIN enrollments e ON p.enrollment_id = e.id
            JOIN students s ON e.student_id = s.id
            WHERE s.name LIKE ? OR s.student_id LIKE ?
            ORDER BY p.date DESC
        """, (f"%{student_key}%", f"%{student_key}%"))

    result = c.fetchall()
    conn.close()
    return result

def course_exists(name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM courses WHERE LOWER(name) = LOWER(?)", (name,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def get_enrollment_id(student_id, course_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM enrollments WHERE student_id = ? AND course_name = ?", (student_id, course_name))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def can_unenroll(student_id, course_name):
    enrollment_id = get_enrollment_id(student_id, course_name)
    if enrollment_id is None:
        return False
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM payments WHERE enrollment_id = ?", (enrollment_id,))
    count = c.fetchone()[0]
    conn.close()
    return count == 0

def unenroll_student(student_id, course_name):
    if not can_unenroll(student_id, course_name):
        return False
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM enrollments WHERE student_id = ? AND course_name = ?", (student_id, course_name))
    conn.commit()
    conn.close()
    return True

def generate_certificate_id():
    """Generate a unique 6-character alphanumeric certificate ID"""
    import random
    import string
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Generate IDs until we find a unique one
    max_attempts = 100
    for _ in range(max_attempts):
        # Generate 6-character alphanumeric string (uppercase letters and digits)
        chars = string.ascii_uppercase + string.digits
        cert_id = ''.join(random.choice(chars) for _ in range(6))
        
        # Check if it's unique
        c.execute("SELECT COUNT(*) FROM students WHERE certificate_id = ?", (cert_id,))
        if c.fetchone()[0] == 0:
            conn.close()
            return cert_id
    
    conn.close()
    # Fallback: use UUID if we can't generate a unique 6-char ID (very unlikely)
    return uuid.uuid4().hex[:6].upper()

def update_certificate_id(student_id, certificate_id):
    """Update the certificate_id for a student"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE students SET certificate_id = ? WHERE id = ?", (certificate_id, student_id))
    conn.commit()
    conn.close()

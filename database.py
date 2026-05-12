"""
database.py - Модуль для работы с базой данных SQLite (SaaS версия)
"""
import sqlite3
import os
from datetime import datetime


DB_NAME = 'checklab_saas.db'


def get_db_connection():
    """Создает подключение к базе данных"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Инициализация структуры базы данных для SaaS"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица организаций (мультитенантность)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            logo_url TEXT,
            subscription_plan TEXT DEFAULT 'free' CHECK(subscription_plan IN ('free', 'basic', 'premium')),
            subscription_expires TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица лидов (заявки с лендинга)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            message TEXT,
            status TEXT DEFAULT 'new' CHECK(status IN ('new', 'contacted', 'converted', 'rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица пользователей (с привязкой к организации)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            user_type TEXT NOT NULL CHECK(user_type IN ('admin', 'teacher', 'student')),
            student_group TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id)
        )
    ''')
    
    # Таблица работ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER NOT NULL,
            student_group TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    ''')
    
    # Таблица шагов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER NOT NULL,
            step_type TEXT NOT NULL CHECK(step_type IN ('checkbox', 'text', 'file')),
            text TEXT NOT NULL,
            required BOOLEAN DEFAULT 1,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    ''')
    
    # Таблица выполнений работ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'submitted')),
            submitted_at TIMESTAMP,
            UNIQUE(work_id, student_id),
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    ''')
    
    # Таблица ответов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            step_id INTEGER NOT NULL,
            answer_text TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(submission_id, step_id),
            FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
            FOREIGN KEY (step_id) REFERENCES steps(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ База данных инициализирована!")


def create_demo_data():
    """Создание демонстрационных данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже данные
    cursor.execute('SELECT COUNT(*) as count FROM organizations')
    if cursor.fetchone()['count'] > 0:
        print("✓ Демо-данные уже существуют")
        conn.close()
        return
    
    # Создаем демо-организации (клиенты)
    demo_orgs = [
        ('Павлодарский колледж информационных технологий', 'ПКИТ', None, 'premium'),
        ('Астана IT University', 'AIU', None, 'premium'),
        ('Алматинский технологический колледж', 'АТК', None, 'basic'),
        ('Караганда Политехникум', 'КП', None, 'basic'),
    ]
    
    for org_name, short_name, logo, plan in demo_orgs:
        cursor.execute('''
            INSERT INTO organizations (name, short_name, logo_url, subscription_plan)
            VALUES (?, ?, ?, ?)
        ''', (org_name, short_name, logo, plan))
    
    # Создаем тестовую организацию для работы
    cursor.execute('''
        INSERT INTO organizations (name, short_name, subscription_plan)
        VALUES (?, ?, ?)
    ''', ('Демо Колледж', 'DEMO', 'free'))
    
    test_org_id = cursor.lastrowid
    
    # Создаем тестовых пользователей
    # Админ организации
    cursor.execute('''
        INSERT INTO users (organization_id, username, full_name, password, user_type, email)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (test_org_id, 'admin', 'Администратор Системы', 'admin123', 'admin', 'admin@demo.kz'))
    
    # Преподаватель
    cursor.execute('''
        INSERT INTO users (organization_id, username, full_name, password, user_type, email)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (test_org_id, 'teacher', 'Иван Петров', 'teacher123', 'teacher', 'teacher@demo.kz'))
    
    # Студенты
    cursor.execute('''
        INSERT INTO users (organization_id, username, full_name, password, user_type, student_group)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (test_org_id, 'student1', 'Алексей Смирнов', 'student123', 'student', 'ИС-21'))
    
    cursor.execute('''
        INSERT INTO users (organization_id, username, full_name, password, user_type, student_group)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (test_org_id, 'student2', 'Мария Иванова', 'student123', 'student', 'ИС-21'))
    
    conn.commit()
    conn.close()
    
    print("✓ Демо-данные созданы:")
    print("  Организаций: 5 (4 клиента + 1 тестовая)")
    print("  Пользователей: 4 (1 admin, 1 teacher, 2 students)")
    print("\n  Тестовые аккаунты:")
    print("  - Админ: admin / admin123")
    print("  - Преподаватель: teacher / teacher123")
    print("  - Студент 1: student1 / student123")
    print("  - Студент 2: student2 / student123")


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ЛИДАМИ
# ============================================================================

def create_lead(org_name, contact_name, phone, email, message):
    """Создание новой заявки с лендинга"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO leads (organization_name, contact_name, phone, email, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (org_name, contact_name, phone, email, message))
    
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def get_all_leads():
    """Получить все заявки"""
    conn = get_db_connection()
    leads = conn.execute('''
        SELECT * FROM leads ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return leads


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ОРГАНИЗАЦИЯМИ
# ============================================================================

def get_all_organizations():
    """Получить все организации (клиентов)"""
    conn = get_db_connection()
    orgs = conn.execute('''
        SELECT * FROM organizations WHERE is_active = 1 ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return orgs


def get_organization(org_id):
    """Получить организацию по ID"""
    conn = get_db_connection()
    org = conn.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
    conn.close()
    return org


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ============================================================================

def get_user_by_credentials(username, password):
    """Получить пользователя по логину и паролю"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1',
        (username, password)
    ).fetchone()
    conn.close()
    return user


def get_all_groups(org_id):
    """Получить список всех групп студентов в организации"""
    conn = get_db_connection()
    groups = conn.execute(
        'SELECT DISTINCT student_group FROM users WHERE organization_id = ? AND user_type = "student" AND student_group IS NOT NULL',
        (org_id,)
    ).fetchall()
    conn.close()
    return [g['student_group'] for g in groups]


# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТ (С УЧЕТОМ ОРГАНИЗАЦИИ)
# ============================================================================

def create_work(org_id, title, description, teacher_id, student_group, steps):
    """Создание новой работы с шагами"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO works (organization_id, title, description, teacher_id, student_group)
            VALUES (?, ?, ?, ?, ?)
        ''', (org_id, title, description, teacher_id, student_group))
        
        work_id = cursor.lastrowid
        
        for step in steps:
            cursor.execute('''
                INSERT INTO steps (work_id, step_type, text, required)
                VALUES (?, ?, ?, ?)
            ''', (work_id, step['type'], step['text'], step.get('required', True)))
        
        conn.commit()
        return work_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_teacher_works(teacher_id, org_id):
    """Получить все работы преподавателя"""
    conn = get_db_connection()
    works = conn.execute('''
        SELECT w.*, 
               COUNT(DISTINCT s.student_id) as total_students,
               COUNT(DISTINCT CASE WHEN s.status = 'submitted' THEN s.student_id END) as submitted_students
        FROM works w
        LEFT JOIN users u ON u.student_group = w.student_group AND u.user_type = 'student' AND u.organization_id = w.organization_id
        LEFT JOIN submissions s ON s.work_id = w.id AND s.student_id = u.id
        WHERE w.teacher_id = ? AND w.organization_id = ?
        GROUP BY w.id
        ORDER BY w.created_at DESC
    ''', (teacher_id, org_id)).fetchall()
    conn.close()
    return works


def get_work_details(work_id):
    """Получить детали работы"""
    conn = get_db_connection()
    
    work = conn.execute('SELECT * FROM works WHERE id = ?', (work_id,)).fetchone()
    if not work:
        conn.close()
        return None
    
    steps = conn.execute(
        'SELECT * FROM steps WHERE work_id = ? ORDER BY id',
        (work_id,)
    ).fetchall()
    
    conn.close()
    return {'work': work, 'steps': steps}


def get_work_submissions(work_id):
    """Получить все выполнения работы студентами"""
    conn = get_db_connection()
    submissions = conn.execute('''
        SELECT u.id, u.full_name, u.username, s.id as submission_id, s.status, s.submitted_at
        FROM users u
        LEFT JOIN submissions s ON s.student_id = u.id AND s.work_id = ?
        WHERE u.student_group = (SELECT student_group FROM works WHERE id = ?)
          AND u.user_type = 'student'
          AND u.organization_id = (SELECT organization_id FROM works WHERE id = ?)
        ORDER BY u.full_name
    ''', (work_id, work_id, work_id)).fetchall()
    conn.close()
    return submissions


def get_student_works(student_id, org_id):
    """Получить все работы для студента"""
    conn = get_db_connection()
    
    student = conn.execute('SELECT student_group FROM users WHERE id = ?', (student_id,)).fetchone()
    if not student:
        conn.close()
        return []
    
    works = conn.execute('''
        SELECT w.*, s.status, s.submitted_at,
               COUNT(st.id) as total_steps,
               COUNT(a.id) as completed_steps
        FROM works w
        LEFT JOIN submissions s ON s.work_id = w.id AND s.student_id = ?
        LEFT JOIN steps st ON st.work_id = w.id
        LEFT JOIN answers a ON a.submission_id = s.id AND a.step_id = st.id
        WHERE w.student_group = ? AND w.organization_id = ?
        GROUP BY w.id
        ORDER BY w.created_at DESC
    ''', (student_id, student['student_group'], org_id)).fetchall()
    
    conn.close()
    return works


def get_or_create_submission(work_id, student_id):
    """Получить или создать submission для студента"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    submission = conn.execute(
        'SELECT * FROM submissions WHERE work_id = ? AND student_id = ?',
        (work_id, student_id)
    ).fetchone()
    
    if not submission:
        cursor.execute('''
            INSERT INTO submissions (work_id, student_id, status)
            VALUES (?, ?, 'in_progress')
        ''', (work_id, student_id))
        conn.commit()
        submission_id = cursor.lastrowid
        submission = conn.execute(
            'SELECT * FROM submissions WHERE id = ?',
            (submission_id,)
        ).fetchone()
    
    conn.close()
    return submission


def save_answer(submission_id, step_id, answer_text=None, file_path=None):
    """Сохранить или обновить ответ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO answers (submission_id, step_id, answer_text, file_path)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(submission_id, step_id) DO UPDATE SET
                answer_text = excluded.answer_text,
                file_path = excluded.file_path,
                created_at = CURRENT_TIMESTAMP
        ''', (submission_id, step_id, answer_text, file_path))
        
        conn.commit()
    finally:
        conn.close()


def submit_work(submission_id):
    """Отметить работу как сданную"""
    conn = get_db_connection()
    conn.execute('''
        UPDATE submissions 
        SET status = 'submitted', submitted_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (submission_id,))
    conn.commit()
    conn.close()


def get_submission_answers(submission_id):
    """Получить все ответы по submission"""
    conn = get_db_connection()
    answers = conn.execute('''
        SELECT a.*, s.text as step_text, s.step_type, s.required
        FROM answers a
        JOIN steps s ON s.id = a.step_id
        WHERE a.submission_id = ?
        ORDER BY s.id
    ''', (submission_id,)).fetchall()
    conn.close()
    return answers


def get_student_work_data(work_id, student_id):
    """Получить данные работы для выполнения студентом"""
    conn = get_db_connection()
    
    work = conn.execute('SELECT * FROM works WHERE id = ?', (work_id,)).fetchone()
    if not work:
        conn.close()
        return None
    
    steps = conn.execute(
        'SELECT * FROM steps WHERE work_id = ? ORDER BY id',
        (work_id,)
    ).fetchall()
    
    submission = get_or_create_submission(work_id, student_id)
    
    answers = conn.execute('''
        SELECT * FROM answers WHERE submission_id = ?
    ''', (submission['id'],)).fetchall()
    
    answers_dict = {}
    for answer in answers:
        answers_dict[answer['step_id']] = answer
    
    conn.close()
    
    return {
        'work': work,
        'steps': steps,
        'submission': submission,
        'answers': answers_dict
    }


# ============================================================================
# СТАТИСТИКА
# ============================================================================

def get_platform_stats():
    """Получить общую статистику платформы для лендинга"""
    conn = get_db_connection()
    
    # Количество организаций
    orgs_count = conn.execute('SELECT COUNT(*) as count FROM organizations WHERE is_active = 1').fetchone()['count']
    
    # Количество пользователей
    users_count = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1').fetchone()['count']
    
    # Количество работ
    works_count = conn.execute('SELECT COUNT(*) as count FROM works').fetchone()['count']
    
    # Количество выполнений
    submissions_count = conn.execute('SELECT COUNT(*) as count FROM submissions WHERE status = "submitted"').fetchone()['count']
    
    conn.close()
    
    return {
        'organizations': orgs_count,
        'users': users_count,
        'works': works_count,
        'submissions': submissions_count
    }

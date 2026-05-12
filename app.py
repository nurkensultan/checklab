"""
app.py - Основное Flask приложение CheckLab Engine SaaS
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'checklab-saas-secret-key-2024')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ============================================================================
# LANDING PAGE & MARKETING
# ============================================================================

@app.route('/')
def landing():
    """Главная страница - маркетинговый лендинг"""
    stats = db.get_platform_stats()
    organizations = db.get_all_organizations()
    # Показываем только клиентов (не тестовую организацию)
    clients = [org for org in organizations if org['short_name'] != 'DEMO']
    return render_template('landing.html', stats=stats, clients=clients)


@app.route('/api/submit_lead', methods=['POST'])
def submit_lead():
    """API: Отправка заявки с лендинга"""
    data = request.get_json()
    
    org_name = data.get('organization_name', '').strip()
    contact_name = data.get('contact_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()
    
    if not org_name or not contact_name or not phone:
        return jsonify({'success': False, 'error': 'Заполните обязательные поля'}), 400
    
    try:
        lead_id = db.create_lead(org_name, contact_name, phone, email, message)
        return jsonify({'success': True, 'lead_id': lead_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AUTHENTICATION
# ============================================================================

@app.route('/login')
def login_page():
    """Страница авторизации"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Обработка авторизации"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        return render_template('login.html', error='Введите логин и пароль')
    
    user = db.get_user_by_credentials(username, password)
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['user_type'] = user['user_type']
        session['organization_id'] = user['organization_id']
        session['student_group'] = user['student_group']
        
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error='Неверный логин или пароль')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('landing'))


@app.route('/dashboard')
def dashboard():
    """Единая точка входа в дашборд (перенаправление по роли)"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    if session['user_type'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif session['user_type'] == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin')
def admin_dashboard():
    """Дашборд администратора организации"""
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect(url_for('login_page'))
    
    org = db.get_organization(session['organization_id'])
    leads = db.get_all_leads()
    stats = db.get_platform_stats()
    
    return render_template('admin.html', organization=org, leads=leads, stats=stats)


# ============================================================================
# TEACHER ROUTES
# ============================================================================

@app.route('/teacher')
def teacher_dashboard():
    """Дашборд преподавателя"""
    if 'user_id' not in session or session['user_type'] not in ['teacher', 'admin']:
        return redirect(url_for('login_page'))
    
    works = db.get_teacher_works(session['user_id'], session['organization_id'])
    return render_template('teacher.html', works=works)


@app.route('/teacher/create')
def create_work_page():
    """Страница создания работы"""
    if 'user_id' not in session or session['user_type'] not in ['teacher', 'admin']:
        return redirect(url_for('login_page'))
    
    groups = db.get_all_groups(session['organization_id'])
    return render_template('create_work.html', groups=groups)


@app.route('/api/create_work', methods=['POST'])
def api_create_work():
    """API: Создание работы"""
    if 'user_id' not in session or session['user_type'] not in ['teacher', 'admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'success': False, 'error': 'Название работы обязательно'}), 400
    
    if not data.get('student_group'):
        return jsonify({'success': False, 'error': 'Выберите группу'}), 400
    
    if not data.get('steps') or len(data['steps']) == 0:
        return jsonify({'success': False, 'error': 'Добавьте хотя бы один шаг'}), 400
    
    try:
        work_id = db.create_work(
            org_id=session['organization_id'],
            title=data['title'],
            description=data.get('description', ''),
            teacher_id=session['user_id'],
            student_group=data['student_group'],
            steps=data['steps']
        )
        
        return jsonify({'success': True, 'work_id': work_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/work/<int:work_id>')
def api_get_work(work_id):
    """API: Получить данные работы"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    work_data = db.get_work_details(work_id)
    if not work_data:
        return jsonify({'success': False, 'error': 'Работа не найдена'}), 404
    
    submissions = db.get_work_submissions(work_id)
    
    result = {
        'work': dict(work_data['work']),
        'steps': [dict(step) for step in work_data['steps']],
        'submissions': [dict(sub) for sub in submissions]
    }
    
    return jsonify(result)


@app.route('/api/submission/<int:submission_id>')
def api_get_submission(submission_id):
    """API: Получить ответы студента"""
    if 'user_id' not in session or session['user_type'] not in ['teacher', 'admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    answers = db.get_submission_answers(submission_id)
    
    return jsonify({
        'success': True,
        'answers': [dict(answer) for answer in answers]
    })


# ============================================================================
# STUDENT ROUTES
# ============================================================================

@app.route('/student')
def student_dashboard():
    """Дашборд студента"""
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login_page'))
    
    works = db.get_student_works(session['user_id'], session['organization_id'])
    return render_template('student.html', works=works)


@app.route('/api/student/work/<int:work_id>')
def api_get_student_work(work_id):
    """API: Получить работу для выполнения студентом"""
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    work_data = db.get_student_work_data(work_id, session['user_id'])
    
    if not work_data:
        return jsonify({'success': False, 'error': 'Работа не найдена'}), 404
    
    result = {
        'work': dict(work_data['work']),
        'steps': [dict(step) for step in work_data['steps']],
        'submission': dict(work_data['submission']),
        'answers': {k: dict(v) for k, v in work_data['answers'].items()}
    }
    
    return jsonify(result)


@app.route('/api/save_answer', methods=['POST'])
def api_save_answer():
    """API: Сохранить ответ студента"""
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    submission_id = request.form.get('submission_id')
    if not submission_id:
        return jsonify({'success': False, 'error': 'submission_id required'}), 400
    
    step_id = request.form.get('step_id')
    if not step_id:
        return jsonify({'success': False, 'error': 'step_id required'}), 400
    
    answer_text = request.form.get('answer_text')
    file_path = None
    
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{submission_id}_{step_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            file_path = unique_filename
    
    try:
        db.save_answer(submission_id, step_id, answer_text, file_path)
        return jsonify({'success': True, 'file_path': file_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/submit_work', methods=['POST'])
def api_submit_work():
    """API: Сдать работу на проверку"""
    if 'user_id' not in session or session['user_type'] != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    submission_id = data.get('submission_id')
    
    if not submission_id:
        return jsonify({'success': False, 'error': 'submission_id required'}), 400
    
    try:
        db.submit_work(submission_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# FILE ROUTES
# ============================================================================

@app.route('/uploads/<filename>')
def download_file(filename):
    """Скачивание загруженного файла"""
    if 'user_id' not in session:
        return "Unauthorized", 401
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return "Внутренняя ошибка сервера", 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CheckLab Engine SaaS")
    print("=" * 60)
    print("🚀 Запуск сервера на http://127.0.0.1:5000")
    print("-" * 60)
    print("📄 Главная страница: http://127.0.0.1:5000")
    print("🔐 Вход в систему: http://127.0.0.1:5000/login")
    print("-" * 60)
    print("Тестовые аккаунты:")
    print("  👨‍💼 Админ: admin / admin123")
    print("  👨‍🏫 Преподаватель: teacher / teacher123")
    print("  👨‍🎓 Студент 1: student1 / student123")
    print("  👨‍🎓 Студент 2: student2 / student123")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

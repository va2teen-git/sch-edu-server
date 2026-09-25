import sys
import os
from flask import Flask, render_template, request, redirect, session, jsonify
from logic import generate_network_l1_task, generate_network_l2_task
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from logic import generate_random_bits, repetition_encode, introduce_noise, repetition_decode, hamming_encode, calculate_syndrome, add_parity_bit, generate_law_incidents
from datetime import datetime
import random
import secrets

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

import json
import os

lessons_index = {}
index_path = os.path.join(os.getcwd(), 'lessons_index.json')
if os.path.exists(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        lessons_index = json.load(f)



import logging
from logging.handlers import RotatingFileHandler
import os

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(clientip)s - %(message)s')
log_file_path = os.path.join(os.getcwd(), 'server.log')
log_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)

app.logger.setLevel(logging.INFO)
app.logger.addHandler(log_handler)

# Custom filter to inject client IP safely
class ContextFilter(logging.Filter):
    def filter(self, record):
        from flask import request, has_request_context
        if has_request_context():
            record.clientip = request.remote_addr or 'unknown'
        else:
            record.clientip = 'system'
        return True

app.logger.addFilter(ContextFilter())

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(log_handler)
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.addFilter(ContextFilter())


# Generating a secure random secret key for the server instance
app.secret_key = secrets.token_hex(32)

old_db_path = os.path.join(os.getcwd(), 'hamming_logs.db')
new_db_path = os.path.join(os.getcwd(), 'school_data.db')

if os.path.exists(old_db_path) and not os.path.exists(new_db_path):
    os.rename(old_db_path, new_db_path)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{new_db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

db = SQLAlchemy(app)

# Настройка серверных сессий
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_PERMANENT'] = False
Session(app)

class LogEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(500), nullable=False)

class TaskAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    mission_name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    time_spent_sec = db.Column(db.Integer, nullable=False)
    attempts_count = db.Column(db.Integer, default=0)
    success = db.Column(db.Boolean, default=False)
    action_log = db.Column(db.Text, nullable=False) # JSON string

with app.app_context():
    db.create_all()
    # Ensure the sessions table is explicitly created (required for some Flask-Session versions)
    if hasattr(app, 'session_interface') and hasattr(app.session_interface, 'sql_session_model'):
        app.session_interface.sql_session_model.__table__.create(db.engine, checkfirst=True)

def log_action(name, action_text):
    if name != '#учитель#':
        new_log = LogEvent(student_name=name, action=action_text)
        db.session.add(new_log)
        
        # Автоматическая конвертация старых логов в новую телеметрию
        if '[ВЕРНО]' in action_text or '[ОШИБКА]' in action_text:
            # Игнорируем логи, которые уже сгенерированы новой телеметрией
            if 'Попыток:' not in action_text:
                success = '[ВЕРНО]' in action_text
                mission = "Прочие задания"
                if ":" in action_text:
                    mission = action_text.split(":")[0].strip()
                user_input = action_text.split(']', 1)[-1].strip()
                
                # Ищем последнюю попытку
                attempt = TaskAttempt.query.filter_by(student_name=name, mission_name=mission).order_by(TaskAttempt.id.desc()).first()
                
                import json
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                now_str = now.isoformat() + "Z"
                
                # Если нет попытки, или предыдущая была завершена успехом, или слишком старая (> 10 мин)
                is_new = True
                if attempt:
                    try:
                        start_dt = datetime.fromisoformat(attempt.start_time.replace('Z', ''))
                        if not attempt.success and (now - start_dt) < timedelta(minutes=10):
                            is_new = False
                    except:
                        pass
                        
                if is_new:
                    attempt = TaskAttempt(
                        student_name=name,
                        mission_name=mission,
                        start_time=now_str,
                        time_spent_sec=0,
                        attempts_count=0,
                        success=success,
                        action_log="[]"
                    )
                    db.session.add(attempt)
                    
                logs_arr = json.loads(attempt.action_log)
                logs_arr.append({
                    "time": now_str,
                    "input": user_input,
                    "success": success
                })
                
                attempt.attempts_count += 1
                attempt.success = success
                attempt.action_log = json.dumps(logs_arr)
                
                try:
                    first_time = datetime.fromisoformat(logs_arr[0]["time"].replace('Z',''))
                    attempt.time_spent_sec = int((now - first_time).total_seconds())
                except:
                    pass

        db.session.commit()

@app.route('/telemetry', methods=['POST'])
def telemetry():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    data = request.json
    status_flag = data.get('status', 'completed')
    
    attempt = TaskAttempt.query.filter_by(
        student_name=session['student_name'],
        mission_name=data.get('mission_name', 'Unknown'),
        start_time=data.get('start_time', '')
    ).first()
    
    if not attempt:
        attempt = TaskAttempt(
            student_name=session['student_name'],
            mission_name=data.get('mission_name', 'Unknown'),
            start_time=data.get('start_time', '')
        )
        db.session.add(attempt)
        
    attempt.time_spent_sec = data.get('time_spent_sec', 0)
    attempt.attempts_count = data.get('attempts_count', 0)
    attempt.success = data.get('success', False)
    attempt.action_log = data.get('action_log', '[]')
    
    db.session.commit()
    
    if status_flag != 'in_progress':
        log_action(session['student_name'], f"[{'УСПЕХ' if attempt.success else 'ПРОВАЛ'}] {attempt.mission_name}. Попыток: {attempt.attempts_count}, Время: {attempt.time_spent_sec}с")
        
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('student_name', '').strip()
        grade = request.form.get('grade', '')
        
        if not name or not grade:
            return render_template('login.html', error="Заполните все поля")
        
        if name == '#учитель#':
            session['student_name'] = '#учитель#'
            session['grade'] = 'teacher'
            return redirect('/teacher')
                
        grade_map = {'7': '7', '8': '8', '9': '9', '10-gum': '10 Гум', '10-tech': '10 Тех', '11-gum': '11 Гум', '11-tech': '11 Тех'}
        display_grade = grade_map.get(grade, grade)
        full_name = f"{name} ({display_grade} кл)"
        session['student_name'] = full_name
        session['grade'] = grade
        
        log_action(full_name, "--- ВОШЕЛ В СИСТЕМУ ---")
        session['m1_correct'] = 0
        session['m2_correct'] = 0
        return redirect('/menu')
        
    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'student_name' not in session: return redirect('/')
    grade = session.get('grade', '8')
    lessons = lessons_index.get(grade, [])
    return render_template('menu.html', name=session['student_name'], grade=grade, lessons=lessons)

@app.route('/theory')
def theory():
    if 'student_name' not in session: return redirect('/')
    return render_template('theory.html')

@app.route('/mission_parity')
def mission_parity():
    if 'student_name' not in session: return redirect('/')
    
    if session.get('m0_correct', 0) >= 5:
        return render_template('mission_parity.html', completed=True)
        
    data = generate_random_bits(4)
    encoded = add_parity_bit(data)
    
    # 50% chance to introduce an error
    import random
    has_error = random.choice([True, False])
    if has_error:
        task_bits = introduce_noise(encoded, 1)
    else:
        task_bits = encoded
        
    session['m0_task'] = task_bits
    session['m0_has_error'] = has_error
    
    return render_template('mission_parity.html', task=task_bits, correct=session.get('m0_correct', 0), target=5, completed=False)

@app.route('/check_parity', methods=['POST'])
def check_parity_route():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    user_says_error = request.json.get('has_error')
    actual_error = session.get('m0_has_error')
    
    if user_says_error == actual_error:
        session['m0_correct'] = session.get('m0_correct', 0) + 1
        log_action(session['student_name'], f"М0 (Четность): [ВЕРНО] Сигнал {session.get('m0_task')}. Ответ пользователя: {'ошибка есть' if user_says_error else 'ошибок нет'}.")
        return jsonify({"success": True, "msg": "Правильно! Ты отлично справился."})
    else:
        log_action(session['student_name'], f"М0 (Четность): [ОШИБКА] Сигнал {session.get('m0_task')}. Ошибся с определением.")
        explanation = "Сумма единиц нечетная, значит ошибка есть!" if actual_error else "Сумма единиц четная, значит ошибок нет!"
        return jsonify({"success": False, "msg": f"Неверно. {explanation}"})

@app.route('/mission1')
def mission1():
    if 'student_name' not in session: return redirect('/')
    
    if session.get('m1_correct', 0) >= 3:
        return render_template('mission1.html', completed=True)
        
    data_bit = generate_random_bits(1)
    encoded = repetition_encode(data_bit)
    noisy = introduce_noise(encoded, 1)
    session['m1_task'] = noisy
    session['m1_answer'] = data_bit[0]
    
    return render_template('mission1.html', task=noisy, correct=session.get('m1_correct', 0), target=3, completed=False)

@app.route('/check_m1', methods=['POST'])
def check_m1():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    answer_str = request.json.get('answer')
    if answer_str is None or answer_str == '':
        return jsonify({"success": False, "msg": "Вы ничего не ввели"})
        
    try:
        ans = int(answer_str)
    except:
        return jsonify({"success": False, "msg": "Введите число 0 или 1"})
        
    correct_ans = session.get('m1_answer')
    if ans == correct_ans:
        session['m1_correct'] = session.get('m1_correct', 0) + 1
        log_action(session['student_name'], f"М1: [ВЕРНО] Расшифровал {session.get('m1_task')} как {ans}.")
        return jsonify({"success": True, "msg": f"Правильно! Исходный бит был {ans}."})
    else:
        log_action(session['student_name'], f"М1: [ОШИБКА] Ввел {ans} вместо {correct_ans} для {session.get('m1_task')}.")
        return jsonify({"success": False, "msg": f"Ошибка! По правилу большинства должно быть {correct_ans}."})

@app.route('/mission2')
def mission2():
    if 'student_name' not in session: return redirect('/')
    
    if session.get('m2_correct', 0) >= 10:
        return render_template('mission2.html', completed=True)
        
    data = generate_random_bits(4)
    encoded = hamming_encode(data)
    noisy = introduce_noise(encoded, 1)
    syndrome, _ = calculate_syndrome(noisy)
    
    session['m2_task'] = noisy
    session['m2_syndrome'] = syndrome
    
    log_action(session['student_name'], f"М2: Выдана задача {noisy}. Верный ответ: поз {syndrome}.")
    
    return render_template('mission2.html', task=noisy, correct=session.get('m2_correct', 0), target=10, completed=False)

@app.route('/check_m2', methods=['POST'])
def check_m2():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    pos = request.json.get('position')
    correct_pos = session.get('m2_syndrome')
    
    if pos == correct_pos:
        session['m2_correct'] = session.get('m2_correct', 0) + 1
        log_action(session['student_name'], f"М2: [ВЕРНО] Кликнул на поз {pos}.")
        return jsonify({"success": True, "msg": f"Блестяще! Ошибка действительно в бите №{pos}."})
    else:
        log_action(session['student_name'], f"М2: [ОШИБКА] Выбрал поз {pos} вместо {correct_pos}.")
        return jsonify({"success": False, "msg": f"Ошибка! Выбрана позиция {pos}. Ошибка реально была в позиции {correct_pos}."})



@app.route('/teacher')
def teacher():
    if session.get('student_name') != '#учитель#':
        return redirect('/')
        
    attempts = TaskAttempt.query.order_by(TaskAttempt.id.desc()).all()
    
    students = {}
    import json
    from datetime import datetime
    
    for attempt in attempts:
        s_name = attempt.student_name
        
        lesson_name = attempt.mission_name
        task_name = 'Общее'
        if ' :: ' in attempt.mission_name:
            lesson_name, task_name = attempt.mission_name.split(' :: ', 1)
            
        if s_name not in students:
            students[s_name] = {'missions': {}}
            
        KNOWN_LESSON_TASKS = {
            'Практическая работа: Практическая работа по теме "Помехоустойчивые коды"': ['Четность', 'Повторение', 'Хэмминг'],
            'Законодательство Российской Федерации в области программного обеспечения и данных': ['Уровень 1', 'Уровень 2', 'Уровень 3'],
            'Практическая работа: Законодательство Российской Федерации в области программного обеспечения и данных': ['Уровень 1', 'Уровень 2', 'Уровень 3'],
            'Системы. Компоненты системы и их взаимодействие. Системный эффект. Управление как информационный процесс. Обратная связь': ['М1 (Ящики)', 'М2 (Баланс ОС)', 'М3 (TCP)'],
            'Принципы построения и аппаратные компоненты компьютерных сетей. Сетевые протоколы': ['Уровень 1', 'Уровень 2', 'Уровень 3'],
            'Восьмеричная система счисления': ['Уровень 1', 'Уровень 2', 'Уровень 3']
        }
        
        if lesson_name not in students[s_name]['missions']:
            default_tasks = {}
            known_tasks = KNOWN_LESSON_TASKS.get(lesson_name, [])
            if not known_tasks and task_name != 'Общее':
                known_tasks = [task_name] # Fallback
                
            for kt in known_tasks:
                default_tasks[kt] = {
                    'attempts_list': [],
                    'time_spent': 0,
                    'errors': 0,
                    'success': False
                }
                
            students[s_name]['missions'][lesson_name] = {
                'tasks': default_tasks,
                'timeline': [],
                'global_time': 0,
                'global_errors': 0,
                'tasks_completed': set()
            }
            
        lesson_obj = students[s_name]['missions'][lesson_name]
        
        if task_name not in lesson_obj['tasks']:
            lesson_obj['tasks'][task_name] = {
                'attempts_list': [],
                'time_spent': 0,
                'errors': 0,
                'success': False
            }
        
        task_obj = lesson_obj['tasks'][task_name]
        
        parsed = []
        try:
            if attempt.action_log:
                parsed = json.loads(attempt.action_log)
        except:
            pass
            
        attempt.action_log_parsed = parsed
        task_obj['attempts_list'].append(attempt)
        
        if attempt.success:
            task_obj['success'] = True
            lesson_obj['tasks_completed'].add(task_name)
            
        # Calculate stats for the task based on the LATEST attempt
        # or aggregate them. We'll aggregate time and errors from parsed log.
        task_time = attempt.time_spent_sec
        task_errors = sum(1 for act in parsed if not act.get('success', True))
        
        task_obj['time_spent'] += task_time
        task_obj['errors'] += task_errors
        
        last_time = None
        for idx, act in enumerate(parsed):
            try:
                dt = datetime.fromisoformat(act['time'].replace('Z', ''))
            except:
                dt = datetime.utcnow()
                
            think_time = 0
            if last_time:
                think_time = round((dt - last_time).total_seconds(), 1)
            last_time = dt
            
            is_final_success = act.get('success', False) and attempt.success and (idx == len(parsed) - 1)
            
            lesson_obj['timeline'].append({
                'time': dt,
                'task': task_name,
                'type': 'action',
                'text': act.get('input', ''),
                'success': act.get('success', False),
                'attempt_num': attempt.attempts_count,
                'think_time': think_time,
                'is_final_success': is_final_success,
                'total_attempts': attempt.attempts_count,
                'total_time': attempt.time_spent_sec
            })
            
    # Sort timelines globally per lesson
    for s_data in students.values():
        for m_data in s_data['missions'].values():
            m_data['timeline'].sort(key=lambda x: x['time'], reverse=True)
            
            # Global stats aggregate
            for t_data in m_data['tasks'].values():
                m_data['global_time'] += t_data['time_spent']
                m_data['global_errors'] += t_data['errors']
                
    return render_template('teacher.html', students=students)


@app.route('/check_octal_level', methods=['POST'])
def check_octal_level():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    data = request.json
    level = str(data.get('level', '1'))
    user_answer = str(data.get('answer', '')).strip()
    
    correct_answer = str(session.get(f'octal_lvl{level}_ans', ''))
    
    if user_answer == correct_answer:
        log_action(session['student_name'], f"Урок 8кл (Ур {level}): [ВЕРНО] Ответ: {correct_answer}")
        return jsonify({"success": True, "msg": "Доступ разрешен!"})
    else:
        log_action(session['student_name'], f"Урок 8кл (Ур {level}): [ОШИБКА] Ввел {user_answer} вместо {correct_answer}")
        return jsonify({"success": False, "msg": "Ошибка! Код не подходит."})



@app.route('/api/sys11/m1', methods=['POST'])
def api_sys11_m1():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    data = request.json
    action = data.get('action')
    import random
    
    if action == 'generate':
        ops = [('+', lambda x, n: x+n), ('-', lambda x, n: x-n), ('*', lambda x, n: x*n)]
        a_op_idx = random.randint(0, 2)
        b_op_idx = random.randint(0, 2)
        c_op_idx = random.randint(0, 2)
        
        a_n = random.randint(2, 11)
        b_n = random.randint(2, 11)
        c_n = random.randint(2, 11)
        
        start_val = random.randint(1, 10)
        
        seqs = [('A','B','C'), ('A','C','B'), ('B','A','C'), ('B','C','A'), ('C','A','B'), ('C','B','A')]
        correct_seq = random.choice(seqs)
        
        val = start_val
        funcs = {
            'A': lambda x: ops[a_op_idx][1](x, a_n),
            'B': lambda x: ops[b_op_idx][1](x, b_n),
            'C': lambda x: ops[c_op_idx][1](x, c_n),
        }
        val = funcs[correct_seq[0]](val)
        val = funcs[correct_seq[1]](val)
        val = funcs[correct_seq[2]](val)
        
        session['sys11_m1_target'] = val
        session['sys11_m1_start'] = start_val
        session['sys11_m1_funcs'] = {
            'A': {'op': ops[a_op_idx][0], 'n': a_n},
            'B': {'op': ops[b_op_idx][0], 'n': b_n},
            'C': {'op': ops[c_op_idx][0], 'n': c_n}
        }
        
        return jsonify({
            'start_val': start_val,
            'target_val': val,
            'funcs': session['sys11_m1_funcs']
        })
        
    elif action == 'check':
        seq = data.get('seq')
        if 'sys11_m1_target' not in session:
            return jsonify({'success': False, 'invalid': True, 'error': 'No active task. Please wait for next generation.'})
            
        funcs_meta = session['sys11_m1_funcs']
        val = session['sys11_m1_start']
        
        ops_map = {'+': lambda x, n: x+n, '-': lambda x, n: x-n, '*': lambda x, n: x*n}
        for step in seq:
            meta = funcs_meta.get(step)
            if not meta: return jsonify({'success': False})
            val = ops_map[meta['op']](val, meta['n'])
            
        if val == session['sys11_m1_target']:
            session.pop('sys11_m1_target', None) # Burn the token
            return jsonify({'success': True, 'val': val})
        else:
            return jsonify({'success': False, 'val': val, 'target': session['sys11_m1_target']})
    
    return jsonify({"error": "Unknown action"})

@app.route('/api/sys11/m3', methods=['POST'])
def api_sys11_m3():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    data = request.json
    action = data.get('action')
    import random
    
    if action == 'generate':
        win = random.randint(2, 16)
        is_loss = random.random() > 0.6
        
        if is_loss:
            correct = max(1, win // 2)
        else:
            correct = win + 1
            
        session['sys11_m3_ans'] = correct
        return jsonify({'win': win, 'is_loss': is_loss})
        
    elif action == 'check':
        ans = data.get('ans')
        if 'sys11_m3_ans' not in session:
            return jsonify({'success': False, 'invalid': True, 'error': 'No active task. Please wait for next generation.'})
            
        if ans == session['sys11_m3_ans']:
            session.pop('sys11_m3_ans', None) # Burn the token
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    
    return jsonify({"error": "Unknown action"})

@app.route('/api/law_task', methods=['POST'])
def api_law_task():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    data = request.json
    level = data.get('level', 1)
    import random
    
    if level == 1:
        tasks = [
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №45-А", "department": "Отдел видеомонтажа", "software": "DaVinci Resolve (Взломанная версия)", "desc": "Системный администратор установил версию с торрент-трекера. Просим утвердить использование.", "ans": "Нарушение", "hint": "Взлом коммерческого ПО - пиратство."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №12-Б", "department": "Отдел разработки", "software": "Библиотека шифрования (GPLv3)", "desc": "Планируем внедрить эту библиотеку в наше проприетарное приложение. Исходный код мы не откроем.", "ans": "Нарушение", "hint": "GPL требует открытия исходного кода любой программы, использующей код GPL."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №88-В", "department": "Бухгалтерия", "software": "Архиватор (Пробная версия)", "desc": "Установлен 40 дней назад. При запуске просит купить лицензию, но работает.", "ans": "Нарушение", "hint": "Это Shareware. После пробного периода программу нужно купить или удалить."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №02-Г", "department": "Отдел 3D", "software": "Blender", "desc": "Скачана с сайта. Лицензия позволяет коммерческое использование. Код менять не будем.", "ans": "Open Source", "hint": "Blender - свободное ПО (GNU GPL), разрешает коммерческое использование."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №15-Д", "department": "Аналитика", "software": "PDF-ридер", "desc": "Бесплатна, но запрещает декомпиляцию. Исходного кода нет.", "ans": "Freeware", "hint": "Freeware - бесплатное ПО с закрытым кодом."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №16-Е", "department": "Отдел продаж", "software": "Microsoft Office (Ключ из интернета)", "desc": "Нашли в интернете корпоративный ключ активации и активировали офис на 50 ПК.", "ans": "Нарушение", "hint": "Использование чужих корпоративных ключей - это незаконное использование (пиратство)."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №17-Ж", "department": "Разработка", "software": "Утилита (MIT License)", "desc": "Будем использовать код утилиты в нашем закрытом коммерческом проекте.", "ans": "Open Source", "hint": "Лицензия MIT (в отличие от GPL) позволяет использовать код в проприетарных проектах без открытия исходников."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №18-З", "department": "Колл-центр", "software": "Skype", "desc": "Скачан официально. Используется для связи с клиентами. Код закрыт, денег не просит.", "ans": "Freeware", "hint": "Классический пример Freeware."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №19-И", "department": "Архитектура", "software": "AutoCAD (Студенческая версия)", "desc": "Студент-практикант установил свою студенческую лицензию, чтобы мы могли делать коммерческие чертежи.", "ans": "Нарушение", "hint": "Студенческие (Educational) лицензии строго запрещают коммерческое использование."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №20-К", "department": "Серверный отдел", "software": "Ubuntu Server", "desc": "Установили на все серверы компании. Операционная система бесплатна и с открытым кодом.", "ans": "Open Source", "hint": "Linux/Ubuntu распространяется под свободными лицензиями."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №21-Л", "department": "Разработка", "software": "Текстовый редактор Sublime", "desc": "В заголовке написано 'UNREGISTERED', но мы используем его уже год для написания кода компании.", "ans": "Нарушение", "hint": "Игнорирование надписи 'UNREGISTERED' после пробного периода - нарушение лицензии Shareware."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №22-М", "department": "Дизайн", "software": "Adobe Photoshop (1 лицензия)", "desc": "Купили одну лицензию и установили на 15 компьютеров в отделе.", "ans": "Нарушение", "hint": "Нарушение условий тиражирования. 1 лицензия = 1 ПК (как правило)."},
            {"doc_type": "ЗАЯВКА НА ИСПОЛЬЗОВАНИЕ ПО №23-Н", "department": "Сисадмины", "software": "Total Commander", "desc": "При запуске нужно нажать цифру 1, 2 или 3. Пользуемся бесплатно уже 5 лет.", "ans": "Нарушение", "hint": "Классический пример Shareware (Nagware). По истечении месяца ПО нужно купить."}
        ]
        return jsonify(random.choice(tasks))
        
    elif level == 2:
        tasks = [
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-12", "plaintiff": "Программист Иванов", "defendant": "Программист Петров", "essence": "Истец описал алгоритм в журнале. Ответчик написал по нему программу. Истец подал в суд за кражу ИС.", "is_violation": False, "hint": "Согласно ст. 1259 ГК РФ, алгоритмы и идеи не охраняются авторским правом."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-15", "plaintiff": "ООО 'Игровая Студия'", "defendant": "Студент Смирнов", "essence": "Студент написал игру, не зарегистрировав её в Роспатенте. ООО начало продавать игру, заявив, что права свободны.", "is_violation": True, "hint": "Авторское право возникает по факту создания кода. Регистрация добровольна."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-18", "plaintiff": "Корпорация 'ОфисСофт'", "defendant": "Школа №123", "essence": "Школа купила 1 лицензию офиса и установила на 20 ПК, сославшись на образовательные цели.", "is_violation": True, "hint": "Установка одной лицензии на 20 ПК - тиражирование. Образовательные цели не отменяют договор."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-21", "plaintiff": "Студентка Сидорова", "defendant": "Учитель", "essence": "Учитель включил код из дипломной работы ученицы в свое платное приложение без ее ведома.", "is_violation": True, "hint": "Программа ученика - объект его авторского права. Использование без согласия запрещено."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-24", "plaintiff": "ЗАО 'СофтПром'", "defendant": "ООО 'Аналитика'", "essence": "Ответчик декомпилировал купленную программу для изучения её структуры в обход запрета в договоре.", "is_violation": True, "hint": "Изучение алгоритма путем декомпиляции при прямом запрете - нарушение договора."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-27", "plaintiff": "ООО 'Шутер'", "defendant": "ООО 'Экшен'", "essence": "Ответчик выпустил игру в том же жанре (стрелялка от первого лица), с похожей механикой прыжков и стрельбы.", "is_violation": False, "hint": "Жанры, механики и идеи не защищаются авторским правом. Главное - чтобы код и графика не были скопированы."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-30", "plaintiff": "Программист Васечкин", "defendant": "Переводчик Джонс", "essence": "Джонс перевел интерфейс программы Васечкина на английский язык и продает её за рубежом без разрешения.", "is_violation": True, "hint": "Перевод программы является производным произведением. Для его создания нужно согласие автора оригинала."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-33", "plaintiff": "Создатель языка Python", "defendant": "Банк 'Инвест'", "essence": "Банк написал свою внутреннюю финансовую систему на Python и не заплатил создателю языка.", "is_violation": False, "hint": "Языки программирования не охраняются авторским правом (ст. 1259 ГК РФ)."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-36", "plaintiff": "IT-Компания", "defendant": "Бывший сотрудник", "essence": "Сотрудник в рабочее время по заданию начальника написал программу. Уволившись, он забрал код и продает его.", "is_violation": True, "hint": "Это 'служебное произведение' (ст. 1295 ГК РФ). Исключительное право принадлежит работодателю."},
            {"doc_type": "МАТЕРИАЛЫ ДЕЛА № 2026/АП-39", "plaintiff": "IT-Компания", "defendant": "Сотрудник", "essence": "Сотрудник дома, в выходной, на личном ПК написал мобильную игру. Компания требует отдать права, так как он у них работает.", "is_violation": False, "hint": "Программа создана не в рамках служебных обязанностей. Права принадлежат автору-сотруднику."}
        ]
        return jsonify(random.choice(tasks))
        
    elif level == 3:
        tasks = [
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/01", "target": "Сайт школы №5", "audit_result": "На сайте опубликован список учеников с их оценками и домашними адресами. Согласий родителей нет.", "is_violation": True, "hint": "Распространение ПД требует согласия."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/05", "target": "БЦ 'Альфа'", "audit_result": "Внедрена система распознавания лиц. У всех сотрудников есть бумажные согласия на биометрию.", "is_violation": False, "hint": "Биометрия требует письменного согласия. Оно получено."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/09", "target": "Магазин 'Шопоголик'", "audit_result": "При заказе галочка 'Согласен на рекламную рассылку' проставлена по умолчанию.", "is_violation": True, "hint": "Предустановленные галочки (opt-out) запрещены, согласие должно быть активным."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/12", "target": "Больница", "audit_result": "В реанимации пациенту без сознания оказывалась помощь, данные о здоровье занесены в базу без согласия.", "is_violation": False, "hint": "Медицинская помощь в экстренных случаях допускает обработку спец. ПД без согласия."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/16", "target": "Приложение 'Фонарик'", "audit_result": "Приложение требует доступ к GPS и Контактам, иначе не работает.", "is_violation": True, "hint": "Нарушение принципа целеполагания. Данные избыточны для фонарика."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/20", "target": "Соцсеть 'VK'", "audit_result": "Выяснилось, что базы ПД российских пользователей хранятся на серверах в Мюнхене.", "is_violation": True, "hint": "Нарушение локализации. ПД граждан РФ должны быть на серверах в РФ."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/23", "target": "ООО 'Ромашка'", "audit_result": "В отделе кадров в личных делах хранятся копии паспортов и свидетельств о браке уволенных 5 лет назад сотрудников.", "is_violation": True, "hint": "Нарушение сроков хранения. После увольнения избыточные копии должны уничтожаться."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/26", "target": "Сайт интернет-магазина", "audit_result": "Форма сбора email для рассылки находится на сайте. Политика конфиденциальности опубликована в подвале сайта.", "is_violation": False, "hint": "Публикация Политики обработки ПД на сайте обязательна. Нарушения нет."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/29", "target": "Турагентство", "audit_result": "Сотрудник переслал скан паспорта клиента в отель Турции через WhatsApp без шифрования.", "is_violation": True, "hint": "Трансграничная передача ПД требует обеспечения безопасности и шифрования."},
            {"doc_type": "ПРОТОКОЛ ПРОВЕРКИ № 152/32", "target": "Фитнес-клуб", "audit_result": "При покупке абонемента требуют указать национальность и вероисповедание.", "is_violation": True, "hint": "Нарушение избыточности. Эти данные не нужны для оказания фитнес-услуг."}
        ]
        return jsonify(random.choice(tasks))

@app.route('/api/networks_task', methods=['POST'])
def api_networks_task():
    if 'student_name' not in session: return jsonify({"error": "No session"})

    data = request.json
    level = data.get('level', 1)
    
    if level == 1:
        from logic import generate_network_l1_task
        return jsonify(generate_network_l1_task())
    elif level == 2:
        from logic import generate_network_l2_task
        return jsonify(generate_network_l2_task())
    elif level == 3:
        import random
        scenario = random.randint(1, 4)
        
        target_ip = f"{random.randint(8, 200)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
        local_ip = f"192.168.1.{random.randint(2, 254)}"
        gateway = "192.168.1.1"
        
        if scenario == 1:
            hops = [gateway]
            for i in range(4):
                hops.append(f"{random.randint(10, 200)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 254)}")
            broken_idx = random.randint(1, 3)
            return jsonify({
                "scenario": 1,
                "target_ip": target_ip, "local_ip": local_ip, "gateway": gateway,
                "hops": hops, "broken_idx": broken_idx,
                "ans": hops[broken_idx],
                "task_text": f"Пользователи жалуются на недоступность сервера <strong class='text-info'>{target_ip}</strong>. Используя утилиту <code>tracert</code>, определите IP-адрес последнего доступного шлюза (узла) перед обрывом маршрута.",
                "hint": f"Введите tracert {target_ip} и посмотрите, какой IP-адрес был на строке ПЕРЕД первой строкой с 'Превышен интервал ожидания'."
            })
            
        elif scenario == 2:
            return jsonify({
                "scenario": 2,
                "target_ip": target_ip, "local_ip": local_ip, "gateway": gateway,
                "ans": gateway,
                "task_text": "Пропал доступ к интернету. Первым делом нужно проверить доступность вашего локального маршрутизатора (Основного шлюза). Узнайте его IP-адрес с помощью <code>ipconfig</code> и введите в качестве ответа.",
                "hint": "Введите ipconfig. Найдите строку 'Основной шлюз'. Это и есть ответ."
            })
            
        elif scenario == 3:
            return jsonify({
                "scenario": 3,
                "target_ip": target_ip, "local_ip": local_ip, "gateway": gateway,
                "ans": local_ip,
                "task_text": "Системный администратор просит вас сообщить ваш локальный IP-адрес для настройки удаленного доступа. Узнайте свой IPv4-адрес через консоль и введите его.",
                "hint": "Введите ipconfig. Найдите строку 'IPv4-адрес'."
            })
            
        elif scenario == 4:
            domains = ["google.com", "yandex.ru", "vk.com", "sch.edu"]
            domain = random.choice(domains)
            return jsonify({
                "scenario": 4,
                "target_ip": target_ip, "local_ip": local_ip, "gateway": gateway,
                "domain": domain,
                "ans": target_ip,
                "task_text": f"Сайт <strong class='text-info'>{domain}</strong> не открывается в браузере. Возможно проблема в DNS. Отправьте <code>ping {domain}</code> и выясните, в какой IP-адрес он разрешается сервером.",
                "hint": f"Напишите ping {domain}. В первой же строке будет написано 'Обмен пакетами с {domain} [IP-АДРЕС]'. Введите этот IP."
            })

if __name__ == '__main__':
    from waitress import serve
    print("=====================================================")
    print("🚀 M.A.S.T.E.R. Server is running (Production Mode)")
    print("🌐 Open http://localhost:5000 in your browser.")
    print("🛑 Press CTRL+C to stop the server.")
    print("=====================================================")
    serve(app, host='0.0.0.0', port=5000, threads=16)

@app.route('/lesson/generic/<grade>/<lesson_id>')
def generic_lesson_route(grade, lesson_id):
    if 'student_name' not in session: return redirect('/')
    lesson = next((l for l in lessons_index.get(grade, []) if str(l['id']) == str(lesson_id)), None)
    if not lesson:
        return "Урок не найден", 404
        
    custom_templates = {
        '11-tech_9': 'codes11.html',
        '11-tech_10': 'lesson10.html',
        '10-tech_12': 'law10.html',
        '10-tech_13': 'networks10.html',
        '8_4': 'octal.html'
    }
    key = f"{grade}_{lesson_id}"
    template_name = custom_templates.get(key, 'generic_lesson.html')
    
    log_action(session['student_name'], f"Открыл Урок {lesson_id} ({grade}): {lesson['theme']}")
    
    # --- Custom Initialization Logic ---
    kwargs = {'lesson': lesson}
    
    if template_name == 'codes11.html':
        data0 = generate_random_bits(4)
        encoded0 = add_parity_bit(data0)
        has_error = random.choice([True, False])
        task0_bits = introduce_noise(encoded0, 1) if has_error else encoded0
        session['m0_task'] = task0_bits
        session['m0_has_error'] = has_error
        
        data_bit1 = generate_random_bits(1)
        encoded1 = repetition_encode(data_bit1)
        noisy1 = introduce_noise(encoded1, 1)
        session['m1_task'] = noisy1
        session['m1_answer'] = data_bit1[0]
        
        data2 = generate_random_bits(4)
        encoded2 = hamming_encode(data2)
        noisy2 = introduce_noise(encoded2, 1)
        syndrome2, _ = calculate_syndrome(noisy2)
        session['m2_task'] = noisy2
        session['m2_syndrome'] = syndrome2
        
        kwargs.update({
            'm0_task': task0_bits, 'm0_correct': session.get('m0_correct', 0),
            'm1_task': noisy1, 'm1_correct': session.get('m1_correct', 0),
            'm2_task': noisy2, 'm2_correct': session.get('m2_correct', 0)
        })
        
    elif template_name == 'law10.html':
        incidents = generate_law_incidents()
        session['law_incidents'] = incidents
        kwargs['incidents_json'] = json.dumps(incidents)
        
    elif template_name == 'octal.html':
        lvl1_dec = random.randint(50, 300)
        session['octal_lvl1_ans'] = oct(lvl1_dec)[2:]
        
        lvl2_oct = oct(random.randint(64, 511))[2:] # 3 octal digits
        lvl2_bin = bin(int(lvl2_oct, 8))[2:]
        session['octal_lvl2_ans'] = lvl2_oct
        
        triads = [random.randint(0, 7) for _ in range(3)]
        bin_str = "".join([bin(t)[2:].zfill(3) for t in triads])
        bug_index = random.randint(0, 2)
        wrong_digit = (triads[bug_index] + random.randint(1, 6)) % 8
        fake_octal = list(map(str, triads))
        fake_octal[bug_index] = str(wrong_digit)
        fake_octal_str = "".join(fake_octal)
        
        session['octal_lvl3_ans'] = str(triads[bug_index])
        
        kwargs.update({
            'lvl1_dec': lvl1_dec, 
            'lvl2_bin': lvl2_bin,
            'lvl3_bin': bin_str,
            'lvl3_fake': fake_octal_str
        })
        
    # lesson10.html and networks10.html don't require server-side generated jinja kwargs, they use pure API
        
    return render_template(template_name, **kwargs)

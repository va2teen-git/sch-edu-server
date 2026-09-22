import sys
import os
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from logic import generate_random_bits, repetition_encode, introduce_noise, repetition_decode, hamming_encode, calculate_syndrome, add_parity_bit
from datetime import datetime
import random

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

app.secret_key = 'super_secret_key_123'
db_path = os.path.join(os.getcwd(), 'hamming_logs.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

db = SQLAlchemy(app)

class LogEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

def log_action(name, action_text):
    if name != '#учитель#':
        new_log = LogEvent(student_name=name, action=action_text)
        db.session.add(new_log)
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('student_name', '').strip()
        if not name:
            return render_template('login.html', error="Имя не может быть пустым")
        
        session['student_name'] = name
        
        if name == '#учитель#':
            return redirect('/teacher')
            
        log_action(name, "--- ВОШЕЛ В СИСТЕМУ ---")
        session['m1_correct'] = 0
        session['m2_correct'] = 0
        return redirect('/menu')
        
    return render_template('login.html')

@app.route('/menu')
def menu():
    if 'student_name' not in session: return redirect('/')
    return render_template('menu.html', name=session['student_name'])

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
        
    logs = LogEvent.query.order_by(LogEvent.timestamp.desc()).all()
    
    students = {}
    for log in logs:
        if log.student_name not in students:
            students[log.student_name] = []
        students[log.student_name].append(log)
        
    return render_template('teacher.html', students=students)

@app.route('/lesson/grade8/octal')
def lesson_octal():
    if 'student_name' not in session: return redirect('/')
    
    decimal_number = random.randint(100, 500)
    octal_answer = oct(decimal_number)[2:]
    
    session['octal_task_decimal'] = decimal_number
    session['octal_task_answer'] = octal_answer
    
    return render_template('octal.html', decimal_number=decimal_number)

@app.route('/check_octal', methods=['POST'])
def check_octal():
    if 'student_name' not in session: return jsonify({"error": "No session"})
    
    user_answer = request.json.get('answer', '')
    correct_answer = session.get('octal_task_answer', '')
    
    if str(user_answer).strip() == str(correct_answer):
        log_action(session['student_name'], f"Урок 8кл (Восьмеричная): [ВЕРНО] Перевел {session.get('octal_task_decimal')} в {correct_answer}.")
        return jsonify({"success": True, "msg": "Доступ разрешен! Сейф открыт."})
    else:
        log_action(session['student_name'], f"Урок 8кл (Восьмеричная): [ОШИБКА] Ввел {user_answer} вместо {correct_answer} для {session.get('octal_task_decimal')}.")
        return jsonify({"success": False, "msg": "Ошибка! Код не подходит."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

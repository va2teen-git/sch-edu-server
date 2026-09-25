import re
import traceback

file_path = r'D:\sch-edu-server\templates\lesson10.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Tab 1
    t1_regex = r'(<!-- Задание 1 -->\s*<div class="tab-pane fade show active" id="t1">)\s*(<div class="card cyber-box p-4 border-info">[\s\S]*?<h4 class="text-info mb-3">([^<]+)</h4>\s*<p class="small text-muted">([^<]+)</p>)'
    def repl_t1(m):
        return f"""{m.group(1)}
                <div id="lvl1-intro" class="text-center mt-4">
                    <h4 class="text-warning">{m.group(3)}</h4>
                    <p class="text-muted">{m.group(4)} Необходимо выполнить 3 раза.</p>
                    <button class="btn btn-outline-warning mt-3" style="border-radius: 0; font-size: 1.2rem;" onclick="startTask('М1 (Ящики)', 'lvl1-intro', 'lvl1-workspace')">НАЧАТЬ ЗАДАНИЕ</button>
                </div>
                <div id="lvl1-workspace" style="display: none;">
                {m.group(2)}"""
    content = re.sub(t1_regex, repl_t1, content)
    content = re.sub(r'(<div id="res1" class="mt-2 fw-bold text-center"></div>\s*</div>)\s*</div>', r'\1\n                </div>\n            </div>', content)

    # Tab 2
    t2_regex = r'(<!-- Задание 2 -->\s*<div class="tab-pane fade" id="t2">)\s*(<div class="card cyber-box p-4 border-warning">[\s\S]*?<h4 class="text-warning mb-3">([^<]+)</h4>\s*<p class="small text-muted">([^<]+)</p>)'
    def repl_t2(m):
        return f"""{m.group(1)}
                <div id="lvl2-intro" class="text-center mt-4">
                    <h4 class="text-warning">{m.group(3)}</h4>
                    <p class="text-muted">{m.group(4)} Необходимо выполнить 5 раз.</p>
                    <button class="btn btn-outline-warning mt-3" style="border-radius: 0; font-size: 1.2rem;" onclick="startTask('М2 (Баланс ОС)', 'lvl2-intro', 'lvl2-workspace')">НАЧАТЬ ЗАДАНИЕ</button>
                </div>
                <div id="lvl2-workspace" style="display: none;">
                {m.group(2)}"""
    content = re.sub(t2_regex, repl_t2, content)
    content = re.sub(r'(<div id="res2" class="mt-2 fw-bold text-center text-muted">[^<]+</div>\s*</div>)\s*</div>', r'\1\n                </div>\n            </div>', content)

    # Tab 3
    t3_regex = r'(<!-- Задание 3 -->\s*<div class="tab-pane fade" id="t3">)\s*(<div class="card cyber-box p-4 border-success">[\s\S]*?<h4 class="text-success mb-3">([^<]+)</h4>\s*<p class="small text-muted">([^<]+)</p>)'
    def repl_t3(m):
        return f"""{m.group(1)}
                <div id="lvl3-intro" class="text-center mt-4">
                    <h4 class="text-warning">{m.group(3)}</h4>
                    <p class="text-muted">{m.group(4)} Необходимо выполнить 8 раз.</p>
                    <button class="btn btn-outline-warning mt-3" style="border-radius: 0; font-size: 1.2rem;" onclick="startTask('М3 (TCP)', 'lvl3-intro', 'lvl3-workspace')">НАЧАТЬ ЗАДАНИЕ</button>
                </div>
                <div id="lvl3-workspace" style="display: none;">
                {m.group(2)}"""
    content = re.sub(t3_regex, repl_t3, content)
    content = re.sub(r'(<div id="res3" class="mt-2 fw-bold text-center"></div>\s*</div>)\s*</div>', r'\1\n                </div>\n            </div>', content)

    telemetry_old = r'// --- ТЕЛЕМЕТРИЯ ---[\s\S]*?// --- МИССИЯ 1 \(ЧЕРНЫЕ ЯЩИКИ\) ---'
    
    telemetry_new = '''// =======================================================
    // СТАНДАРТ ТЕЛЕМЕТРИИ
    // =======================================================
    const LESSON_NAME = "Теория систем (11 кл)";
    const taskNames = ['М1 (Ящики)', 'М2 (Баланс ОС)', 'М3 (TCP)'];
    
    const startTimes = {};
    const attemptsCount = {};
    const actionLogs = {};
    
    taskNames.forEach(t => {
        startTimes[t] = null;
        attemptsCount[t] = 0;
        actionLogs[t] = [];
    });

    function startTask(task, introId, workspaceId) {
        document.getElementById(introId).style.display = 'none';
        document.getElementById(workspaceId).style.display = 'block';
        
        startTimes[task] = new Date();
        attemptsCount[task] = 0;
        actionLogs[task] = [];
        
        sendTelemetry(task, 'in_progress');
    }

    function logAction(task, action, success) {
        if (!startTimes[task]) return;
        attemptsCount[task]++;
        actionLogs[task].push({ time: new Date().toISOString(), input: action, success: success });
        sendTelemetry(task, 'in_progress');
    }

    function sendTelemetry(task, status = 'completed') {
        const timeSpent = Math.floor((new Date() - startTimes[task]) / 1000);
        
        fetch('/telemetry', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                mission_name: `${LESSON_NAME} :: ${task}`,
                start_time: startTimes[task].toISOString(),
                time_spent_sec: timeSpent,
                attempts_count: attemptsCount[task],
                success: (status === 'completed'),
                action_log: JSON.stringify(actionLogs[task]),
                status: status
            })
        });
        
        if (status === 'completed') {
            startTimes[task] = new Date();
            attemptsCount[task] = 0;
            actionLogs[task] = [];
        }
    }

    // --- МИССИЯ 1 (ЧЕРНЫЕ ЯЩИКИ) ---'''

    content = re.sub(telemetry_old, telemetry_new, content)

    # Clean border-radius
    content = re.sub(r'border-radius:\s*[^;]+;', 'border-radius: 0 !important;', content)
    
    content = content.replace("sendTel('М1 (Ящики)', true)", "sendTelemetry('М1 (Ящики)', 'completed')")
    content = content.replace("sendTel('М1 (Ящики)', false)", "sendTelemetry('М1 (Ящики)', 'failed')")
    content = content.replace("sendTel('М2 (Баланс ОС)', true)", "sendTelemetry('М2 (Баланс ОС)', 'completed')")
    content = content.replace("sendTel('М2 (Баланс ОС)', false)", "sendTelemetry('М2 (Баланс ОС)', 'failed')")
    content = content.replace("sendTel('М3 (TCP)', true)", "sendTelemetry('М3 (TCP)', 'completed')")
    content = content.replace("sendTel('М3 (TCP)', false)", "sendTelemetry('М3 (TCP)', 'failed')")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done")
except Exception as e:
    traceback.print_exc()

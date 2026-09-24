import random

def generate_random_bits(length):
    return [random.choice([0, 1]) for _ in range(length)]

# --- Parity Bit (Бит четности) ---
def calculate_parity(bits):
    """Calculates even parity bit"""
    return sum(bits) % 2

def add_parity_bit(bits):
    """Adds an even parity bit to the end of the bits list."""
    p = calculate_parity(bits)
    return bits + [p]

def check_parity(bits):
    """Returns True if there is no detectable error (even number of 1s)."""
    return sum(bits) % 2 == 0

# --- Repetition Code (Код с повторением x3) ---
def repetition_encode(bits):
    """Triples every bit."""
    encoded = []
    for b in bits:
        encoded.extend([b, b, b])
    return encoded

def repetition_decode(bits):
    """Decodes using majority vote."""
    decoded = []
    for i in range(0, len(bits), 3):
        chunk = bits[i:i+3]
        if sum(chunk) >= 2:
            decoded.append(1)
        else:
            decoded.append(0)
    return decoded

# --- Hamming Code (Код Хэмминга 7, 4) ---
# Информационные биты: d1, d2, d3, d4 (позиции 3, 5, 6, 7)
# Проверочные биты: p1, p2, p3 (позиции 1, 2, 4)
def hamming_encode(data_bits):
    """Encodes 4 bits of data into 7 bits of Hamming code (even parity)."""
    if len(data_bits) != 4:
        raise ValueError("Data must be exactly 4 bits long.")
    
    # p1 проверяет 1, 3, 5, 7
    p1 = (data_bits[0] + data_bits[1] + data_bits[3]) % 2
    # p2 проверяет 2, 3, 6, 7
    p2 = (data_bits[0] + data_bits[2] + data_bits[3]) % 2
    # p3 проверяет 4, 5, 6, 7
    p3 = (data_bits[1] + data_bits[2] + data_bits[3]) % 2
    
    # Формат: p1, p2, d1, p3, d2, d3, d4
    # Позиции: 1,  2,  3,  4,  5,  6,  7
    return [p1, p2, data_bits[0], p3, data_bits[1], data_bits[2], data_bits[3]]

def calculate_syndrome(hamming_bits):
    """Calculates syndrome for 7-bit Hamming code. Returns (integer_syndrome, [s3, s2, s1])."""
    s1 = (hamming_bits[0] + hamming_bits[2] + hamming_bits[4] + hamming_bits[6]) % 2
    s2 = (hamming_bits[1] + hamming_bits[2] + hamming_bits[5] + hamming_bits[6]) % 2
    s3 = (hamming_bits[3] + hamming_bits[4] + hamming_bits[5] + hamming_bits[6]) % 2
    
    syndrome = s3 * 4 + s2 * 2 + s1 * 1
    return syndrome, [s3, s2, s1]

def hamming_decode(hamming_bits):
    """
    Decodes Hamming code. 
    Returns:
    - corrected_bits: 7 bits with error fixed
    - syndrome: integer position of error (0 if no error)
    - data: 4 original data bits extracted
    """
    syndrome, _ = calculate_syndrome(hamming_bits)
    corrected_bits = list(hamming_bits)
    
    if syndrome != 0:
        idx = syndrome - 1 # Array is 0-indexed, positions are 1-indexed
        corrected_bits[idx] = 1 - corrected_bits[idx]
        
    data = [corrected_bits[2], corrected_bits[4], corrected_bits[5], corrected_bits[6]]
    return corrected_bits, syndrome, data

def introduce_noise(bits, num_errors=1):
    """Flips a given number of random bits to simulate noise."""
    noisy = list(bits)
    positions = random.sample(range(len(bits)), num_errors)
    for pos in positions:
        noisy[pos] = 1 - noisy[pos]
    return noisy


# --- Law & Compliance (Урок 10 класс) ---
def generate_law_incidents():
    import random
    
    apps = ['WordProcessor', 'GraphicEditor', 'CodeIDE', 'DatabaseManager', '3DEngine', 'VideoEditor']
    licenses = ['GPLv3', 'MIT', 'Apache 2.0', 'Commercial', 'Freeware', 'Shareware']
    
    incidents = []
    
    num_incidents = random.randint(15, 20)
    for i in range(num_incidents):
        incident_type = random.choice(['software', 'data'])
        
        if incident_type == 'software':
            app = random.choice(apps) + str(random.randint(2020, 2026))
            lic = random.choice(licenses)
            
            actions = ['installed_free', 'modified_and_sold_closed_source', 'expired_trial', 'paid_subscription']
            action = random.choice(actions)
            
            incidents.append({
                'id': i,
                'type': 'software',
                'app': app,
                'license': lic,
                'action': action
            })
            
        else:
            data_types = ['email', 'phone', 'biometric', 'passport']
            d_type = random.choice(data_types)
            consent = random.choice([True, False])
            
            incidents.append({
                'id': i,
                'type': 'data',
                'data_type': d_type,
                'user_consent': consent
            })
            
    return incidents

# --- Networks & Protocols (Урок 10 класс) ---
def generate_network_l1_task():
    import random
    
    difficulty = random.randint(1, 3)
    
    devices = [
        {"id": "inet", "name": "Провайдер", "type": "internet", "x": 50, "y": 10},
        {"id": "router", "name": "Маршрутизатор", "type": "router", "x": 50, "y": 40}
    ]
    edges = [["inet", "router"]]
    
    if difficulty <= 2:
        devices.append({"id": "sw1", "name": "Коммутатор", "type": "switch", "x": 50, "y": 70})
        edges.append(["router", "sw1"])
        
        num_pcs = random.randint(2, 4)
        for i in range(num_pcs):
            devices.append({"id": f"pc{i}", "name": f"ПК {i+1}", "type": "pc", "x": 20 + i*20, "y": 100})
            edges.append(["sw1", f"pc{i}"])
            
        if difficulty == 2:
            devices.append({"id": "pr1", "name": "Принтер", "type": "printer", "x": 80, "y": 100})
            edges.append(["sw1", "pr1"])
            
    else:
        devices.append({"id": "sw1", "name": "Коммутатор 1", "type": "switch", "x": 25, "y": 70})
        devices.append({"id": "sw2", "name": "Коммутатор 2", "type": "switch", "x": 75, "y": 70})
        edges.append(["router", "sw1"])
        edges.append(["router", "sw2"])
        
        devices.append({"id": "pc1", "name": "ПК 1", "type": "pc", "x": 15, "y": 100})
        devices.append({"id": "pc2", "name": "ПК 2", "type": "pc", "x": 35, "y": 100})
        edges.append(["sw1", "pc1"])
        edges.append(["sw1", "pc2"])
        
        devices.append({"id": "pc3", "name": "ПК 3", "type": "pc", "x": 75, "y": 100})
        edges.append(["sw2", "pc3"])
        
    random.shuffle(devices)
    
    return {
        "devices": devices,
        "edges": edges,
        "hint": "Провайдер подключается к Маршрутизатору. Маршрутизатор к Коммутатору. А уже к Коммутатору подключаются все ПК и принтеры в одной сети."
    }

def generate_network_l2_task():
    import random
    base_ip = f"192.168.{random.randint(1, 10)}"
    ip_src = f"{base_ip}.{random.randint(10, 50)}"
    is_local = random.choice([True, False])
    if is_local:
        ip_dst = f"{base_ip}.{random.randint(51, 100)}"
        ans = "Локально"
    else:
        ip_dst = f"192.168.{random.randint(11, 20)}.{random.randint(10, 50)}"
        ans = "Шлюз"
    return {
        "ip_src": ip_src,
        "mask": "255.255.255.0",
        "ip_dst": ip_dst,
        "ans": ans,
        "hint": "Маска 255.255.255.0 означает, что первые 3 числа (октета) должны совпадать, чтобы узлы были в одной сети. Иначе - пакет идет через шлюз."
    }

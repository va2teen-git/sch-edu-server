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

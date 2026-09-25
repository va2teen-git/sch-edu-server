import pandas as pd
import glob
import json
import os
import math

file_to_grade = {
    '2026-2027_7 класс_информатика_Ватутин.xlsx': '7',
    '2026-2027_8 класс_информатика_Ватутин.xlsx': '8',
    '2026-2027_9 класс_информатика_Ватутин.xlsx': '9',
    '2026-2027_10 класс_базовый_информатика_Ватутин.xlsx': '10-gum',
    '2026-2027_10 класс_углубленный_информатика_Ватутин.xlsx': '10-tech',
    '2026-2027_11 класс_базовый_информатика_Ватутин.xlsx': '11-gum',
    '2026-2027_11 класс_углубленный_информатика_Ватутин.xlsx': '11-tech',
}

lessons_index = {}

for filepath in glob.glob('wp/*.xlsx'):
    filename = os.path.basename(filepath)
    if filename not in file_to_grade:
        continue
    
    grade_key = file_to_grade[filename]
    df = pd.read_excel(filepath)
    
    lessons = []
    
    for idx, row in df.iterrows():
        lesson_num_val = row['№']
        
        if pd.isna(lesson_num_val):
            continue
            
        try:
            lesson_num = int(float(lesson_num_val))
        except ValueError:
            lesson_num = str(lesson_num_val).strip()
            
        theme = str(row['Тема']).strip()
        lesson_type = str(row['Тип']).strip() if 'Тип' in df.columns and not pd.isna(row['Тип']) else 'Урок'
        
        # All lessons go through the generic route now
        route = f'/lesson/generic/{grade_key}/{lesson_num}'
            
        lessons.append({
            'id': str(lesson_num),
            'type': lesson_type,
            'theme': theme,
            'route': route
        })
        
    lessons_index[grade_key] = lessons

with open('lessons_index.json', 'w', encoding='utf-8') as f:
    json.dump(lessons_index, f, ensure_ascii=False, indent=2)

print("lessons_index.json updated with generic routes for ALL lessons.")

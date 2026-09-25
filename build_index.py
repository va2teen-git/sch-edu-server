import pandas as pd
import glob
import json
import os
import math

# Mapping of file names to grade keys used in session['grade']
# grade_map = {'7': '7', '8': '8', '9': '9', '10-gum': '10 Гум', '10-tech': '10 Тех', '11-gum': '11 Гум', '11-tech': '11 Тех'}
# Let's map filename -> grade key
file_to_grade = {
    '2026-2027_7 класс_информатика_Ватутин.xlsx': '7',
    '2026-2027_8 класс_информатика_Ватутин.xlsx': '8',
    '2026-2027_9 класс_информатика_Ватутин.xlsx': '9',
    '2026-2027_10 класс_базовый_информатика_Ватутин.xlsx': '10-gum',
    '2026-2027_10 класс_углубленный_информатика_Ватутин.xlsx': '10-tech',
    '2026-2027_11 класс_базовый_информатика_Ватутин.xlsx': '11-gum',
    '2026-2027_11 класс_углубленный_информатика_Ватутин.xlsx': '11-tech',
}

# Known custom routes mapping
# grade -> { lesson_number: custom_route }
custom_routes = {
    '11-tech': {
        9: '/lesson/grade11/codes',
        10: '/lesson/grade11/systems'
    },
    '10-tech': {
        12: '/lesson/grade10/law',
        13: '/lesson/grade10/networks'
    },
    '8': {
        4: '/lesson/grade8/octal'
    }
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
        
        # Handle cases where № might be NaN or strings like '1-2'
        if pd.isna(lesson_num_val):
            continue
            
        try:
            lesson_num = int(float(lesson_num_val))
        except ValueError:
            # If it's a string like '1-2', we can just use it as string, 
            # but let's parse the first number or just use the string.
            # We'll use string as ID, but for custom routing we need to match it.
            lesson_num = str(lesson_num_val).strip()
            
        theme = str(row['Тема']).strip()
        lesson_type = str(row['Тип']).strip() if 'Тип' in df.columns and not pd.isna(row['Тип']) else 'Урок'
        
        route = custom_routes.get(grade_key, {}).get(lesson_num if isinstance(lesson_num, int) else None)
        if not route:
            # Check if we can parse it as int
            try:
                num_int = int(str(lesson_num).split('-')[0])
                route = custom_routes.get(grade_key, {}).get(num_int)
            except:
                pass
                
        if not route:
            # Generic route
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

print("lessons_index.json created successfully with", sum(len(l) for l in lessons_index.values()), "total lessons.")

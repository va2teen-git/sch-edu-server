import glob
import re

for f in glob.glob('D:/sch-edu-server/templates/*.html'):
    content = open(f, encoding='utf-8').read()
    matches = re.findall(r'class="[^"]*col-[^"]*"', content)
    if matches:
        print(f, matches)

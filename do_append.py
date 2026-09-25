import os

with open('D:/sch-edu-server/scratch_append_tests.py', 'r', encoding='utf-8') as f:
    new_tests = f.read()

with open('D:/sch-edu-server/tests/test_backend.py', 'a', encoding='utf-8') as f:
    f.write("\n" + new_tests)

print("Tests appended!")

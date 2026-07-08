"""BBLOTTO PRO release verification helper.
Run: python scripts/verify_release.py
"""
from pathlib import Path
import ast
import sys

BASE = Path(__file__).resolve().parents[1]
REQUIRED = [
    'start.py', 'requirements.txt', 'runtime.txt', 'railway.json', 'Dockerfile',
    'backend/app.py', 'frontend/index.html', 'frontend/app.js', 'frontend/style.css', '.env.example', '.gitignore'
]
errors = []
for rel in REQUIRED:
    if not (BASE / rel).exists():
        errors.append(f'missing: {rel}')

for py in BASE.rglob('*.py'):
    if any(part in {'__pycache__', '.venv', 'venv'} for part in py.parts):
        continue
    try:
        ast.parse(py.read_text(encoding='utf-8'), filename=str(py))
    except Exception as exc:
        errors.append(f'python syntax: {py.relative_to(BASE)} -> {exc}')

bad = []
for p in BASE.rglob('*'):
    if p.is_file() and (p.suffix in {'.pyc', '.pyo', '.tmp'} or p.name == '.env'):
        bad.append(str(p.relative_to(BASE)))
if bad:
    errors.append('blocked files: ' + ', '.join(bad[:20]))

if errors:
    print('[BBLOTTO VERIFY] FAIL')
    for e in errors:
        print('-', e)
    sys.exit(1)
print('[BBLOTTO VERIFY] OK - release package looks ready')

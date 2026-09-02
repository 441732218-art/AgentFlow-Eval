import os
root = r'D:\AgentFlow-Eval'
exclude = {'node_modules','.git','.venv','.pytest_cache','.ruff_cache','__pycache__'}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in exclude]
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        ext = fn.lower().rsplit('.',1)[-1] if '.' in fn else ''
        if ext not in ('html','md','py','txt','json','js','ts','pyc'): continue
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except: continue
        if 'V1.0' in content:
            for i, l in enumerate(content.split('\n')):
                if 'V1.0' in l and 'V1.0' in l:
                    print(f'{fp}:{i+1}: {l.strip()[:150]}')

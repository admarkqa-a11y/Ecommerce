from pathlib import Path
root=Path(__file__).resolve().parents[1]
for directory in [root/'backend/apps',root/'apps',root/'packages']:
    for p in directory.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in ['node_modules','.next','__pycache__','migrations']):continue
        if p.suffix not in ['.py','.ts','.tsx','.css','.json']:continue
        text=p.read_text(errors='replace')
        for literal in ['World Games','Vertex','demo-electric','97400000001','97400000002']:
            if literal in text:raise SystemExit(f'Client literal {literal!r} in {p.relative_to(root)}')
print('No known demonstration client identifiers in core application source.')

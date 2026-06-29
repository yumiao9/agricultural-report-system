import ssl, urllib.request, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

data = json.dumps({'query': '新疆棉花'}).encode()
req = urllib.request.Request('https://agricultural-report-system.vercel.app/api/research', data=data, method='POST', headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req, context=ctx, timeout=20)
t = json.loads(resp.read())
tid = t['task_id']
print(f'Task: {tid}')

results = {}
steps = [
    ('step-classify', '分类'),
    ('step-search', '搜索'),
    ('step-fetch', '抓取'),
    ('step-extract', '提取'),
    ('step-generate', '生成'),
]
for step, label in steps:
    r = urllib.request.Request(f'https://agricultural-report-system.vercel.app/api/research/{tid}/{step}', method='POST')
    resp = urllib.request.urlopen(r, context=ctx, timeout=30)
    d = json.loads(resp.read())
    results[label] = d
    s = json.dumps(d, ensure_ascii=False)[:200]
    print(f'{label}: {s}')

r2 = urllib.request.urlopen(f'https://agricultural-report-system.vercel.app/api/reports/{tid}', context=ctx, timeout=20)
report = json.loads(r2.read())
print(f'\nData points: {report["data_points_count"]}')
print(f'Sources: {report["sources_count"]}')
md = report.get('markdown_content', '')
open('test_xj_report.txt', 'w', encoding='utf-8').write(md)
print(f'Report length: {len(md)} chars')
print('Report saved to test_xj_report.txt')

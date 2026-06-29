import ssl, urllib.request, json, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

data = json.dumps({'query': '牛油果'}).encode()
req = urllib.request.Request('https://agricultural-report-system.vercel.app/api/research', data=data, method='POST', headers={'Content-Type':'application/json'})
resp = urllib.request.urlopen(req, context=ctx, timeout=30)
t = json.loads(resp.read())
tid = t['task_id']
print(f'Task: {tid}')

for s in ['step-classify', 'step-search', 'step-fetch', 'step-extract', 'step-generate']:
    url = f'https://agricultural-report-system.vercel.app/api/research/{tid}/{s}'
    try:
        r = urllib.request.Request(url, method='POST')
        resp = urllib.request.urlopen(r, context=ctx, timeout=25)
        d = json.loads(resp.read())
        print(f'{s}: status={d.get("status","?")}', end='')
        if 'count' in d: print(f', count={d["count"]}', end='')
        if 'entity_type' in d: print(f', type={d["entity_type"]}', end='')
        print()
    except Exception as e:
        print(f'{s}: ERROR {str(e)[:80]}')

# Check final report
try:
    resp = urllib.request.urlopen(f'https://agricultural-report-system.vercel.app/report/{tid}', context=ctx, timeout=30)
    html = resp.read().decode()
    if '数据概览' in html or '牛油果' in html:
        print('\nReport OK - contains content')
    else:
        print('\nReport generated but may be empty')
except Exception as e:
    print(f'\nReport error: {str(e)[:80]}')

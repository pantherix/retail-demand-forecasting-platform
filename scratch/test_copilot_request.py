import json, requests, sys
payload = {"query": "What should I order today?", "prompt": "What should I order today?", "settings": {}}
try:
    resp = requests.post('http://127.0.0.1:8000/api/enterprise/copilot/chat', json=payload)
    print('Status:', resp.status_code)
    print('Response:', resp.text)
except Exception as e:
    print('Error:', e)
    sys.exit(1)

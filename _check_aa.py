import requests, re
resp = requests.get('https://artificialanalysis.ai/leaderboards/models', timeout=30, headers={'User-Agent': 'InferenceIndexer/1.0'})
html = resp.text
# dump the field order around a fresh claude-opus-5 record
i = html.find('\\"slug\\":\\"claude-opus-5\\"')
print(repr(html[i:i+1200]))

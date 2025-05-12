import json

with open('../verbatims/contributions.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

for item in data:
    if item['user'] != 'Anonyme':
        item['user'] = 'Anonymisé'

with open('../verbatims/contributions-anonymisees.json', 'w+', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)
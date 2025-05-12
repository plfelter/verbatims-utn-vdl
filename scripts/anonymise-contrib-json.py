import json

with open('../verbatims/contributions.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

for item in data:
    if item['user'] != 'Anonyme':
        item['user'] = 'Anonymisé'

import pandas as pd
pd.DataFrame.from_dict(data).to_csv('../verbatims/contributions-anonymisees.csv', index=False)

# Write to JSON file
# with open('../verbatims/contributions-anonymisees.json', 'w+', encoding='utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=4)

# Write to JSONL file (one JSON object per line)
# with open('../verbatims/contributions-anonymisees.jsonl', 'w+', encoding='utf-8') as f:
#     if isinstance(data, list):
#         # If the JSON is an array of objects
#         for item in data:
#             f.write(json.dumps(item, ensure_ascii=False) + '\n')
#     else:
#         # If the JSON is a single object
#         f.write(json.dumps(data, ensure_ascii=False) + '\n')

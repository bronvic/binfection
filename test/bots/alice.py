import sys
import json
import random

MY_NAME = 'alice'

f_name = sys.argv[1]
print("File name is {}".format(f_name))

with open(f_name, 'r') as f:
    data = json.load(f)

cells = data['cells']
blob = data['blob']
moves = []

for cell in cells:
    if cell['owner'] == MY_NAME:
        moves.append({
            "x": cell['x'],
            "y": cell['y'],
            "direction": random.randint(0, 3)
        })

with open(f_name, 'w') as f:
    json.dump({
        "moves": moves,
        "blob": {},
    }, f)

import random
import settings
import json


# Generate random coordinate taking into account boarders
# max_pos - coordinate of top boarder
def random_position(max_pos):
    return random.randint(0 + settings.SPAWN_BORDER_GAP, max_pos - 1 - settings.SPAWN_BORDER_GAP)


# Returns list of coordinate tuples for given coordinate
# Do not include coordinates that are out of field range
def neighbour_coords(coords):
    x, y = coords
    out = []
    for a in range(x - 1, x + 2):
        for b in range(y - 1, y + 2):
            if a != x or b != y:
                if a >= 0 and b >= 0:
                    if a < settings.FIELD_WIDTH and b < settings.FIELD_HEIGHT:
                        out.append((a, b))

    return out


def moves_to_dict(arr):
    out = {}
    for cmd in arr:
        x, y = cmd['x'], cmd['y']
        out[(x, y)] = cmd['direction']

    return out


def out_of_range(coords):
    x, y = coords

    if x < 0 or y < 0:
        return True
    if x > settings.FIELD_WIDTH or y > settings.FIELD_HEIGHT:
        return True

    return False


def load_instructions(bot):
    with open(bot.file(), 'r') as f:
        try:
            instructions = json.load(f)
            if not isinstance(instructions['moves'], list):
                raise Exception("moves not an array")
            if not isinstance(instructions['blob'], dict):
                raise Exception("blob is not a dict")

            return instructions
        except Exception as ex:
            print("Warning! Can't read {} instructions due to error: {}".format(bot.name, ex))

    return {
        "moves": [],
        "blob": {},
    }

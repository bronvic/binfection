import os
import uuid
import json
from subprocess import Popen, PIPE, CalledProcessError
from pathlib import Path

from src.helpers import random_position, neighbour_coords, moves_to_dict, out_of_range, load_instructions
import settings


class Direction:
    UP, RIGHT, DOWN, LEFT = range(4)

    @staticmethod
    def all():
        return range(4)


class Cell:
    owner = None
    units = 0

    def __init__(self, owner=None, units=0):
        self.owner = owner
        self.units = units

    def to_dict(self, coords):
        x, y = coords
        return {
            "owner": self.owner,
            "units": self.units,
            "x": x,
            "y": y,
        }


class Bot:
    runner = None
    _file = None

    # data, that bots saved in previous round
    blob = None

    def __init__(self, runner):
        self.runner = runner

    @property
    def name(self):
        return Path(self.runner).stem

    def file(self, game_id=None):
        if game_id is None:
            return self._file
        else:
            self._file = os.path.join(settings.GAMES_DIR, str(game_id) + '.' + self.name)


class Game:
    bots = []
    # list of field
    game_process = []
    # Hashmap for used cells
    # Tuple of coordinates is a key, cell is a value
    cells = {}

    session_id = None

    def __init__(self, *runner_paths):
        self.session_id = uuid.uuid4()
        # DEBUG
        # self.session_id = 0
        self.result_file = os.path.join(settings.GAMES_DIR, str(self.session_id) + '.res')

        for path in runner_paths:
            assert os.path.isfile(path), "{} is not file".format(path)
            assert os.access(path, os.X_OK), "{} is not executable".format(path)

            self.bots.append(Bot(path))

    def bot_names(self):
        return [bot.name for bot in self.bots]

    # Check if given number of bots be placed at the field
    def placement_is_possible(self):
        # TODO: calculate it somehow. This implementation totally temporary
        return settings.FIELD_WIDTH * settings.FIELD_HEIGHT >= len(self.bots)

    def generate_start_positions(self):
        assert self.placement_is_possible(), "Can't place {} bots on field with given rules".format(len(self.bots))
        # TODO: FIELD_HEIGHT here is quite random parameter. I took it because I want number of attempts to depend on the size of the field
        limit_of_attempts = settings.FIELD_HEIGHT

        for bot in self.bots:
            attempt = 0
            x = random_position(settings.FIELD_WIDTH)
            y = random_position(settings.FIELD_HEIGHT)
            print("{}\tx = {}, y = {}".format(bot.name, x, y))

            while any(abs(x - x0) <= settings.SPAWNS_DISTANCE and abs(y - y0) <= settings.SPAWNS_DISTANCE for (x0, y0) in self.cells) and attempt < limit_of_attempts:
                x = random_position(settings.FIELD_WIDTH)
                y = random_position(settings.FIELD_HEIGHT)
                print("Rerender")
                print("{}\tx = {}, y = {}".format(bot.name, x, y))

                attempt += 1

            if attempt >= limit_of_attempts:
                print("Warning! Can't place bots randomly")
                break
            else:
                self.cells[(x, y)] = Cell(bot.name, settings.WARRIORS_INIT_NUMBER)

        if len(self.cells) * settings.SPAWNS_NUMBER != len(self.bots):
            # TODO: try to place them "manually", i think.
            return False
        else:
            return True

    def dump_to_files(self):
        bot_processed = {}
        bot_dump = {}
        for bot in self.bots:
            bot_processed[bot.name] = set()
            bot_dump[bot.name] = []

        for coords, cell in self.cells.items():
            assert cell.owner in self.bot_names(), "Wrong owner ({}) of cell {}".format(cell.owner, coords)

            if coords not in bot_processed[cell.owner]:
                bot_dump[cell.owner].append(cell.to_dict(coords))
                bot_processed[cell.owner].add(coords)

            # Add neighbours for given cell to dump
            # User can see all neighbour cells. If border nearby, user will see nothing
            for n_coords in neighbour_coords(coords):
                if n_coords in bot_processed[cell.owner]:
                    continue
                else:
                    try:
                        n_cell = self.cells[n_coords]
                    except KeyError:
                        n_cell = Cell()

                    bot_dump[cell.owner].append(n_cell.to_dict(n_coords))
                    bot_processed[cell.owner].add(n_coords)

        for bot in self.bots:
            with open(bot.file(), 'w') as f:
                f.write(json.dumps({
                    "cells": bot_dump[bot.name],
                    "blob": bot.blob if bot.blob else {},
                }))

    def check_moves(self, moves, name, out):
        for move in moves:
            try:
                x, y = move['x'], move['y']
                direction = move['direction']
                if direction not in Direction.all():
                    raise Exception("Wrong direction")
            except KeyError:
                print("Warning! Wrong format of move {}".format(move))
                continue
            except Exception as ex:
                print("Warning! For move {}, exception {}".format(move, ex))
                continue

            try:
                cell = self.cells[(x, y)]
                if cell.owner != name:
                    print("Warning! Attempt to move opponent's cell")
                    continue

                out.append(move)
            except KeyError:
                print("Warning! Wrong cell want to be moved {}".format(move))
                continue

        return out

    def execute_instructions(self, instructions):
        marked_to_delete = set()
        marked_to_create = {}

        # TODO: Figure out what is the best way to make turn
        # TODO: Should every cell process from top left corner to bottom right?
        # TODO: Or should we make it truly simultaneous?
        for coords, cell in self.cells.items():
            try:
                direction = instructions[coords]
                x1, y1 = coords

                if direction == Direction.UP:
                    x2, y2 = x1, y1 - 1
                elif direction == Direction.DOWN:
                    x2, y2 = x1, y1 + 1
                elif direction == Direction.LEFT:
                    x2, y2 = x1 - 1, y1
                elif direction == Direction.RIGHT:
                    x2, y2 = x1 + 1, y1
                else:
                    assert False, "Wrong direction {}".format(direction)

                units_leave = int(cell.units / 2)
                units_left = cell.units - units_leave

                cell.units = units_left

                # Units that goes over the border never come back
                if out_of_range((x2, y2)):
                    continue

                try:
                    disputed_cell = self.cells[(x2, y2)]
                    if cell.owner != disputed_cell.owner:
                        fight_result = cell.units - disputed_cell.units
                    else:
                        fight_result = cell.units + disputed_cell.units
                        if fight_result > settings.WARRIORS_LIMIT:
                            fight_result = settings.WARRIORS_LIMIT

                    if fight_result > 0:
                        disputed_cell.owner = cell.owner
                    elif fight_result < 0:
                        pass
                    else:
                        # Mark to delete cell without units because we can't do it in iterator
                        disputed_cell.owner = None
                        marked_to_delete.add((x2, y2))

                    disputed_cell.units = abs(fight_result)
                except KeyError:
                    # TODO: Now I resolve conflicts right here
                    # TODO: Maybe only add cell to structure and traverse them in the end?
                    # TODO: For this, we need hashmap for marked_to_create, that can store several items in one place
                    try:
                        existing_cell = marked_to_create[(x2, y2)]
                        if cell.owner != existing_cell.owner:
                            fight_result = cell.units - existing_cell.units
                        else:
                            fight_result = cell.units + existing_cell.units
                            if fight_result > settings.WARRIORS_LIMIT:
                                fight_result = settings.WARRIORS_LIMIT

                        if fight_result > 0:
                            marked_to_create[x2, y2] = Cell(cell.owner, abs(fight_result))
                        elif fight_result < 0:
                            marked_to_create[x2, y2] = Cell(existing_cell.owner, abs(fight_result))
                        else:
                            del marked_to_create[(x2, y2)]

                    except KeyError:
                        marked_to_create[(x2, y2)] = Cell(cell.owner, units_leave)

            except KeyError:
                continue

        for coords in marked_to_delete:
            del self.cells[coords]

        try:
            self.cells = {**self.cells, **marked_to_create}
        except Exception as ex:
            print(ex)

    def grow(self):
        for _, cell in self.cells.items():
            cell.units *= settings.GROW_COEFFICIENT
            if cell.units > settings.WARRIORS_LIMIT:
                cell.units = settings.WARRIORS_LIMIT

    def save_current_position(self):
        cells = []
        for coords, cell in self.cells.items():
            x, y = coords
            cells.append({
                "owner": cell.owner,
                "units": cell.units,
                "x": x,
                "y": y,
            })

        self.game_process.append(cells)

    def start(self):
        # Load parameters that was unknown on init
        for bot in self.bots:
            bot.file(self.session_id)
            bot.blob = {}

        # prepare place for the game
        print("Start game with uuid {}".format(self.session_id))
        print("Bots: {}".format(self.bot_names()))

        ok = self.generate_start_positions()
        if not ok:
            print("Error! Can't generate start position")
            # TODO: return code?
            return

        print("\nStart position")
        self.field_debug_print()
        self.save_current_position()

        turn = 0
        while turn < settings.TURNS_LIMIT:
            self.dump_to_files()

            # Here will be communication with runners
            for bot in self.bots:
                pipe = Popen([bot.runner, bot.file()], stdin=PIPE, stdout=PIPE)
                result, error = pipe.communicate()

                if pipe.wait() != 0:
                    raise CalledProcessError(-1, bot.runner)
                if error is not None:
                    raise BaseException(error)

            # Collect bot's commands and blobs
            instructions = {}
            checked_moves = []
            for bot in self.bots:
                instructions[bot.name] = load_instructions(bot)
                self.check_moves(instructions[bot.name]['moves'], bot.name, checked_moves)
                bot.blob = instructions[bot.name]['blob']

            self.execute_instructions(moves_to_dict(checked_moves))
            print("\nTurn {}".format(turn))
            self.field_debug_print()
            self.save_current_position()

            self.grow()
            print()
            self.field_debug_print()
            self.save_current_position()

            turn += 1

        with open(self.result_file, 'w') as f:
            f.write(json.dumps(self.game_process))

        for bot in self.bots:
            os.remove(bot.file())

    def field_debug_print(self):
        max_len = len(str(settings.WARRIORS_LIMIT))
        for y in range(0, settings.FIELD_HEIGHT):
            for x in range(0, settings.FIELD_WIDTH):
                try:
                    cell = self.cells[(x, y)]
                    units_formatted = str(cell.units).ljust(max_len)
                    print(f'{cell.owner[0].upper()}{units_formatted} ', end='')
                except KeyError:
                    units_formatted = '0'.ljust(max_len)
                    print(f'_{units_formatted} ', end='')

            print()

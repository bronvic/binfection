from os.path import join
from src.game import *
from settings import RUNNERS_DIR


def main(*bot_names):
    runner_paths = [join(RUNNERS_DIR, name) for name in bot_names]

    game = Game(*runner_paths)
    game.start()


main('alice.sh', 'bob.sh')

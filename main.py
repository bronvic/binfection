from os.path import join
from src.game import *
from settings import RUNNERS_DIR


def main(bot1_runner, bot2_runner):
    game = Game(join(RUNNERS_DIR, bot1_runner), join(RUNNERS_DIR, bot2_runner))
    game.start()


main('alice.sh', 'bob.sh')

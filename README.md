# binfection 
Platform for bots to play the game

version 0.0.1

The idea is: make competitions between bots

* Add your bot to test/bots/
* Add .sh script to test/runners. Script should run your bot
* Path your script name as one of parameters in the main function of main.py
* Run main.py

## The game
Two bots are playing on cell field. They manage units which can move and fight.
### I phase
Every turn game gives you conditions of all cells where you have units and all neighbor cells. One cell has 8 neighbors. If you see less, there is a border nearby.
### II phase
For each cell, you can use direction to move your units.
### III phase
Game calculate instructions from bots simultaneously. It splits units on every cell in half and sends half of them in direction you choose

If you move to empty cell, this cell becomes yours

If you move to the enemy cell, the winner is the one who has more units. Number of units left on the cell is the difference between units

If both bots move to empty cell, rules same as if one of the bots was there

If there are 0 units on the cell after fight, cell becomes nobody's

If you move your units beyond the limits of the field, they will disappear


## API
Game communicates with bots using files with json. Your runner will be called with one argument: filename in which you can find json with current state of the field.
You have to write json with your instructions to this file in the end

json which game will put to file looks like this:
```json
  {
    "cells": [{
        "owner": "alice",
        "units": 5,
        "x": 4,
        "y": 3
      }
    ],
    "blob": {}
  }
```
where
* owner - name of the owner of the cell. Note that name of your bot will be name of .sh file without extention
* units - number of units in the cell
* x, y - cell coordinates
* blob - whatever you saved in prevous turn


Your instructions should look like this:
```json
{
  "moves": [{
      "x": 4,
      "y": 3,
      "direction": 2
    }
  ],
  "blob": {}
}
```
where
* x, y - coordinates of the cell you want to move
* direction - direction to move. 0 - UP, 1 - RIGHT, 2 - DOWN, 3 - LEFT
* blob - any data you want to save for the next 

## Settings
Check out settings in settings.py file. You can override any setting in settings.ini, which should look like this:
```ini
[GENERAL]
TURNS_LIMIT: 20
WARRIORS_LIMIT: 9
WARRIORS_INIT_NUMBER: 5

FIELD_WIDTH: 7
FIELD_HEIGHT: 7
```

## Final output
You will find `{game_id}.res` file in `games` directory after your game finished.
It will contain json with list of lists of cells. Each element of top level list contains cells for the turn.
First element contains cells just after spawn
Second - cells after players make there moves
Third - cells after grow faze
Fourth - cells after players moves again and so on

Thus elements of array correspond such sequence:
```
spawn -> turn 1 -> grow -> turn 2 -> grow -> turn 3 ...
```

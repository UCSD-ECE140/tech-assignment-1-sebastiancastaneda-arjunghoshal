"""
Author: Charles Lee
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from player import Player


class Team:
    def __init__(self, teamName: str):
        assert isinstance(teamName, str)
        self.__name = teamName
        self.players: list[Player] = []
        self.__score = 0

    @property
    def name(self):
        return self.__name

    @property
    def score(self):
        return self.__score

    def addPlayer(self, player: Player):
        assert isinstance(player, Player)
        self.players.append(player)

    def increaseScore(self, value: int):
        assert isinstance(value, int)
        self.__score += value

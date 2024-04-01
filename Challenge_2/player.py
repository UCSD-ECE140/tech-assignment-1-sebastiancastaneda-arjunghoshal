"""
Author: Charles Lee
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from team import Team


class Player:
    def __init__(self, playerName: str, team: Team):
        assert isinstance(playerName, str)

        self.__name = playerName
        self.__team = team
        self.__loc: Optional[tuple[int,int]] = None

    @property
    def name(self):
        return self.__name

    @property
    def team(self):
        return self.__team

    @property
    def loc(self):
        return self.__loc

    @loc.setter
    def loc(self, value: tuple[int,int]):
        assert isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], int)
        self.__loc = value

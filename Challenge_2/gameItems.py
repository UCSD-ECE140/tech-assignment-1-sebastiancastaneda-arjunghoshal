"""
Author: Charles Lee
"""

from abc import abstractmethod

class Wall:
    pass

class Coin:
    @abstractmethod
    def value(self):
        ...

class Coin1(Coin):
    @property
    def value(self):
        return 1

class Coin2(Coin):
    @property
    def value(self):
        return 2

class Coin3(Coin):
    @property
    def value(self):
        return 3
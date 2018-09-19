from enum import Enum

from ..prnml import model


class SpecialLabel(Enum):
    BOS = 1
    STAR = 2


class PDABuilder(object):
    def __init__(self, pda):
        self.pda = pda

        self.symbols = {symbol.value: symbol for symbol in pda.symbols}
        self.locations = {location.value: location for location in
                          pda.locations}

    def symbol(self, value):
        if isinstance(value, model.NoLabel):
            return self.bos()
        if value not in self.symbols:
            self.symbols[value] = self.pda.symbol(value)
        return self.symbols[value]

    def location(self, value):
        if value not in self.locations:
            self.locations[value] = self.pda.location(value)
        return self.locations[value]

    def star(self):
        return self.symbol(SpecialLabel.STAR)

    def bos(self):
        return self.symbol(SpecialLabel.BOS)

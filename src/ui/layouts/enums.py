from enum import Enum


class LayoutType(str, Enum):
    VBOX = 'vbox'
    HBOX = 'hbox'
    GRID = 'grid'

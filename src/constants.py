from enum import Enum, StrEnum


class Program(StrEnum):
    MNGT = "MNGT"
    DATA = "DATA"
    ICP = "ICP"


class Gender(StrEnum):
    M = "M"
    F = "F"


class FontSize(Enum):
    SMALL = 9
    MEDIUM = 10
    LARGE = 12


class Font(StrEnum):
    MONTSERRAT_LIGHT = "Montserrat Light"
    MONTSERRAT_REGULAR = "Montserrat"

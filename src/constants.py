from enum import Enum, StrEnum


class Program(StrEnum):
    MNGT = "MNGT"
    DATA = "DATA"
    ICP = "ICP"


class Gender(StrEnum):
    M = "M"
    F = "F"
    X = "X"


class FileTypeFilter(StrEnum):
    WORD = "Word Files (*.docx);;All Files (*)"
    PDF = "PDF Files (*.pdf);;All Files (*)"


class FileCategory(StrEnum):
    PAPI = "PAPI Gebruikersrapport"
    COG = "Cog. Test"
    NOTES = "Assessment Notes"
    ICP = "ICP Description File"


class Language(StrEnum):
    EN = "English"
    FR = "French"
    NL = "Dutch"


class FontSize(Enum):
    SMALL = 9
    MEDIUM = 10
    LARGE = 12


class Font(StrEnum):
    MONTSERRAT_LIGHT = "Montserrat Light"
    MONTSERRAT_REGULAR = "Montserrat"


class PromptName(StrEnum):
    FIRST_IMPRESSION = "prompt2_firstimpr"
    FIRST_IMPRESSION_ORIGINAL = "prompt2_firstimpr_original"
    PERSONALITY = "prompt3_personality"
    PERSONALITY_ORIGINAL = "prompt3_personality_original"
    COGCAP_SCORES = "prompt4_cogcap_scores"
    COGCAP_SCORES_ORIGINAL = "prompt4_cogcap_scores_original"
    COGCAP_REMARKS = "prompt4_cogcap_remarks"
    COGCAP_REMARKS_ORIGINAL = "prompt4_cogcap_remarks_original"
    LANGUAGE = "prompt5_language"
    LANGUAGE_ORIGINAL = "prompt5_language_original"
    CONQUAL = "prompt6a_conqual"
    CONQUAL_ORIGINAL = "prompt6a_conqual_original"
    CONIMPROV = "prompt6b_conimprov"
    CONIMPROV_ORIGINAL = "prompt6b_conimprov_original"
    QUALSCORE = "prompt7_qualscore"
    QUALSCORE_ORIGINAL = "prompt7_qualscore_original"
    QUALSCORE_DATA = "prompt7_qualscore_data"
    QUALSCORE_DATA_ORIGINAL = "prompt7_qualscore_data_original"
    DATATOOLS = "prompt8_datatools"
    DATATOOLS_ORIGINAL = "prompt8_datatools_original"
    INTERESTS = "prompt9_interests"
    INTERESTS_ORIGINAL = "prompt9_interests_original"


REQUIRED_FILE_CATEGORIES = [
    file_category for file_category in FileCategory if file_category != FileCategory.ICP
]

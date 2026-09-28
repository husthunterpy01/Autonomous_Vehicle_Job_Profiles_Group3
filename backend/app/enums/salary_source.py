from enum import Enum


class SalarySource(str, Enum):
    API = "api"
    REGEX = "regex"
    LEVELS_FYI_AVERAGE = "levels_fyi_average"

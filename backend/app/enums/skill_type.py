from enum import Enum


class SkillType(str, Enum):
    TOOL = "tool"
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DOMAIN_CONCEPT = "domain_concept"
    CERTIFICATION = "certification"

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditCategoryRule:
    name: str
    keywords: tuple[str, ...]

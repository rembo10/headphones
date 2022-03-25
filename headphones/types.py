from dataclasses import dataclass

@dataclass(frozen=True)
class Result:
    title: str
    size: int
    url: str
    provider: str
    kind: str
    matches: bool

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    text: str
    people: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)


CASES: list[EvalCase] = []

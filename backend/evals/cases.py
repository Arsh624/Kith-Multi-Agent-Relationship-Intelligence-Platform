from dataclasses import dataclass, field


@dataclass
class EvalCase:
    text: str
    people: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)


CASES: list[EvalCase] = [
    EvalCase(
        text="Hi, I am a PM at Stripe. Reach out anytime.",
        people=["I"],
        companies=["Stripe"],
    ),
    EvalCase(
        text="Met Priya Sharma today, she is a designer at Figma.",
        people=["Priya Sharma"],
        companies=["Figma"],
    ),
    EvalCase(
        text="My friend Ravi leads recruiting at Notion, I can introduce you.",
        people=["Ravi"],
        companies=["Notion"],
        relationships=[("I", "Ravi", "can_intro")],
    ),
    EvalCase(
        text="Dipunj works at Cloudflare. His friend Rahul is an SDE at Qualcomm.",
        people=["Dipunj", "Rahul"],
        companies=["Cloudflare", "Qualcomm"],
        relationships=[("Dipunj", "Rahul", "knows")],
    ),
    EvalCase(
        text="Sarah referred me to Tom, who runs data at Databricks.",
        people=["Sarah", "Tom"],
        companies=["Databricks"],
        relationships=[("Sarah", "Tom", "referred")],
    ),
    EvalCase(
        text="Thanks for the coffee. No work talk, just catching up.",
        people=[],
        companies=[],
    ),
    EvalCase(
        text="Alex is a founder at a stealth startup, no company name yet.",
        people=["Alex"],
        companies=[],
    ),
    EvalCase(
        text="I chatted with Maya Chen (Google) and Arjun Patel (Stripe) at the meetup.",
        people=["Maya Chen", "Arjun Patel"],
        companies=["Google", "Stripe"],
    ),
    EvalCase(
        text="Priya can connect you with her colleague Neha at Stripe.",
        people=["Priya", "Neha"],
        companies=["Stripe"],
        relationships=[("Priya", "Neha", "can_intro")],
    ),
    EvalCase(
        text="Following up: Ben from Airbnb said to email him next week.",
        people=["Ben"],
        companies=["Airbnb"],
    ),
    EvalCase(
        text="Lena is a recruiter at Meta and knows Sam, a PM at Meta.",
        people=["Lena", "Sam"],
        companies=["Meta"],
        relationships=[("Lena", "Sam", "knows")],
    ),
    EvalCase(
        text="Quick note to self: call the dentist tomorrow.",
        people=[],
        companies=[],
    ),
]

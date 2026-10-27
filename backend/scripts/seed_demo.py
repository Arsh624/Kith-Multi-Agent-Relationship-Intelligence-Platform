"""Seed a separate, fictional demo account for recording a Kith demo.

Talks to the public HTTP API only (no direct database access), so it is safe to
point at the live app: it creates or reuses ONE demo user and never reads,
edits, or deletes anyone else's data. If the demo user already has people, it
skips seeding (it never deletes anything) and just re-verifies the demo.

Usage (from backend/):
    python scripts/seed_demo.py                                   # local, http://127.0.0.1:8012
    python scripts/seed_demo.py --base https://kith-1a3z.onrender.com

Password: taken from --password or the KITH_DEMO_PASSWORD env var. If neither is
given, a random one is generated and written to backend/.demo_credentials
(gitignored), so it is never committed.

All people below are fictional.
"""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_EMAIL = "kith.demo@example.com"
CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / ".demo_credentials"

# (name, company, title, known_through, note). Order matters: an introducer must
# exist before anyone "known through" them. No known_through = you know them directly.
PEOPLE = [
    ("Maya Chen", "Notion", "Senior Product Manager", None,
     "Former teammate, very responsive, happy to make intros."),
    ("Arjun Patel", "Stripe", "Software Engineer", None,
     "Met at a payments infra meetup."),
    ("Sofia Martinez", "Datadog", "Engineering Manager", None,
     "Mentor from grad school, gives great resume feedback."),
    ("Liam Brooks", "Airbnb", "Data Scientist", None,
     "College friend working on pricing models."),
    ("Daniel Okafor", "Carvana", "Staff Software Engineer", "Maya Chen",
     "Works on the vehicle logistics platform. Maya can introduce me."),
    ("Hannah Kim", "Carvana", "Technical Recruiter", "Daniel Okafor",
     "Hires backend and data engineers."),
    ("Ethan Wright", "Stripe", "Backend Engineer", "Arjun Patel",
     "Builds billing APIs."),
    ("Priya Nair", "Datadog", "Senior Recruiter", "Sofia Martinez",
     "Runs early-career hiring."),
    ("Noah Johnson", "Airbnb", "Machine Learning Engineer", "Liam Brooks",
     "Search ranking and recommendations."),
    ("Grace Liu", "Figma", "Product Designer", "Maya Chen",
     "Design systems and prototyping."),
    ("Omar Haddad", "Cloudflare", "DevOps Engineer", "Sofia Martinez",
     "Kubernetes and edge infrastructure."),
    ("Chloe Davis", "Microsoft", "University Recruiter", "Liam Brooks",
     "Campus hiring for new grads."),
]

STATUS = {"Maya Chen": "hot", "Daniel Okafor": "warm", "Arjun Patel": "warm",
          "Hannah Kim": "cold"}
FAVORITES = {"Maya Chen", "Daniel Okafor"}
TASKS = [
    ("Ask Maya for an intro to Daniel at Carvana", "high"),
    ("Send Sofia my updated resume", "medium"),
    ("Thank Arjun for the Stripe referral tips", "low"),
]


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.token = None

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8")
            try:
                return err.code, json.loads(raw)
            except ValueError:
                return err.code, raw


def resolve_password(cli_password):
    if cli_password:
        return cli_password
    if os.environ.get("KITH_DEMO_PASSWORD"):
        return os.environ["KITH_DEMO_PASSWORD"]
    if CREDENTIALS_FILE.exists():
        for line in CREDENTIALS_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    password = secrets.token_urlsafe(12)
    CREDENTIALS_FILE.write_text(f"password={password}\n", encoding="utf-8")
    print(f"Generated a demo password and saved it to {CREDENTIALS_FILE}")
    return password


def sign_in(api: Api, email: str, password: str) -> None:
    status, body = api.call("POST", "/auth/register",
                            {"email": email, "password": password})
    if status == 400:  # already registered: log in instead
        status, body = api.call("POST", "/auth/login",
                                {"email": email, "password": password})
    if status not in (200, 201):
        sys.exit(f"Could not sign in as {email}: HTTP {status} {body}")
    api.token = body["access_token"]


def seed(api: Api) -> None:
    ids = {}
    for name, company, title, known_through, note in PEOPLE:
        status, body = api.call("POST", "/people", {
            "name": name, "company": company, "known_through": known_through})
        if status != 201:
            sys.exit(f"Adding {name} failed: HTTP {status} {body}")
        ids[name] = body["id"]
        patch = {"title": title, "note": note}
        if name in STATUS:
            patch["status"] = STATUS[name]
        if name in FAVORITES:
            patch["favorite"] = True
        api.call("PATCH", f"/people/{ids[name]}", patch)
    for title, priority in TASKS:
        api.call("POST", "/tasks", {"title": title, "priority": priority})
    print(f"Seeded {len(PEOPLE)} people and {len(TASKS)} tasks.")


def verify(api: Api) -> bool:
    ok = True
    _, people = api.call("GET", "/people")
    print(f"\nDemo account has {len(people)} people.")

    _, paths = api.call("GET", "/intro-paths?" + urllib.parse.urlencode(
        {"company": "Carvana"}))
    print("Paths to Carvana:")
    for path in paths.get("paths", []):
        print("  " + " -> ".join(path))
    ok &= ["You", "Maya Chen", "Daniel Okafor", "Carvana"] in paths.get("paths", [])

    # The first search also builds the vector index (self-healing), so this warms it.
    status, found = api.call("GET", "/search?" + urllib.parse.urlencode(
        {"q": "talent acquisition"}))
    names = [r["name"] for r in (found or {}).get("results", [])][:3]
    print(f'Search by meaning "talent acquisition" (HTTP {status}) top 3: {names}')
    recruiters = {"Hannah Kim", "Priya Nair", "Chloe Davis"}
    ok &= status == 200 and bool(recruiters & set(names))
    print("\nDEMO READY" if ok else "\nDEMO CHECK FAILED (see output above)")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8012")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    api = Api(args.base)
    sign_in(api, args.email, resolve_password(args.password))
    _, existing = api.call("GET", "/people")
    if existing:
        print(f"{args.email} already has {len(existing)} people; skipping seeding.")
    else:
        seed(api)
    sys.exit(0 if verify(api) else 1)


if __name__ == "__main__":
    main()

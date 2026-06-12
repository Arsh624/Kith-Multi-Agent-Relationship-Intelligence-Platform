import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.search.embedder import GeminiEmbedder
from app.search.store import QdrantVectorStore

PEOPLE = [
    (str(uuid.uuid4()), "Mia (designer, Figma)", "Mia Chen. designer. Figma."),
    (str(uuid.uuid4()), "Bob (engineer, Stripe)", "Bob Lee. backend engineer. Stripe."),
    (str(uuid.uuid4()), "Sara (recruiter, Notion)", "Sara Park. recruiter. Notion."),
]


def main() -> None:
    embedder = GeminiEmbedder(
        api_key=settings.gemini_api_key, model=settings.embedding_model
    )
    store = QdrantVectorStore(path="./qdrant_smoke")
    labels = {}
    for person_id, label, text in PEOPLE:
        labels[person_id] = label
        store.index("smoke-user", person_id, embedder.embed(text))
    hits = store.search("smoke-user", embedder.embed("who is a designer"), 3)
    for hit in hits:
        print(labels[hit.person_id], round(hit.score, 3))


if __name__ == "__main__":
    main()

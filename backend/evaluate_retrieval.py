"""Run a small retrieval smoke test against the current local database."""

from app.rag import embed
from app.storage import search


CASES = [
    ("What are the standard working hours?", "company-handbook.md"),
    ("How do I define a Python function?", "python-basics.md"),
    ("What is the capital of Japan?", None),
]


def main():
    # ponytail: sequential local evaluation; parallel requests add complexity before this dataset needs it.
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.models import User
        user = User.query.first()
        if not user:
            raise SystemExit("Create a user and upload the sample documents first.")
        for question, expected_file in CASES:
            results = search(embed(question), user.id)
            files = {item["filename"] for item in results}
            passed = expected_file in files if expected_file else not files
            print("PASS" if passed else "FAIL", question, sorted(files))


if __name__ == "__main__":
    main()

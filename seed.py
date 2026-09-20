from app import create_app
from app.cli import seed_content

app = create_app()
if __name__ == "__main__":
    with app.app_context():
        seed_content(demo=True)
        print("Demo content seeded. Sample accounts are disabled in production.")

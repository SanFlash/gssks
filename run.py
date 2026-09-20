"""Local first-run launcher and production WSGI entry point."""
from pathlib import Path

if __name__ == '__main__':
    from app.local_startup import prepare_local_environment
    try:
        prepare_local_environment(Path(__file__).resolve().parent)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

from app import create_app

app = create_app()

if __name__ == '__main__':
    from app.local_startup import initialize_local_database
    try:
        initialize_local_database(app)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print('GSSKS local setup ready: http://127.0.0.1:5000')
    print('Development login details are in .env. Optional integrations remain disabled unless configured.')
    app.run(host='127.0.0.1', port=5000, debug=False)

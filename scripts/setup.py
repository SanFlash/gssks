"""Create a working local development configuration without password prompts."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    os.chdir(ROOT)
    print("Gyanpath setup — local development. Optional integrations remain disabled.")
    if sys.version_info[:2] != (3, 13):
        print(
            "Python 3.13 is the validated runtime. Current: " + sys.version.split()[0]
        )
        return 1
    path = ROOT / ".env"
    if not path.exists():
        data = (
            (ROOT / ".env.example")
            .read_text()
            .replace("SECRET_KEY=change-me", "SECRET_KEY=" + secrets.token_hex(32))
        )
        path.write_text(data)
        try:
            path.chmod(0o600)
        except OSError:
            pass
        print(
            "Created .env with a generated local secret and documented demo accounts."
        )
    else:
        print("Existing .env retained. No credentials changed.")
    for args in [
        ["-m", "flask", "--app", "run", "db", "upgrade"],
        ["seed.py"],
        ["-m", "flask", "--app", "run", "check-config"],
    ]:
        subprocess.run([sys.executable, *args], check=True)
    print("Ready. Run: python run.py — open http://127.0.0.1:5000")
    print("Admin credentials: DEMO_ADMIN_EMAIL and DEMO_ADMIN_PASSWORD in .env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

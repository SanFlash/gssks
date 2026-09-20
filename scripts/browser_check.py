"""Local browser smoke and responsive QA. Run from project root."""

import json
import threading
import tempfile
from pathlib import Path
from werkzeug.serving import make_server, WSGIRequestHandler
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from app import create_app
from app.extensions import db
from app.cli import seed_content


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


temporary = tempfile.TemporaryDirectory()
app = create_app(
    {
        **{key: value for key, value in dotenv_values(".env.example").items() if key.startswith("DEMO_")},
        "RATELIMIT_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + temporary.name + "/browser.db",
    }
)
with app.app_context():
    db.create_all()
    seed_content(demo=True)
server = make_server(
    "127.0.0.1", 5099, app, threaded=True, request_handler=QuietHandler
)
threading.Thread(target=server.serve_forever, daemon=True).start()
output = Path("docs/screenshots")
output.mkdir(parents=True, exist_ok=True)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # External fonts and motion libraries are optional; use deterministic local fallbacks for QA.
    context.route("https://**/*", lambda route: route.abort())
    page.goto("http://127.0.0.1:5099/", wait_until="networkidle")
    page.screenshot(path=str(output / "home-desktop.png"), full_page=True)
    widths = [
        320,
        360,
        375,
        390,
        414,
        430,
        480,
        768,
        820,
        1024,
        1280,
        1366,
        1440,
        1600,
        1920,
        2560,
    ]
    for width in widths:
        page.set_viewport_size({"width": width, "height": 900})
        page.goto("http://127.0.0.1:5099/", wait_until="domcontentloaded")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1"
        )
        results.append({"route": "/", "width": width, "horizontal_overflow": overflow})
        if overflow:
            page.screenshot(path='/tmp/gssks-overflow.png', full_page=True)
            print(page.evaluate("({width:innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth,bad:[...document.querySelectorAll('*')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>({tag:e.tagName,cls:e.className,w:e.clientWidth,s:e.scrollWidth})).slice(0,30)})"))
            print(page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right,text:e.innerText?.slice(0,70)})).slice(0,20)"))
        assert not overflow, f"Homepage overflows at {width}"
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(output / "home-mobile.png"), full_page=True)
    page.get_by_role("button", name="Open navigation").click()
    page.locator("#primary-nav").get_by_role(
        "link", name="ICPS", exact=True
    ).click()
    assert page.url.endswith("/icps")
    for path in [
        "/projects",
        "/projects/gandhi-shilp-bazaar-2024",
        "/icps",
        "/recognition",
        "/about",
        "/news-events",
        "/get-involved",
        "/volunteer",
        "/contact",
        "/donate",
        "/gallery",
        "/login",
    ]:
        page.goto("http://127.0.0.1:5099" + path, wait_until="domcontentloaded")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth + 1"
        )
        results.append({"route": path, "width": 390, "horizontal_overflow": overflow})
        assert not overflow, path
    page.locator("#email").fill("admin.demo@gyanpath.local")
    page.locator("#password").fill("Gyanpath@Demo2026!")
    page.get_by_role("button", name="Sign in securely").click()
    page.goto("http://127.0.0.1:5099/admin", wait_until="domcontentloaded")
    assert page.locator(".admin-sidebar").count() == 1
    page.screenshot(path=str(output / "admin-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(path=str(output / "admin-desktop.png"), full_page=True)
    page.goto("http://127.0.0.1:5099/admin/content-studio", wait_until="domcontentloaded")
    assert page.get_by_role("heading", name="ICPS programme page").count() == 1
    page.screenshot(path=str(output / "studio-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
    page.screenshot(path=str(output / "studio-mobile.png"), full_page=True)
    page.goto("http://127.0.0.1:5099/admin/website/leadership", wait_until="domcontentloaded")
    page.locator("#founder_bio").fill("Organization-approved biography entered during browser verification.")
    page.get_by_role("button", name="Save settings").click()
    page.goto("http://127.0.0.1:5099/recognition", wait_until="domcontentloaded")
    assert "Organization-approved biography entered during browser verification." in page.locator("main").inner_text()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(
        "http://127.0.0.1:5099/admin/manage/projects/new", wait_until="domcontentloaded"
    )
    assert page.locator(".rich-editor").count() > 0
    page.set_viewport_size({"width": 320, "height": 900})
    assert not page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth + 1"
    )
    page.goto("http://127.0.0.1:5099/gallery", wait_until="domcontentloaded")
    assert "DEMO CONTENT" not in page.locator("main").inner_text()
    page.goto("http://127.0.0.1:5099/contact", wait_until="domcontentloaded")
    page.locator("#name").fill("QA Example")
    page.locator("#email").fill("qa@example.org")
    page.locator("#subject").fill("Browser test enquiry")
    page.locator("#message").fill("Testing the complete browser submission workflow.")
    page.locator("#consent").check()
    page.get_by_role("button", name="Send enquiry").click()
    assert (
        page.get_by_role("status")
        .filter(has_text="Your enquiry has been received")
        .count()
        == 1
    )
    page.goto("http://127.0.0.1:5099/volunteer", wait_until="domcontentloaded")
    for field, value in {
        "name": "QA Volunteer",
        "email": "qa-volunteer@example.org",
        "phone": "9876543210",
        "city": "Bhopal",
        "age": "25",
        "skills": "Teaching and research",
    }.items():
        page.locator("#" + field).fill(value)
    page.locator("#consent").check()
    page.get_by_role("button", name="Submit application").click()
    assert (
        page.get_by_role("status")
        .filter(has_text="Your application has been received")
        .count()
        == 1
    )
    assert not errors, errors
    browser.close()
server.shutdown()
temporary.cleanup()
Path("docs/browser-results.json").write_text(
    json.dumps(
        {
            "transport": "local WSGI HTTP server",
            "browser": "Chromium 139",
            "reduced_motion": True,
            "external_assets": "blocked to verify local fallback",
            "checks": results,
            "javascript_errors": errors,
        },
        indent=2,
    )
)
print(
    f"{len(results)} responsive checks passed; navigation, login, admin, editor, publication filtering, contact and volunteer submission passed."
)

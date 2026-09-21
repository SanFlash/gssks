"""Real CSRF checks; never disable protection as a deployment workaround."""
import re
from flask import g


def clear_request_cache():
    # The shared fixture holds an app context; real HTTP requests get fresh g.
    g.pop("csrf_token", None)
    g.pop("_login_user", None)


def test_refresh_recovers_stale_session_and_login(app, client):
    app.config['WTF_CSRF_ENABLED'] = True
    page = client.get('/admin/login')
    old = re.search(r'name="csrf-token" content="([^"]+)"', page.text)[1]
    with client.session_transaction() as session:
        session.clear()
    credentials = {'email': app.config['DEMO_ADMIN_EMAIL'], 'password': app.config['DEMO_ADMIN_PASSWORD']}
    rejected = client.post('/admin/login', data={**credentials, 'csrf_token': old})
    assert rejected.status_code == 400
    assert 'Reopen your form' in rejected.text
    clear_request_cache()
    response = client.get('/auth/csrf')
    assert response.json['authenticated'] is False
    assert 'no-store' in response.headers['Cache-Control']
    result = client.post('/admin/login', data={**credentials, 'csrf_token': response.json['csrf_token']})
    assert result.status_code == 302
    clear_request_cache()
    assert client.get('/auth/csrf').json['authenticated'] is True


def test_tokens_are_session_bound_and_cross_origin_blocked(app, client):
    app.config['WTF_CSRF_ENABLED'] = True
    token = client.get('/auth/csrf').json['csrf_token']
    other = app.test_client()
    assert other.post('/login', data={'csrf_token': token}).status_code == 400
    assert client.post('/login', data={}).status_code == 400
    assert client.get('/auth/csrf', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.get('/auth/csrf', headers={'Origin': 'https://another.example'}).status_code == 403


def test_public_form_html_is_not_cached(app, client):
    for path in ['/', '/contact', '/volunteer', '/admin/login']:
        response = client.get(path)
        assert response.status_code == 200
        assert 'no-store' in response.headers['Cache-Control']
        assert '/static/js/forms.js' in response.text

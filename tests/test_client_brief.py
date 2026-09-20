from app.extensions import db
from app.models import Project, OrganizationSetting
from app.services.client_brief import apply_client_brief


def test_client_facts_and_publication_gate(app, client):
    app.config['SHOW_DEMO_CONTENT'] = False
    home = client.get('/').get_data(as_text=True)
    for text in ['Education.', 'Awareness.', 'Empowerment.', '1262/92', '1992', '0755-4278487', '088893937454', 'gyanpathngo.176@gmail.com', 'Gandhi Shilp Bazaar', '₹14,95,577+']:
        assert text in home
    assert 'DEMO CONTENT' not in home
    assert 'craft-scene' not in home
    assert client.get('/projects/community-skills').status_code == 404
    assert client.get('/projects/gandhi-shilp-bazaar-2024').status_code == 200
    api = client.get('/api/projects').get_data(as_text=True)
    assert 'community-skills' not in api
    for path in ['/news-events', '/get-involved', '/awareness', '/empowerment', '/contact', '/impact', '/documents']:
        assert client.get(path).status_code == 200
    sitemap = client.get('/sitemap.xml').get_data(as_text=True)
    assert '/news-events' in sitemap and '/get-involved' in sitemap
    assert '/projects/community-skills' not in sitemap


def test_brief_is_idempotent_and_preserves_custom_project(app):
    apply_client_brief()
    project = db.session.scalar(db.select(Project).where(Project.slug == 'gandhi-shilp-bazaar-2024'))
    project.outcomes = '<p>Organization edited outcomes.</p>'
    db.session.commit()
    apply_client_brief(overwrite=True)
    db.session.commit()
    assert project.outcomes == '<p>Organization edited outcomes.</p>'
    assert len(db.session.scalars(db.select(Project).where(Project.slug == project.slug)).all()) == 1
    assert project.beneficiary_count == 50
    assert str(project.start_date) == '2024-09-11'
    assert str(project.end_date) == '2024-09-17'
    assert not db.session.scalar(db.select(Project).where(Project.is_demo.is_(True), Project.published.is_(True)))

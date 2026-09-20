from app.extensions import db
from app.models import OrganizationSetting, Document, MediaAsset, Page
from app.services.design_brief import recognition_cards, apply_design_brief
from app.services.content import settings


def test_client_ui_and_private_sources(app, client):
    app.config['SHOW_DEMO_CONTENT'] = False
    for path in ['/', '/icps', '/recognition', '/about']:
        response = client.get(path)
        assert response.status_code == 200
        assert b'brand.css' in response.data
    home = client.get('/').get_data(as_text=True)
    assert 'Founder &amp; Director' in home
    assert 'I. S. Chauhan' in home
    assert 'data-certificate=' not in home
    assert client.get('/source-review-client-links').status_code == 404
    assert 'source-review-client-links' not in client.get('/sitemap.xml').get_data(as_text=True)
    assert client.get('/admin/content-studio').status_code == 302


def test_certificate_requires_verified_complete_public_record(app):
    values = settings()
    asset = MediaAsset(title='Certificate', secure_url='https://res.cloudinary.com/example/raw/upload/cert.pdf', public_id='cert', resource_type='raw', format='pdf', visibility='private')
    db.session.add(asset); db.session.flush()
    doc = Document(title='Award', media_id=asset.id, visibility='public')
    db.session.add(doc); db.session.flush()
    values.update(national_award_name='Test Award', national_award_year='2020', national_award_authority='Test Authority', national_award_document_id=str(doc.id), national_award_verified='true')
    assert not recognition_cards(values)[0]['ready']
    asset.visibility = 'public'
    assert recognition_cards(values)[0]['ready']
    doc.visibility = 'private'
    assert not recognition_cards(values)[0]['ready']


def test_studio_and_validation(admin):
    assert admin.get('/admin/content-studio').status_code == 200
    for group in ['branding','icps','leadership','recognition']:
        assert admin.get('/admin/website/' + group).status_code == 200
    response = admin.post('/admin/website/recognition', data={'national_award_verified':'true', 'state_award_verified':'false'})
    assert b'Verification requires' in response.data
    assert admin.post('/admin/website/leadership', data={'founder_image':'javascript:alert(1)'}).status_code == 200


def test_design_upgrade_preserves_custom_copy(app):
    row = db.session.scalar(db.select(OrganizationSetting).where(OrganizationSetting.key == 'hero_title'))
    row.value = 'Organization edited heading'
    apply_design_brief(); apply_design_brief()
    assert row.value == 'Organization edited heading'
    assert len(db.session.scalars(db.select(Page).where(Page.slug == 'icps')).all()) == 1

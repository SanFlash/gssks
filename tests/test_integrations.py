from io import BytesIO
from PIL import Image
from werkzeug.datastructures import FileStorage
from app.extensions import db
from app.models import MediaAsset
from app.services.media import MediaService


def image_file():
    output = BytesIO()
    Image.new("RGB", (4, 4), "green").save(output, format="PNG")
    output.seek(0)
    return FileStorage(output, filename="test.png", content_type="image/png")


def test_cloudinary_upload_replace_delete(app, monkeypatch):
    app.config.update(
        CLOUDINARY_CLOUD_NAME="demo",
        CLOUDINARY_API_KEY="test",
        CLOUDINARY_API_SECRET="test",
    )
    calls = []

    def upload(*args, **kwargs):
        calls.append(kwargs)
        return {
            "public_id": f"gyanpath/gallery/test{len(calls)}",
            "secure_url": f"https://res.cloudinary.com/demo/image/upload/test{len(calls)}.png",
            "width": 4,
            "height": 4,
            "format": "png",
        }

    monkeypatch.setattr("cloudinary.uploader.upload", upload)
    monkeypatch.setattr("cloudinary.uploader.destroy", lambda *a, **k: {"result": "ok"})
    service = MediaService()
    asset = service.upload_image(image_file())
    db.session.commit()
    original_id = asset.id
    service.replace_asset(asset, image_file())
    db.session.commit()
    assert asset.id == original_id and asset.public_id.endswith("test2")
    assert db.session.scalar(db.select(db.func.count(MediaAsset.id))) == 1
    service.delete_asset(asset)
    db.session.commit()
    assert db.session.scalar(db.select(db.func.count(MediaAsset.id))) == 0

"""Validated Cloudinary uploads with authenticated delivery for private assets."""

import io
import re
from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from PIL import Image, UnidentifiedImageError
from flask import current_app
from werkzeug.utils import secure_filename
from app.models import MediaAsset
from app.extensions import db


class MediaService:
    @staticmethod
    def configured():
        return all(
            current_app.config.get(k)
            for k in [
                "CLOUDINARY_CLOUD_NAME",
                "CLOUDINARY_API_KEY",
                "CLOUDINARY_API_SECRET",
            ]
        )

    @staticmethod
    def validate(file, kind):
        filename = secure_filename(file.filename or "")
        ext = Path(filename).suffix.lower().lstrip(".")
        allowed = {
            "image": {"jpg", "jpeg", "png", "webp"},
            "video": {"mp4", "webm"},
            "raw": {"pdf"},
        }
        if kind not in allowed or ext not in allowed[kind]:
            raise ValueError("File extension is not allowed.")
        data = file.read(25 * 1024 * 1024 + 1)
        file.seek(0)
        limit = {"image": 10, "raw": 5, "video": 25}[kind] * 1024 * 1024
        if not data or len(data) > limit:
            raise ValueError("File is empty or exceeds the upload limit.")
        if kind == "image":
            try:
                with Image.open(io.BytesIO(data)) as image:
                    if image.width * image.height > 24_000_000:
                        raise ValueError("Image exceeds 24 megapixels.")
                    if image.format.lower() not in {"jpeg", "png", "webp"}:
                        raise ValueError("Unsupported image format.")
                    detected = image.format.lower()
                    image.verify()
                if detected != ("jpeg" if ext == "jpg" else ext):
                    raise ValueError("Image format does not match its extension.")
            except (
                UnidentifiedImageError,
                OSError,
                Image.DecompressionBombError,
            ) as exc:
                raise ValueError("Invalid image file.") from exc
        elif kind == "raw":
            if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
                raise ValueError("Invalid PDF file.")
            if re.search(rb"/(JavaScript|JS|Launch|EmbeddedFile|OpenAction)\b", data):
                raise ValueError("Active or embedded PDF content is not allowed.")
        elif ext == "mp4" and data[4:8] != b"ftyp":
            raise ValueError("Invalid MP4 file.")
        elif ext == "webm" and not data.startswith(b"\x1aE\xdf\xa3"):
            raise ValueError("Invalid WebM file.")
        mime = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "pdf": "application/pdf",
            "mp4": "video/mp4",
            "webm": "video/webm",
        }[ext]
        if file.mimetype not in {mime, "application/octet-stream"}:
            raise ValueError("Content type does not match the file.")
        return data, filename

    def _upload(self, file, kind, folder="gallery", private=False):
        data, filename = self.validate(file, kind)
        if not self.configured():
            raise ValueError(
                "Cloudinary is not configured. Add the three CLOUDINARY variables to enable uploads."
            )
        if folder not in {
            "branding",
            "hero",
            "projects",
            "artisans",
            "events",
            "gallery",
            "videos",
            "documents",
            "blog",
        }:
            raise ValueError("Invalid media folder.")
        cloudinary.config(
            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=current_app.config["CLOUDINARY_API_KEY"],
            api_secret=current_app.config["CLOUDINARY_API_SECRET"],
            secure=True,
        )
        result = cloudinary.uploader.upload(
            io.BytesIO(data),
            resource_type=kind,
            folder=f"gyanpath/{folder}",
            type="authenticated" if private else "upload",
            use_filename=False,
            unique_filename=True,
        )
        asset = MediaAsset(
            title=filename,
            public_id=result["public_id"],
            secure_url=result["secure_url"],
            resource_type=kind,
            width=result.get("width"),
            height=result.get("height"),
            format=result.get("format"),
            folder=folder,
            visibility="private" if private else "public",
        )
        db.session.add(asset)
        db.session.flush()
        return asset

    def upload_image(self, file, folder="gallery", private=False):
        return self._upload(file, "image", folder, private)

    def upload_video(self, file, folder="videos", private=False):
        return self._upload(file, "video", folder, private)

    def upload_document(self, file, folder="documents", private=True):
        return self._upload(file, "raw", folder, private)

    def delete_asset(self, asset):
        if asset.public_id:
            cloudinary.uploader.destroy(
                asset.public_id,
                resource_type=asset.resource_type,
                type="authenticated" if asset.visibility == "private" else "upload",
                invalidate=True,
            )
        db.session.delete(asset)

    def replace_asset(self, asset, file):
        new = self._upload(
            file, asset.resource_type, asset.folder, asset.visibility == "private"
        )
        old_public_id, old_type, old_visibility = (
            asset.public_id,
            asset.resource_type,
            asset.visibility,
        )
        old_url = asset.secure_url
        values = {
            field: getattr(new, field)
            for field in ["public_id", "secure_url", "width", "height", "format"]
        }
        db.session.delete(new)
        db.session.flush()
        for field, value in values.items():
            setattr(asset, field, value)
        from app.models import (
            Page,
            Project,
            Artisan,
            Event,
            BlogPost,
            Gallery,
            ImpactStory,
            OrganizationSetting,
        )

        for model in [Page, Project, Artisan, Event, BlogPost, Gallery, ImpactStory]:
            db.session.execute(
                db.update(model)
                .where(model.cover_image == old_url)
                .values(cover_image=asset.secure_url)
            )
        db.session.execute(
            db.update(OrganizationSetting)
            .where(
                OrganizationSetting.key.in_(["logo", "favicon", "hero_image"]),
                OrganizationSetting.value == old_url,
            )
            .values(value=asset.secure_url)
        )
        if old_public_id:
            cloudinary.uploader.destroy(
                old_public_id,
                resource_type=old_type,
                type="authenticated" if old_visibility == "private" else "upload",
                invalidate=True,
            )
        return asset

    @staticmethod
    def generate_transformed_url(asset, width=960):
        if asset.visibility != "public":
            return ""
        if not asset.public_id or asset.resource_type != "image":
            return asset.secure_url
        return cloudinary.utils.cloudinary_url(
            asset.public_id,
            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
            secure=True,
            width=min(max(int(width), 100), 2000),
            crop="limit",
            quality="auto",
            fetch_format="auto",
        )[0]

    @staticmethod
    def private_url(asset):
        return cloudinary.utils.private_download_url(
            asset.public_id,
            asset.format or "pdf",
            resource_type=asset.resource_type,
            type="authenticated",
            expires_at=__import__("time").time().__int__() + 60,
            attachment=True,
        )

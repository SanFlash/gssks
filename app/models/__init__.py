"""Relational domain models for content, operations, and access control."""

import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now, nullable=False)


role_permissions = db.Table(
    "role_permissions",
    db.Column(
        "role_id", db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    ),
    db.Column(
        "permission_id",
        db.ForeignKey("permission.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(TimestampMixin, db.Model):
    name = db.Column(db.String(40), unique=True, nullable=False)
    permissions = db.relationship(
        "Permission", secondary=role_permissions, lazy="selectin"
    )


class Permission(TimestampMixin, db.Model):
    name = db.Column(db.String(80), unique=True, nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    role = db.relationship("Role", lazy="joined")
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    session_version = db.Column(db.Integer, default=1, nullable=False)

    @property
    def is_active(self):
        return self.active

    def set_password(self, value):
        self.password_hash = generate_password_hash(value)
        self.session_version = (self.session_version or 0) + 1

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)

    def can(self, permission):
        return self.active and (
            self.role.name == "SUPER_ADMIN"
            or any(p.name == permission for p in self.role.permissions)
        )

    def get_id(self):
        return f"{self.id}:{self.session_version}"


class AuditLog(TimestampMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"))
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80))
    ip = db.Column(db.String(64))


class OrganizationSetting(TimestampMixin, db.Model):
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, default="", nullable=False)


class SiteSetting(TimestampMixin, db.Model):
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, default="", nullable=False)


class ContentMixin(TimestampMixin):
    title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(500), default="")
    description = db.Column(db.Text, default="")
    cover_image = db.Column(db.String(1000), default="")
    published = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    seo_title = db.Column(db.String(180), default="")
    seo_description = db.Column(db.String(320), default="")
    keywords = db.Column(db.String(500), default="")


class Page(ContentMixin, db.Model):
    sections = db.relationship(
        "PageSection", backref="page", cascade="all, delete-orphan"
    )


class PageSection(TimestampMixin, db.Model):
    page_id = db.Column(
        db.Integer, db.ForeignKey("page.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)


class ProjectCategory(TimestampMixin, db.Model):
    title = db.Column(db.String(120), unique=True, nullable=False)


class Project(ContentMixin, db.Model):
    category_id = db.Column(
        db.Integer, db.ForeignKey("project_category.id", ondelete="SET NULL")
    )
    category = db.relationship("ProjectCategory")
    location = db.Column(db.String(180), default="")
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Upcoming", nullable=False)
    beneficiary_count = db.Column(db.Integer, default=0, nullable=False)
    target = db.Column(db.Integer, default=0, nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    objectives = db.Column(db.Text, default="")
    activities = db.Column(db.Text, default="")
    outcomes = db.Column(db.Text, default="")
    impact = db.Column(db.Text, default="")
    video = db.Column(db.String(1000), default="")
    featured = db.Column(db.Boolean, default=False)
    images = db.relationship(
        "ProjectImage", backref="project", cascade="all, delete-orphan"
    )
    documents = db.relationship("Document", backref="project")
    __table_args__ = (
        db.CheckConstraint("progress >= 0 AND progress <= 100"),
        db.CheckConstraint("beneficiary_count >= 0"),
    )


class MediaAsset(TimestampMixin, db.Model):
    title = db.Column(db.String(180), nullable=False)
    public_id = db.Column(db.String(255), unique=True)
    secure_url = db.Column(db.String(1000), nullable=False)
    resource_type = db.Column(db.String(30), nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    format = db.Column(db.String(20))
    folder = db.Column(db.String(120), default="gallery")
    tags = db.Column(db.String(500), default="")
    alt_text = db.Column(db.String(250), default="")
    visibility = db.Column(db.String(20), default="public", nullable=False)


class ProjectImage(TimestampMixin, db.Model):
    project_id = db.Column(
        db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    media_id = db.Column(db.Integer, db.ForeignKey("media_asset.id"), nullable=False)
    media = db.relationship("MediaAsset")
    caption = db.Column(db.String(250), default="")
    position = db.Column(db.Integer, default=0)


class ArtisanCategory(TimestampMixin, db.Model):
    title = db.Column(db.String(120), unique=True, nullable=False)


class Artisan(ContentMixin, db.Model):
    category_id = db.Column(
        db.Integer, db.ForeignKey("artisan_category.id", ondelete="SET NULL")
    )
    category = db.relationship("ArtisanCategory")
    location = db.Column(db.String(180), default="")
    skill = db.Column(db.String(180), default="")
    craft = db.Column(db.String(180), default="")
    experience = db.Column(db.String(180), default="")
    products = db.Column(db.Text, default="")
    social_url = db.Column(db.String(1000), default="")


class Event(ContentMixin, db.Model):
    location = db.Column(db.String(180), default="")
    date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    registration_enabled = db.Column(db.Boolean, default=False)
    registration_limit = db.Column(db.Integer, default=50)
    registration_count = db.Column(db.Integer, default=0, nullable=False)
    organizer = db.Column(db.String(180), default="")
    status = db.Column(db.String(30), default="Upcoming")
    __table_args__ = (db.CheckConstraint("registration_count >= 0"),)


class EventRegistration(TimestampMixin, db.Model):
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    event = db.relationship("Event")
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30), default="")
    consent = db.Column(db.Boolean, nullable=False)
    status = db.Column(db.String(30), default="Registered")
    __table_args__ = (db.UniqueConstraint("event_id", "email"),)


class VolunteerApplication(TimestampMixin, db.Model):
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True)
    phone = db.Column(db.String(30), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    occupation = db.Column(db.String(180), default="")
    skills = db.Column(db.Text, nullable=False)
    availability = db.Column(db.String(180), nullable=False)
    areas_of_interest = db.Column(db.String(500), nullable=False)
    message = db.Column(db.Text, default="")
    resume_id = db.Column(db.Integer, db.ForeignKey("media_asset.id"))
    resume = db.relationship("MediaAsset")
    consent = db.Column(db.Boolean, nullable=False)
    status = db.Column(db.String(30), default="Pending", nullable=False)


class Donation(TimestampMixin, db.Model):
    token = db.Column(
        db.String(64), default=lambda: uuid.uuid4().hex, unique=True, nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30), default="")
    pan_encrypted = db.Column(db.Text, default="")
    address = db.Column(db.Text, default="")
    anonymous = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, default="")
    purpose = db.Column(db.String(180), default="Community development")
    amount = db.Column(db.Integer, nullable=False)  # Always integer paise.
    currency = db.Column(db.String(3), default="INR", nullable=False)
    order_id = db.Column(db.String(100), unique=True)
    payment_id = db.Column(db.String(100), unique=True)
    signature = db.Column(db.String(128))
    status = db.Column(db.String(30), default="Created", nullable=False)
    payment_method = db.Column(db.String(40))
    receipt = db.relationship("DonationReceipt", backref="donation", uselist=False)
    __table_args__ = (db.CheckConstraint("amount >= 100"),)


class DonationReceipt(TimestampMixin, db.Model):
    donation_id = db.Column(
        db.Integer, db.ForeignKey("donation.id"), unique=True, nullable=False
    )
    receipt_number = db.Column(db.String(80), unique=True, nullable=False)


class ContactMessage(TimestampMixin, db.Model):
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30), default="")
    subject = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="New", nullable=False)


class BlogCategory(TimestampMixin, db.Model):
    title = db.Column(db.String(120), nullable=False, unique=True)


blog_tags = db.Table(
    "blog_tags",
    db.Column(
        "post_id", db.ForeignKey("blog_post.id", ondelete="CASCADE"), primary_key=True
    ),
    db.Column(
        "tag_id", db.ForeignKey("blog_tag.id", ondelete="CASCADE"), primary_key=True
    ),
)


class BlogTag(TimestampMixin, db.Model):
    title = db.Column(db.String(80), unique=True, nullable=False)


class BlogPost(ContentMixin, db.Model):
    author = db.Column(db.String(120), default="")
    category_id = db.Column(
        db.Integer, db.ForeignKey("blog_category.id", ondelete="SET NULL")
    )
    category = db.relationship("BlogCategory")
    tags = db.relationship("BlogTag", secondary=blog_tags)
    publish_date = db.Column(db.Date)


class Gallery(ContentMixin, db.Model):
    category = db.Column(db.String(80), default="Other")
    media_id = db.Column(db.Integer, db.ForeignKey("media_asset.id"))
    media = db.relationship("MediaAsset")
    artisan_id = db.Column(db.Integer, db.ForeignKey("artisan.id", ondelete="SET NULL"))
    artisan = db.relationship("Artisan")
    event_id = db.Column(db.Integer, db.ForeignKey("event.id", ondelete="SET NULL"))
    location = db.Column(db.String(180), default="")


class ImpactStatistic(TimestampMixin, db.Model):
    title = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Integer, default=0, nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    position = db.Column(db.Integer, default=0)
    __table_args__ = (db.CheckConstraint("value >= 0"),)


class ImpactStory(ContentMixin, db.Model):
    date_label = db.Column(db.String(80), default="")
    position = db.Column(db.Integer, default=0)


class Document(TimestampMixin, db.Model):
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), default="Other Documents")
    year = db.Column(db.Integer)
    description = db.Column(db.Text, default="")
    media_id = db.Column(db.Integer, db.ForeignKey("media_asset.id"), nullable=False)
    media = db.relationship("MediaAsset")
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="SET NULL"))
    visibility = db.Column(db.String(20), default="private", nullable=False)


class SocialLink(TimestampMixin, db.Model):
    title = db.Column(db.String(80), unique=True, nullable=False)
    url = db.Column(db.String(1000), nullable=False)


class NewsletterSubscriber(TimestampMixin, db.Model):
    email = db.Column(db.String(254), unique=True, nullable=False)
    name = db.Column(db.String(120), default="")
    consent = db.Column(db.Boolean, nullable=False)
    unsubscribe_token = db.Column(
        db.String(64), default=lambda: uuid.uuid4().hex, unique=True, nullable=False
    )


class FAQ(TimestampMixin, db.Model):
    question = db.Column(db.String(250), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=False)


class NavigationItem(TimestampMixin, db.Model):
    title = db.Column(db.String(80), nullable=False)
    path = db.Column(db.String(180), nullable=False)
    position = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=True)


class EmailJob(TimestampMixin, db.Model):
    recipient = db.Column(db.String(254), nullable=False)
    subject = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="Pending", nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)

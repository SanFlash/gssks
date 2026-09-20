"""Transactional public form workflows."""

from datetime import date
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import (
    ContactMessage,
    VolunteerApplication,
    Event,
    EventRegistration,
    NewsletterSubscriber,
)
from app.services.email import queue_email
from app.services.media import MediaService


class ApplicationError(ValueError):
    pass


def contact(data):
    record = ContactMessage(
        **{k: data[k] for k in ["name", "email", "phone", "subject", "message"]}
    )
    record.email = record.email.strip().lower()
    db.session.add(record)
    queue_email(
        record.email, "Your enquiry has been received", "contact", name=record.name
    )
    db.session.commit()
    return record


def volunteer(data, resume=None):
    email = data["email"].strip().lower()
    if db.session.scalar(
        db.select(VolunteerApplication).where(VolunteerApplication.email == email)
    ):
        raise ApplicationError(
            "An application for this email already exists. Contact us to update it."
        )
    fields = [
        "name",
        "phone",
        "city",
        "age",
        "occupation",
        "skills",
        "availability",
        "areas_of_interest",
        "message",
        "consent",
    ]
    record = VolunteerApplication(email=email, **{k: data[k] for k in fields})
    if resume and resume.filename:
        record.resume = MediaService().upload_document(resume, private=True)
    db.session.add(record)
    queue_email(
        email,
        "Your volunteer application has been received",
        "volunteer",
        name=record.name,
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ApplicationError("An application for this email already exists.") from exc
    return record


def register_event(event, data):
    if (
        not event.registration_enabled
        or event.status != "Upcoming"
        or (event.date and event.date < date.today())
    ):
        raise ApplicationError("Registration is closed for this event.")
    # Atomic conditional update prevents oversubscription on PostgreSQL AND SQLite.
    result = db.session.execute(
        db.update(Event)
        .where(
            Event.id == event.id,
            Event.registration_enabled.is_(True),
            Event.registration_count < Event.registration_limit,
        )
        .values(registration_count=Event.registration_count + 1)
    )
    if result.rowcount != 1:
        db.session.rollback()
        raise ApplicationError("This event has reached its registration limit.")
    record = EventRegistration(
        event_id=event.id,
        name=data["name"],
        email=data["email"].strip().lower(),
        phone=data["phone"],
        consent=data["consent"],
    )
    db.session.add(record)
    queue_email(
        record.email, "Your event registration", "event", name=record.name, event=event
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ApplicationError(
            "This email is already registered for the event."
        ) from exc
    return record


def subscribe(data):
    email = data["email"].strip().lower()
    record = db.session.scalar(
        db.select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    )
    if not record:
        record = NewsletterSubscriber(
            email=email, name=data.get("name", ""), consent=True
        )
        db.session.add(record)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    return record

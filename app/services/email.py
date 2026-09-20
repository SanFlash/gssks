"""Durable mail outbox. No personal data or reset tokens are printed to logs."""

from flask import current_app, render_template
from flask_mail import Message
from app.extensions import db, mail
from app.models import EmailJob


def queue_email(recipient, subject, template, **context):
    job = EmailJob(
        recipient=recipient,
        subject=subject,
        body=render_template(f"email/{template}.txt", **context),
    )
    db.session.add(job)
    if not current_app.config.get("MAIL_SERVER"):
        current_app.logger.info(
            "Email queued in development outbox; SMTP is not configured"
        )
    return job


def drain_outbox(limit=50):
    if not current_app.config.get("MAIL_SERVER"):
        return 0
    count = 0
    jobs = db.session.scalars(
        db.select(EmailJob)
        .where(EmailJob.status == "Pending", EmailJob.attempts < 5)
        .order_by(EmailJob.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    for job in jobs:
        job.attempts += 1
        try:
            mail.send(
                Message(subject=job.subject, recipients=[job.recipient], body=job.body)
            )
            job.status = "Sent"
            count += 1
        except Exception:
            current_app.logger.warning(
                "SMTP delivery failed; message retained in outbox"
            )
        db.session.commit()
    return count

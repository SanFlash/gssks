"""One-time deployment account creation without public bootstrap routes."""
from email_validator import validate_email, EmailNotValidError
from app.extensions import db
from app.models import User, Role, AuditLog


def bootstrap_admin(email, password):
    """Create the first admin only. Never reset accounts on restart."""
    if db.session.scalar(db.select(User.id).join(Role).where(Role.name == 'SUPER_ADMIN')):
        return False
    if not email and not password:
        return False
    try:
        email = validate_email(email or '', check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError('INITIAL_ADMIN_EMAIL must be a valid email address.') from None
    if not password or not 12 <= len(password) <= 128:
        raise ValueError('INITIAL_ADMIN_PASSWORD must contain 12–128 characters.')
    if db.session.scalar(db.select(User.id).where(User.email == email)):
        raise ValueError('Initial admin email already belongs to an account; use another email.')
    role = db.session.scalar(db.select(Role).where(Role.name == 'SUPER_ADMIN'))
    if not role:
        raise ValueError('Initialize organization roles before creating an admin.')
    user = User(name='Organization administrator', email=email, role=role, is_demo=False)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(AuditLog(user_id=user.id, action='create deployment admin', entity='User', entity_id=str(user.id)))
    db.session.commit()
    return True

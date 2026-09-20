"""Validated browser forms reused by the JSON API."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    BooleanField,
    IntegerField,
    SelectField,
    DecimalField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    NumberRange,
    Optional,
    Regexp,
    EqualTo,
)

email_rules = [DataRequired(), Email(check_deliverability=False), Length(max=254)]
phone_rules = [
    Optional(),
    Regexp(r"^[+0-9()\- ]{7,25}$", message="Enter a valid phone number."),
]


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Sign in securely")


class ForgotForm(FlaskForm):
    email = StringField("Email", validators=email_rules)
    submit = SubmitField("Send reset instructions")


class ResetForm(FlaskForm):
    password = PasswordField(
        "New password", validators=[DataRequired(), Length(min=12, max=128)]
    )
    confirmation = PasswordField("Confirm password", validators=[EqualTo("password")])
    submit = SubmitField("Update password")


class ContactForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=email_rules)
    phone = StringField("Phone", validators=phone_rules)
    subject = StringField("Subject", validators=[DataRequired(), Length(max=180)])
    message = TextAreaField(
        "Message", validators=[DataRequired(), Length(min=10, max=5000)]
    )
    consent = BooleanField(
        "I agree to the use of my details to respond to this enquiry.",
        validators=[DataRequired()],
    )
    website = StringField("Leave blank", validators=[Optional(), Length(max=0)])
    submit = SubmitField("Send enquiry")


class VolunteerForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=email_rules)
    phone = StringField("Phone", validators=[DataRequired(), *phone_rules])
    city = StringField("City", validators=[DataRequired(), Length(max=120)])
    age = IntegerField(
        "Age (18 or older)", validators=[DataRequired(), NumberRange(min=18, max=120)]
    )
    occupation = StringField("Occupation", validators=[Optional(), Length(max=180)])
    skills = TextAreaField(
        "Skills you can share", validators=[DataRequired(), Length(max=3000)]
    )
    availability = SelectField(
        "Availability",
        choices=["Weekdays", "Weekends", "Flexible", "Occasional events"],
    )
    areas_of_interest = SelectField(
        "Area of interest",
        choices=[
            "Teaching",
            "Women Empowerment",
            "Community Work",
            "Events",
            "Digital Marketing",
            "Social Media",
            "Photography",
            "Fundraising",
            "Technology",
            "Research",
            "Craft Promotion",
            "Other",
        ],
    )
    message = TextAreaField(
        "Anything else you would like to share?",
        validators=[Optional(), Length(max=3000)],
    )
    resume = FileField(
        "Resume (optional PDF, up to 5 MB)", validators=[FileAllowed(["pdf"])]
    )
    consent = BooleanField(
        "I consent to storing my application and being contacted about volunteering.",
        validators=[DataRequired()],
    )
    website = StringField("Leave blank", validators=[Optional(), Length(max=0)])
    submit = SubmitField("Submit application")


class EventForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=email_rules)
    phone = StringField("Phone", validators=phone_rules)
    consent = BooleanField(
        "I consent to receiving information about this event.",
        validators=[DataRequired()],
    )
    submit = SubmitField("Register for this event")


class NewsletterForm(FlaskForm):
    email = StringField("Email address", validators=email_rules)
    name = StringField("Name (optional)", validators=[Optional(), Length(max=120)])
    consent = BooleanField(
        "Send me updates. I can unsubscribe at any time.", validators=[DataRequired()]
    )
    submit = SubmitField("Subscribe")


class DonationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=email_rules)
    phone = StringField("Phone", validators=phone_rules)
    amount = DecimalField(
        "Donation amount (₹)",
        places=2,
        validators=[DataRequired(), NumberRange(min=1, max=1000000)],
    )
    pan = StringField(
        "PAN (optional)", validators=[Optional(), Regexp(r"^[A-Z]{5}[0-9]{4}[A-Z]$")]
    )
    address = TextAreaField(
        "Address (optional)", validators=[Optional(), Length(max=1000)]
    )
    anonymous = BooleanField("Keep my name private in public acknowledgements")
    message = TextAreaField(
        "Message (optional)", validators=[Optional(), Length(max=2000)]
    )
    consent = BooleanField(
        "I agree to the privacy policy and donation terms.", validators=[DataRequired()]
    )
    submit = SubmitField("Continue to secure payment")

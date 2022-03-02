import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from flask_mail import Mail

app = Flask(__name__)
app.config.from_object("pyproject.config.Config")

db = SQLAlchemy(app)

# email
# If using STARTTLS with MAIL_USE_TLS = True, then use MAIL_PORT = 587
# If using SSL/TLS directly with MAIL_USE_SSL = True, then use MAIL_PORT = 465
# Enable either STARTTLS or SSL/TLS, not both.
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
email_settings = {
    # email server
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": MAIL_USERNAME,
    "MAIL_PASSWORD": os.environ.get('MAIL_PASSWORD'),
    "MAIL_DEBUG": False,
}

app.config.update(email_settings)
mail = Mail(app)

from pyproject import views  # Needs to be at the bottom of the file # noqa

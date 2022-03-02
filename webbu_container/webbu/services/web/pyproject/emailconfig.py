import os
from datetime import datetime

import flask
from flask_mail import Message
from pyproject import mail, app, MAIL_USERNAME


ENVIRON = os.environ.get('FLASK_ENV')
WEBBU_URL = os.environ.get('BASE_URL')
PROD_LOCALHOST = True if os.environ.get('PROD_LOCALHOST') == 'true' else False
FLASK_PORT = os.environ.get('FLASK_RUN_PORT')

EMAIL_ADDRESS = "webbuapp@gmail.com"
FEEDBACK_LINE = f"Give us feedback at {EMAIL_ADDRESS}"
TEAM_LINE = "The Webbu Team"


def get_host():

    host = WEBBU_URL
    if ENVIRON == 'development':
        host = f'http://localhost:{FLASK_PORT}'
    if ENVIRON == 'production' and PROD_LOCALHOST:
        host = f'http://localhost'

    return host


def send_email(subject, recipients, text_body, html_body, reason=''):
    with app.app_context():
        try:
            print(f'send_email to {recipients} r: {reason}')
            msg = Message(subject, sender=MAIL_USERNAME, recipients=recipients)
            msg.body = text_body
            msg.html = html_body
            mail.send(msg)
            return True
        except Exception as e:
            print(f'send_email to {recipients} failed. error: {e}')
            return False


def send_email_login_link(email, token1, token2, extra_msg=None, email_title=None, continue_on_page=None):
    '''
    Send the magic link to the email so the user can log in

    Add the username and timestamp so that gmail does not
    think it's the same email every time
    '''
    print(f'send_email_login_link: {email}')
    if email_title is None:
        subject = 'Webbu Magic Link'
    else:
        subject = email_title

    email_user_part = email.split('@')[0]
    timestamp = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    email_host = get_host()

    link = f'{email_host}/login_link?token1={token1}&token2={token2}&email={email}&continue_on_page={continue_on_page}'

    if extra_msg is None:
        extra_msg = ''

    text_body = f'''\
    Hi {email_user_part},

    {extra_msg}
    Here is your link to sign in to Webbu:

    {link}

    This link will only work once but you can get a new one at https://webbu.app/login

    Enjoy!
    {TEAM_LINE}
    {FEEDBACK_LINE}
    {timestamp}
'''

    html_version = flask.render_template(
        'email_login_link.html',
        email_user_part=email_user_part,
        extra_msg=extra_msg,
        link=link,
        TEAM_LINE=TEAM_LINE,
        FEEDBACK_LINE=FEEDBACK_LINE,
        timestamp=timestamp,
        font_family="font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Ubuntu,sans-serif",
    )

    send_email(subject, [email], text_body, html_version, reason='login_link')




























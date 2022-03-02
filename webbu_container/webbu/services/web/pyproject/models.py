from datetime import datetime

from sqlalchemy import func

from pyproject import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)

    # all of the following can be nullable because user can be registered with just the email
    username = db.Column(db.String(128), unique=True, nullable=False)
    first_name = db.Column(db.String(128), default='', unique=False, nullable=True)
    last_name = db.Column(db.String(128), default='', unique=False, nullable=True)
    pronoun = db.Column(db.String(128), unique=False, default='', nullable=True)
    receive_newsletter = db.Column(db.Boolean(), default=False, nullable=True)
    email_verified = db.Column(db.Boolean(), default=False, nullable=False)
    country = db.Column(db.String(3), default='', nullable=True)  # 2-letter country code
    city = db.Column(db.String(128), default='', nullable=True)
    language = db.Column(db.String(128), default='', nullable=True)

    # date columns. Careful: https://docs.sqlalchemy.org/en/13/core/defaults.html#marking-implicitly-generated-values-timestamps-and-triggered-columns
    date_joined = db.Column(db.DateTime(), default=func.now(), nullable=False)  # func.now() is preferred over datetime.utcnow (python func has funny defaults)
    date_updated = db.Column(db.DateTime(), nullable=True, onupdate=func.now())

    # values: TODO
    tier = db.Column(db.String(12), default='', nullable=False)

    # users can sign in via google or email. Adding the password option in case they opt-in for it
    # since emails can take long/fail and some people dont like using google signin
    # guide: https://nitratine.net/blog/post/how-to-hash-passwords-in-python/
    password_hash_hex = db.Column(db.String(64), default='notset', nullable=True)
    salt_hex = db.Column(db.String(64), default='notset', nullable=True)

    # invite other people and get discounts (TODO)
    referral_code = db.Column(db.String(10), unique=False, nullable=True)
    invited_by_code = db.Column(db.String(10), unique=False, nullable=True)

    configs = db.Column(db.String(1000), unique=False, nullable=True)  # json settings/configs/preferences

    def __init__(self, email, username=None, first_name=None, last_name=None, pronoun=None, receive_newsletter=None, email_verified=False, tier='freetrial', referral_code=None, invited_by_code=None):
        self.email = email
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.pronoun = pronoun
        self.receive_newsletter = receive_newsletter
        self.email_verified = email_verified
        self.tier = tier
        self.referral_code = referral_code

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RememberMeToken(db.Model):
    __tablename__ = "tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    token = db.Column(db.String(256))
    token_series_id = db.Column(db.String(256))
    date_created = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, user_id, token, token_series_id):
        self.user_id = user_id
        self.token = token
        self.token_series_id = token_series_id

    def as_dict(self):
        return {c.user_id: getattr(self, c.user_id) for c in self.__table__.columns}


class UserEvent(db.Model):
    '''
    Each row represents an interaction or action made by the user
    '''
    __tablename__ = "user_events"

    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(70), unique=False, nullable=False)
    user_id = db.Column(db.Integer, unique=False, nullable=True)  # can be empty if not logged in
    guest_id = db.Column(db.String(128), unique=False, nullable=True)

    # user_ip is important because some actions can be done anonymously (so user_id is None)
    # user_ip can also be None if the action is started by the server
    user_ip = db.Column(db.String(47), unique=False, nullable=True)  # max ipv6 string repr is 45 chars
    event_details = db.Column(db.String(400), unique=False, nullable=True)  # parameters as a json object
    date_created = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    browser = db.Column(db.String(12), unique=False, nullable=True)
    is_mobile = db.Column(db.Boolean(), default=False, nullable=True)
    operating_system = db.Column(db.String(12), unique=False, nullable=True)

    useragent_id = db.Column(db.Integer, unique=False, nullable=True)
    referrer_id = db.Column(db.Integer, unique=False, nullable=True)  # a url, either internal or external

    def __init__(self, event_name, user_id, guest_id, user_ip, browser, is_mobile, operating_system, referrer_id, useragent_id, event_details):
        self.event_name = event_name
        self.user_id = user_id
        self.guest_id = guest_id
        self.user_ip = user_ip
        self.browser = browser
        self.is_mobile = is_mobile
        self.operating_system = operating_system
        self.referrer_id = referrer_id
        self.useragent_id = useragent_id
        self.event_details = event_details

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserAgent(db.Model):
    '''
    Tracking user agents separately so that they are not duplicated in user_events
    '''
    __tablename__ = "user_agents"

    id = db.Column(db.Integer, primary_key=True)
    user_agent = db.Column(db.String(300), unique=True, nullable=False, index=True)

    def __init__(self, user_agent):
        self.user_agent = user_agent

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Referrer(db.Model):
    '''
    Tracking separately separately so that they take less space in conversion_event (referenced by id)
    '''
    __tablename__ = "referrers"

    id = db.Column(db.Integer, primary_key=True)
    referrer = db.Column(db.String(200), unique=True, nullable=False, index=True)

    def __init__(self, referrer):
        self.referrer = referrer

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PageView(db.Model):

    """
    Record page views
    """
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, unique=False, nullable=True)
    page_name = db.Column(db.String(40), unique=False, nullable=True)
    user_id = db.Column(db.Integer, unique=False, nullable=True)  # can be empty if not logged in
    guest_id = db.Column(db.String(128), unique=False, nullable=True, index=True)

    user_ip = db.Column(db.String(47), unique=False, nullable=True)  # max ipv6 string repr is 45 chars
    browser = db.Column(db.String(12), unique=False, nullable=True)
    is_mobile = db.Column(db.Boolean(), default=False, nullable=True)
    operating_system = db.Column(db.String(12), unique=False, nullable=True)

    useragent_id = db.Column(db.Integer, unique=False, nullable=True)
    # track how the user moves from page to page using referrer
    referrer_id = db.Column(db.Integer, unique=False, nullable=True)

    # details = db.Column(db.String(500), unique=False, nullable=False)

    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, page_id, page_name, user_id, guest_id, user_ip, browser, is_mobile, operating_system, useragent_id, referrer_id):
        self.page_id = page_id
        self.page_name = page_name
        self.user_id = user_id
        self.guest_id = guest_id

        self.user_ip = user_ip
        self.browser = browser
        self.is_mobile = is_mobile
        self.operating_system = operating_system

        self.useragent_id = useragent_id
        self.referrer_id = referrer_id

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    visible_id = db.Column(db.String(64), unique=True, nullable=False)
    steps = db.Column(db.String(2000), unique=False, nullable=False)
    author_id = db.Column(db.Integer, unique=False, nullable=False)
    hosts = db.Column(db.String(1000), unique=False, nullable=True)
    deleted = db.Column(db.Boolean(), default=False)
    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, visible_id, steps, author_id, hosts):
        self.visible_id = visible_id
        self.steps = steps
        self.author_id = author_id
        self.hosts = hosts

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SkillInstruction(db.Model):
    __tablename__ = "skill_instructions"

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer)
    instruction = db.Column(db.String(2000), index=True)
    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, skill_id, instruction):
        self.skill_id = skill_id
        self.instruction = instruction

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SkillViewCounts(db.Model):
    __tablename__ = "skill_view_counts"

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, index=True)
    view_count = db.Column(db.Integer)
    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, skill_id, view_count):
        self.skill_id = skill_id
        self.view_count = view_count

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SkillExecutions(db.Model):
    __tablename__ = "skill_executions"

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, index=True)
    exec_by_user_id = db.Column(db.Integer)
    exec_by_guest_id = db.Column(db.String(128))
    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, skill_id, exec_by_user_id):
        self.skill_id = skill_id
        self.exec_by_user_id = exec_by_user_id

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SkillVote(db.Model):
    __tablename__ = "skill_votes"

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, index=True)
    user_id = db.Column(db.Integer)
    guest_id = db.Column(db.String(128))
    vote = db.Column(db.Integer)
    current_url = db.Column(db.String(300))
    date = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, skill_id, vote, user_id, guest_id, current_url):
        self.skill_id = skill_id
        self.vote = vote
        self.user_id = user_id
        self.guest_id = guest_id
        self.current_url = current_url

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}











import json
import secrets
import random
import sqlite3

from sqlalchemy import exc, func
import psycopg2


from pyproject import db
from pyproject.models import User, RememberMeToken, UserAgent, Skill, SkillInstruction, Referrer, UserEvent, PageView, SkillVote
import pyproject.emailconfig as emailconfig


def generate_remember_me_token(user_id):
    '''
    Remember me tokens and mechanism:
    based on: https://stackoverflow.com/questions/244882/what-is-the-best-way-to-implement-remember-me-for-a-website
    but not entirely:

    When the user logs in/registers:
        - a login cookie with a token is issued
        - The login cookie contains a series identifier (a string) and a token.
            The series and token are unguessable random numbers from a suitably large space.
            Both are stored together in a database table, the token is hashed (sha256 is fine).
        - When a non-logged-in user visits the site and presents a login cookie, the series identifier is looked up in the database.
            if the series identifier is present and the hash of the token matches the hash for that series identifier, the user is considered authenticated.

    The series identifier prevents DOS attacks because we can detect that someone is guessing (brute-force)
    if many attempts are made in which the the series identifier is not the right one for the token
    '''
    print(f'generate token for: {user_id}')
    token = secrets.token_urlsafe(32)  # on avg. each byte results in approximately 1.3 characters
    token_series_id = secrets.token_urlsafe(32)

    success = save_remember_me_token(user_id, token, token_series_id)

    return success, token, token_series_id


def save_remember_me_token(user_id, token, token_series_id):

    new_token = RememberMeToken(user_id, token, token_series_id)
    try:
        db.session.add(new_token)
        db.session.commit()
        print(f'save_token: Saved token for user: {user_id}')
        return True
    except Exception as e:
        print(f'save_token: Failed saving token for user: {user_id}: {e}')
        db.session.rollback()
        return False


def generate_username(email):
    email_before_at = email.split('@')[0]  # fer@host.com -> fer
    return email_before_at + str(random.randrange(1000, 9999))


def get_field_name(text):
    possible_fields = ["email", "username", "first_name", "last_name"]
    for field in possible_fields:
        if field in text:
            return field

    return ''


def add_user_email_only(email, first_name=None, last_name=None, email_verified=False, continue_on_page=''):
    email = email.lower()
    username = generate_username(email)
    referral_code = secrets.token_urlsafe(7)[:9]  # on avg. each byte results in approximately 1.3 chars, db field is 10
    new_user = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        email_verified=email_verified,
        referral_code=referral_code
    )

    print(f'add_user_email_only: {email} tmp_user: {username}')
    try:
        db.session.add(new_user)
        db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        error_msg = f'Failed adding user'
        error_code = ''
        field_name = get_field_name(str(e.orig))

        unique_violation = False
        if isinstance(e.orig, psycopg2.errors.UniqueViolation):
            unique_violation = True
        if isinstance(e.orig, sqlite3.IntegrityError):
            if 'UNIQUE' in str(e):
                unique_violation = True

        if unique_violation:
            # if it's a unique violation, it could be because the email has already been registered
            # via add_user_email_only()
            # In this case, check if the user was recently created and if so send them a magic link to log in

            if 'email' == field_name:
                create_login_magic_link(email, continue_on_page=continue_on_page)
                msg = f"""\
Check your email ({email}) for the magic link to login.
If you can't find it, check the spam folder or the Promotions tab and drag the email into to the primary inbox"""
                return {'added_email_token': email, 'msg': msg}, None
            else:
                error_code = f'non-unique {field_name}'
                print('add_user: SHOULDNT_HAPPEN fix non-unique {field_name}. Exc: {e}')

        elif isinstance(e.orig, psycopg2.errors.NotNullViolation):
            error_msg = f"Field '{field_name}' cannot be empty"
            error_code = f'null field {field_name}'

        print(f"add_user: {email} field='{field_name}' type: {type(e)} subt: {type(e.orig)} error: {e}")
        return {'error': error_msg, 'error_code': error_code}, None
    except Exception as e:
        # We don't wait for this response, so it does not need to be user friendly
        db.session.rollback()
        print(f"Failed registering email only: {email}. Exception: {e}")
        return {'error': f"Woops! We failed saving the data for {email}. Please try again"}, None

    # after creating the user, create session the tokens
    success, token, token_series_id = generate_remember_me_token(new_user.id)
    if success:
        # send an email so that they verify their email address
        # also important for the workflow: notloggedin-payment -> auto-register -> verify-email
        create_login_magic_link(email)
        return {'added': email}, (token, token_series_id, username, new_user)
    else:
        print(f'add_user_email_only: {email} failed to save session tokens')
        return {'error': f"Woops! We failed logging you in ({email}). Please try again"}, None


def create_login_magic_link(email, email_msg=None, email_title=None, continue_on_page=None):
    email = email.lower()
    print(f'create_login_magic_link: {email}')
    user = find_user_by_email(email)

    success, token, token_series_id = generate_remember_me_token(user.id)
    if success:
        emailconfig.send_email_login_link(user.email, token, token_series_id, extra_msg=email_msg, email_title=email_title, continue_on_page=continue_on_page)
        return True

    return False


def email_matches_token(email, input_token, input_token_series_id, delete_if_found=False, reason='email_matches_token'):
    '''
    Checks whether the provided tokens are valid for the email given

    if delete_if_found is True, then we delete the tokens after the check.
    This is useful for the email magic link tokens that are to be used just once
    But it might be better to just delete them periodically in case the
    user clicks the link twice
    '''
    email = email.lower()

    try:
        user = db.session.query(User).filter_by(email=email).one()

        found_token = db.session.query(RememberMeToken).filter_by(
            user_id=user.id,
            token=input_token,
            token_series_id=input_token_series_id).one()

        if found_token:
            if reason is None:
                reason = 'email_matches_token'

            print(f"{reason}: {email} is loggedin-w-tok")
            if delete_if_found:
                try:
                    db.session.delete(found_token)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f'{reason}: failed deleting temp token for {email}. e: {e}')

            return True, user

    except Exception as e:
        print(f"{reason}: error checking tokens: '{email}' r: {reason}. e: {e}")

    return False, None


def find_user_by_id(user_id, reason=''):
    try:
        user = db.session.query(User).filter_by(id=user_id).one()
        return user
    except Exception as e:
        print(f"find_user_by_id {reason}: Could not find id: {user_id}. e: {e}")
        return None


def find_user_by_email(email, reason=''):
    email = email.lower()
    try:
        user = db.session.query(User).filter_by(email=email).one()
        return user
    except Exception as e:
        print(f"find_user_by_email {reason}: Could not find email: {email}. e: {e}")
        return None


def find_user_by_username(username, reason=''):
    try:
        user = db.session.query(User).filter_by(username=username).one()
        return user
    except Exception:
        # print(f"find_user_by_username {reason}: Could not find user: {username}. e: {e}")
        return None


def find_user_by_referral_code(invite_code):
    try:
        users = db.session.query(User).filter_by(referral_code=invite_code).all()
        # TODO: in the future, make sure it's unique per user
        if len(users) > 0:
            return users[0]
    except Exception:
        # print(f"find_user_by_referral_code {reason}: Could not find user: {username}. e: {e}")
        pass

    return None


def set_email_as_verified(user):

    if user.email_verified is True:
        return

    user.email_verified = True
    try:
        db.session.commit()
        print(f'set_email_as_verified: success for {user.email}')
    except Exception as e:
        db.session.rollback()
        print(f'set_email_as_verified: error for {user.email}. e: {e}')


def record_user_event(event_name, user_id, guest_id, req_info, event_params):

    user_agent = req_info['user_agent'][:300]  # truncate if longer than db limit
    user_agent_id = ''
    if user_agent_obj := find_or_save_user_agent(user_agent):
        user_agent_id = user_agent_obj.id

    referrer = req_info['referrer'][:200]
    referrer_id = 0
    if referrer_obj := find_or_save_referrer(referrer):
        referrer_id = referrer_obj.id

    event_params_json = json.dumps(event_params)
    new_event = UserEvent(
        event_name,
        user_id,  # could be None if not logged in
        guest_id,
        req_info['user_ip'],
        req_info['browser'],
        req_info['is_mobile'],
        req_info['operating_system'],
        referrer_id,
        user_agent_id,
        event_params_json)
    try:
        db.session.add(new_event)
        db.session.commit()
        return True
    except Exception as e:
        print(f'Failed saving user_event: {event_name}: {e}')
        db.session.rollback()
        return False


def save_user_agent(user_agent):
    '''
    Record a user agent
    '''
    user_agent = user_agent[:300]
    user_agent_obj = UserAgent(user_agent)

    try:
        db.session.add(user_agent_obj)
        db.session.commit()
        return user_agent_obj
    except Exception as e:
        print(f'save_user_agent failed: {user_agent}: {e}')
        db.session.rollback()
        return None


def save_referrer(referrer):
    '''
    Record a referrer
    '''
    referrer = referrer[:200]
    referrer_obj = Referrer(referrer)

    try:
        db.session.add(referrer_obj)
        db.session.commit()
        return referrer_obj
    except Exception as e:
        print(f'save_referrer failed: {referrer}: {e}')
        db.session.rollback()
        return None


def find_or_save_user_agent(user_agent):
    try:
        # .first() returns None if not found vs .one() that throws if not found or more than 1 found
        user_agent_obj = db.session.query(UserAgent).filter_by(user_agent=user_agent).first()
        if user_agent_obj:
            # print(f"find_or_save_user_agent: found {user_agent_obj.id}")
            return user_agent_obj
        else:
            # if not already saved, save it
            # print(f"find_or_save_user_agent: not found, saving {user_agent}")
            user_agent_obj = save_user_agent(user_agent)
            return user_agent_obj

    except Exception as e:
        print(f"find_or_save_user_agent: error while finding: {user_agent}. e: {e}")
        return None


def find_or_save_referrer(referrer):
    try:
        # .first() returns None if not found vs .one() that throws if not found or more than 1 found
        referrer_obj = db.session.query(Referrer).filter_by(referrer=referrer).first()
        if referrer_obj:
            # print(f"find_or_save_referrer: found {referrer_obj.id}")
            return referrer_obj
        else:
            # if not already saved, save it
            # print(f"find_or_save_referrer: not found, saving {referrer}")
            referrer_obj = save_referrer(referrer)
            return referrer_obj

    except Exception as e:
        print(f"find_or_save_referrer: error while finding: {referrer}. e: {e}")
        return None


def expunge_object(object_2_expunge):
    '''
    Needed for objects that are cached
    expunge the user, so we can still access it after the db session is closed
    read more: https://stackoverflow.com/questions/15397680/detaching-sqlalchemy-instance-so-no-refresh-happens
    '''
    db.session.expunge(object_2_expunge)


def record_page_view(page, page_name, user_id, guest_id, user_ip, browser, is_mobile, operating_system, user_agent, referrer):

    page = page[:200]
    page_id = 0
    if page_obj := find_or_save_referrer(page):
        page_id = page_obj.id

    user_agent = user_agent[:300]  # truncate if longer
    user_agent_id = 0
    if user_agent_obj := find_or_save_user_agent(user_agent):
        user_agent_id = user_agent_obj.id

    referrer = referrer[:200]
    referrer_id = 0
    if referrer_obj := find_or_save_referrer(referrer):
        referrer_id = referrer_obj.id

    page_view = PageView(
        page_id,
        page_name,
        user_id,
        guest_id,
        user_ip,
        browser,
        is_mobile,
        operating_system,
        user_agent_id,
        referrer_id
    )

    try:
        db.session.add(page_view)
        db.session.commit()
        return True
    except Exception as e:
        print(f'record_page_view: Failed saving p: {page} u: {user_id} g_id: {guest_id} ip: {user_ip} : {e}')
        db.session.rollback()
        return False


# skills ------------------------------

def save_new_skill(steps, instructions, author_id, hosts):
    print(f"save_new_skill: {steps}")

    skill_obj = None

    visible_id = secrets.token_urlsafe(10)  # on avg. each byte results in approximately 1.3 characters
    visible_id = f"@{visible_id}"  # all visible ids will start with @

    try:
        skill_obj = Skill(visible_id, steps, author_id, hosts)
        db.session.add(skill_obj)
        db.session.commit()

    except Exception as e:
        print(f'save_new_skill: failed saving: {skill_obj}: {e}')
        db.session.rollback()
        return None

    for instruction in instructions:
        save_skill_instruction(skill_obj.id, instruction)

    return skill_obj


def save_skill_instruction(skill_id, instruction):
    try:
        new_obj = SkillInstruction(skill_id, instruction)
        db.session.add(new_obj)
        db.session.commit()
        return new_obj

    except Exception as e:
        db.session.rollback()
        print(f'save_skill_instruction failed: s: {skill_id} i: {instruction} e: {e}')
        return None


def search_skills(text, current_url):
    # TODO: add variable support ("make the background $color")
    already_added_skills = set()

    skill_text_tuples = search_skill_by_text_exact(text)
    if len(skill_text_tuples) > 10:  # enough
        return skill_text_tuples

    for skill_tuple in skill_text_tuples:
        already_added_skills.add(skill_tuple[0].id)

    skill_text_tuples_2 = search_skill_by_text_partial(text, already_added_skills)
    skill_text_tuples.extend(skill_text_tuples_2)

    return skill_text_tuples


def search_skill_by_text_exact(text):

    text_lower = text.lower()
    skill_text_tuples = None
    try:
        skill_text_tuples = db.session.query(Skill, SkillInstruction.instruction).filter(
            Skill.deleted == False,  # noqa
            func.lower(SkillInstruction.instruction) == text_lower,
            SkillInstruction.skill_id == Skill.id
        ).all()

        print(f"search_skill_by_text_exact: found: {len(skill_text_tuples)}")

    except Exception as e:
        print(f"search_skill_by_text_exact: Error: {e}")
        return None

    # TODO: don't allow one skill to have repeated instruction texts
    # so that we don't need to remove duplicates here

    return skill_text_tuples


def search_skill_by_text_partial_in_db(text):

    try:
        skill_text_tuples = db.session.query(Skill, SkillInstruction.instruction).filter(
            Skill.deleted == False,  # noqa
            SkillInstruction.instruction.ilike(f"%{text}%"),
            SkillInstruction.skill_id == Skill.id
        ).all()

        print(f"search_skill_partial: found: {len(skill_text_tuples)}")
        return skill_text_tuples
    except Exception as e:
        print(f"search_skill_partial: failed e: {e}")
        return None


def search_skill_by_text_partial(text, already_added_skills):
    # try to find partial matches in the DB using groups of 1, 2, 3, 4, and 5 words

    words = text.split(" ")
    group_size = min(5, len(words))  # if text has 3 words, no point in trying to group 5 words

    start_idx = 0
    end_idx = group_size

    found_tuples = []  # avoid duplicates (set) but keep order of insertion
    print(f"search_skill_by_text_partial: t: {text}")

    # start from biggest group size, so that bigger partial matches are preferred over shorter ones.
    while group_size > 0:
        selected_words = words[start_idx:end_idx]
        print(f"search_skill_by_text_partial: s: {start_idx} e: {end_idx} w: {selected_words}")
        sub_text = ' '.join(selected_words)

        new_results = search_skill_by_text_partial_in_db(sub_text)
        if new_results is not None and len(new_results) > 0:
            for skill, text in new_results:
                if skill.id not in already_added_skills:
                    found_tuples.append((skill, text))
                    already_added_skills.add(skill.id)

        if len(found_tuples) > 10:  # enough matches
            break

        start_idx += 1
        end_idx += 1

        if end_idx > len(text):
            break

        group_size -= 1

    return found_tuples


def get_user_skills(user_id):

    try:
        skill_text_tuples = db.session.query(Skill, func.max(SkillInstruction.instruction)).filter(
            Skill.deleted == False,  # noqa
            SkillInstruction.skill_id == Skill.id
        ).group_by(Skill.id).all()  # only get one instruction per skill

        print(f"get_user_skills: found: {len(skill_text_tuples)}")
        return skill_text_tuples
    except Exception as e:
        print(f"get_user_skills: Error: {e}")
        return None


def find_skill_by_visible_id(visible_id):
    try:
        skill_obj = db.session.query(Skill).filter(
            Skill.deleted == False,  # noqa
            Skill.visible_id == visible_id,
        ).one()

        print(f"find_skill_by_visible_id: found v_id: {visible_id} id: {skill_obj.id}")
        return skill_obj
    except Exception as e:
        print(f"find_skill_by_visible_id: failed finding v_id: {visible_id} e: {e}")
        return None


def find_skill_tuples_by_visible_id(visible_id):
    try:
        skill_text_tuples = db.session.query(Skill, SkillInstruction.instruction).filter(
            Skill.deleted == False,  # noqa
            Skill.visible_id == visible_id,
            SkillInstruction.skill_id == Skill.id,
        ).all()

        print(f"find_skill_tuples_by_visible_id: found: {len(skill_text_tuples)}")
        return skill_text_tuples
    except Exception as e:
        print(f"find_skill_tuples_by_visible_id: failed finding v_id: {visible_id} e: {e}")
        return None


def update_skill(skill_obj, steps, instructions, hosts):

    changed_skill = False
    # 1. if steps differ, update
    if skill_obj.steps != steps:
        skill_obj.steps = steps
        changed_skill = True

    # 2. if hosts differ, update
    if skill_obj.hosts != hosts:
        skill_obj.hosts = hosts
        changed_skill = True

    if changed_skill:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"update_skill: failed updating skill_obj id: {skill_obj.id} e: {e}")
            return None

    update_skill_instructions(skill_obj.id, instructions)
    return skill_obj


def delete_all_instructs_for_a_skill(skill_id):
    try:
        _ = db.session.query(SkillInstruction).filter(
            Skill.deleted == False,  # noqa
            SkillInstruction.skill_id == skill_id,
        ).delete()
        db.session.commit()

        return True

    except Exception as e:
        db.session.rollback()
        print(f'delete_all_instructs_for_a_skill failed: s: {skill_id} e: {e}')
        return False


def update_skill_instructions(skill_id, instructions):
    # if instructions differ, update them
    # a. delete all existing instructions for this skill
    # b. add new instructions

    delete_all_instructs_for_a_skill(skill_id)

    for instruc in instructions:
        save_skill_instruction(skill_id, instruc)

    print(f"update_skill_instructions: done s: {skill_id}")


def delete_skill(skill_obj):
    if not skill_obj:
        return False

    try:
        skill_obj.deleted = True
        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        print(f'delete_skill: failed: s: {skill_obj.visible_id} e: {e}')
        return False


def vote_skill(skill_id, vote, user_id, guest_id, current_url):

    current_url = current_url[:300]  # db field limit

    vote_obj = SkillVote(
        skill_id,
        vote,
        user_id,  # could be None if not logged in
        guest_id,
        current_url)
    try:
        db.session.add(vote_obj)
        db.session.commit()
        return True
    except Exception as e:
        print(f'vote_skill: failed saving vote: s: {skill_id} v: {vote} u: {user_id} g: {guest_id} e: {e}')
        db.session.rollback()
        return False





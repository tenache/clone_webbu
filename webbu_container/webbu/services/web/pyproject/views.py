import datetime
import json
import os
import secrets

from flask import jsonify, render_template, request, redirect
import flask
from flask_cors import CORS
# import spacy
# import stripe

from pyproject import app
import pyproject.db_interface as db_interface

CORS(app)  # Enable CORS for Chrome extension and external callers


EMAIL_COOKIE = 'ck_email'
USERNAME_COOKIE = 'ck_username'
TOKEN_COOKIE = "ck_remember_me_token"
TOKEN_COOKIE_SERIES_ID = "ck_remember_me_token_series_id"
GUEST_ID_COOKIE = 'ck_guest_id'
ENVIRON = os.environ.get('FLASK_ENV')


# override via: $ STRIPE_TEST_MODE=true docker-compose -f docker-compose.prod.yml up
USE_STRIPE_TEST_MODE = True if os.environ.get('STRIPE_TEST_MODE') == 'true' else False
NGROK_WEBHOOK = True if os.environ.get('NGROK_WEBHOOK') == 'true' else False
PROD_LOCALHOST = True if os.environ.get('PROD_LOCALHOST') == 'true' else False
webbu_url = os.environ.get('BASE_URL')
EDIT_KEY = os.environ.get('EDIT_KEY')

marker = '***' * 15
if USE_STRIPE_TEST_MODE:
    warn_stripe = f'{marker} RUNNING IN TEST MODE {marker}'
    print(f'STRIPE_TEST_MODE: {USE_STRIPE_TEST_MODE} {warn_stripe}')

if PROD_LOCALHOST:
    warn_locahost = f'{marker} RUNNING IN TEST MODE {marker}' if PROD_LOCALHOST else ''
    print(f'PROD_LOCALHOST: {PROD_LOCALHOST} {warn_locahost}')


STRIPE_SECRET_KEY = 'xxx'
# STRIPE_PUBLISHABLE_KEY = 'xxx'
if USE_STRIPE_TEST_MODE:
    # STRIPE_PUBLISHABLE_KEY = 'XXX'
    STRIPE_SECRET_KEY = 'xxxx'


header_scripts = ""


def is_test_env():
    if ENVIRON == 'development' or PROD_LOCALHOST:
        return True
    return False


def get_language(request):
    '''
    Returns the language directory and the language
    '''
    supported_languages = ["en", "es"]  # en = english, es = spanish
    lang = request.accept_languages.best_match(supported_languages)
    return lang


def is_mobile(user_agent):
    '''
    docs: https://tedboy.github.io/flask/generated/generated/werkzeug.UserAgent.html
    '''
    if user_agent.platform in {'android', 'iphone', 'ipad'}:
        return True

    return False


def get_req_info(request):
    '''
    Get basic information from the incoming http request
    '''
    req_info = {}
    lang = get_language(request)
    email = request.cookies.get(EMAIL_COOKIE)
    user_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)  # needs config in nginx: 'proxy_set_header X-Real-IP $remote_addr;'

    user_agent = request.user_agent
    referrer = request.referrer if request.referrer else ''

    req_info['url'] = request.url
    req_info['lang'] = lang
    req_info['user_ip'] = user_ip
    req_info['browser'] = user_agent.browser
    req_info['is_mobile'] = is_mobile(user_agent)
    req_info['operating_system'] = user_agent.platform
    req_info['referrer'] = referrer
    req_info['user_agent'] = user_agent.string

    timestamp = datetime.datetime.now()
    print(f'{timestamp} REQ: {request.path} u: {email}, lang: {lang}, ref: {referrer} {user_ip} {user_agent.platform} {user_agent.browser}')

    return req_info


def save_page_view_event(request, page_name, user_id, guest_id, req_info, shop_id=None):

    # db_interface.record_page_view(
    #     request.url,
    #     page_name,
    #     user_id,
    #     guest_id,
    #     shop_id,
    #     req_info['user_ip'],
    #     req_info['browser'],
    #     req_info['is_mobile'],
    #     req_info['operating_system'],
    #     req_info['user_agent'],
    #     req_info['referrer'],
    # )
    pass


def get_timestamp_for_file():
    '''
    Get the timestamp so that we get updated .css and .js every day
    '''
    default_ts = datetime.datetime.now().strftime("%d%b%Y")
    # TODO: get modified date for each file to improve caching performance
    return default_ts


@app.route('/help')
def help(name=None):
    _ = get_req_info(request)

    return render_template(
        'feedback.html',
        page_title='help',
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    )


@app.route('/feedback')
def feedback(name=None):
    _ = get_req_info(request)

    return render_template(
        'feedback.html',
        page_title='feedback',
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    )


@app.route('/skill_not_found')
def skill_not_found(name=None):
    _ = get_req_info(request)

    return render_template(
        'skill_not_found.html',
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts
    )


@app.route('/create')
def create_skill(name=None):
    _ = get_req_info(request)

    user = is_logged_in_and_tokens_match(reason='save_skill')
    if user is None:
        print(f"create_skill: not logged in data")
        return redirect('/login')

    return render_template(
        'create_skill.html',
        page_title='Create a Skill',
        editing=False,
        hosts='',  # produces empty field, thus placeholder is shown in the HTML input
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    )


@app.route('/save_skill', methods=['POST'])
def save_skill(name=None):
    _ = get_req_info(request)

    data = request.form

    user = is_logged_in_and_tokens_match(reason='save_skill')
    if user is None:
        print(f"save_skill: not logged in data: {data}")
        return jsonify({'status': 'failed', 'msg': 'Sign in to create a skill'})

    print(f"save_skill: u: {user.id} data: {data}")

    visible_id = data.get('visible_id')
    editing = False
    if visible_id is not None:
        editing = True

    steps = data.get('steps')
    instructions_json = data.get('instructions')
    hosts = data.get('hosts')

    try:
        instructions = json.loads(instructions_json)
    except Exception as e:
        print(f"save_skill: u: TODO failed loading json for instructions i: {instructions} e: {e}")

    if editing:

        skill_obj = db_interface.find_skill_by_visible_id(visible_id)
        if skill_obj is None:
            return jsonify({'status': 'failed', 'msg': 'could not find the skill'})

        if user.id != skill_obj.author_id:
            return jsonify({'status': 'failed', 'msg': 'no permission to modify this skill'})

        if saved_skill := db_interface.update_skill(skill_obj, steps, instructions, hosts):
            return jsonify({'status': 'success', 'saved_skill': saved_skill.visible_id})
    else:  # create new skill
        if saved_skill := db_interface.save_new_skill(steps, instructions, user.id, hosts):
            return jsonify({'status': 'success', 'saved_skill': saved_skill.visible_id})

    return jsonify({'status': 'failed', 'msg': 'try again'})


@app.route('/search', methods=['GET'])
def search_skills(name=None):
    _ = get_req_info(request)

    current_url = request.args.get('current_url')
    text = request.args.get('search_text')

    print(f"search_skills: text: [{text}] url: {current_url} ")

    skill_text_tuples = db_interface.search_skills(text, current_url)
    print(f"search_skills: url: {current_url} text: {text} found: {skill_text_tuples}")

    if skill_text_tuples is None:
        return jsonify({'user_msg': 'Could not find skills, try again', 'skills': []})

    skill_text_tuples = skill_text_tuples[:5]  # top 5

    skills = []
    for skill, text in skill_text_tuples:
        skills.append({
            'title': text,
            'visible_id': skill.visible_id,
            'steps': skill.steps,
            'author_id': skill.author_id,
            'hosts': skill.hosts,
        })

    user_msg = 'Found skills'
    if len(skills) < 1:
        user_msg = 'No skills found'

    resp = {
        'user_msg': user_msg,
        'skills': skills
    }

    return jsonify(resp)


@app.route('/s/<string:visible_id>', methods=['GET'])
def view_skill(visible_id):
    """
    Anyone should be able to see basic data about the skill
    and the steps it executes
    The owner of the skill should see more data
    """
    _ = get_req_info(request)

    user_msg = request.args.get('user_msg')

    user_id = None
    username = None
    user = is_logged_in_and_tokens_match(reason='view_skill')
    if user:
        user_id = user.id
        username = user.username

    # TODO: check if logged in to show more details
    print(f"view_skill: u: {user_id} v_id: [{visible_id}]")

    skill_instruct_tuples = db_interface.find_skill_tuples_by_visible_id(visible_id)
    if skill_instruct_tuples is None or len(skill_instruct_tuples) < 1:
        print(f"view_skill: u: {user_id} v_id: [{visible_id}] skill not found")
        return render_template('skill_not_found.html')

    skill_obj = skill_instruct_tuples[0][0]
    steps = []
    try:
        steps = json.loads(skill_obj.steps)
    except Exception as e:
        print(f"view_skill: failed to load steps json: u:{user_id} v_id: {visible_id} e:{e}")

    instructions = [skill_text[1] for skill_text in skill_instruct_tuples]

    print(f"view_skill: u: {user_id} found s: {skill_obj.id} steps: {steps}")

    return render_template(
        'create_skill.html',
        username=username,
        steps=steps,
        instructions=instructions,
        skill_obj=skill_obj,
        page_title=f"Skill Details",
        user_msg=user_msg,
        editing=True,
        hosts=skill_obj.hosts,
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    )


@app.route('/delete_skill/<string:visible_id>', methods=['DELETE'])
def delete_skill(visible_id):
    _ = get_req_info(request)

    user = is_logged_in_and_tokens_match(reason='delete_skill')
    if user is None:
        return jsonify({'status': 'failed', 'msg': 'not logged in'})

    print(f"delete_skill: u: {user.id} v_id: [{visible_id}]")

    skill_obj = db_interface.find_skill_by_visible_id(visible_id)
    if skill_obj is None:
        return jsonify({'status': 'failed', 'msg': f'invalid skill {visible_id}'})

    if skill_obj.author_id != user.id:
        print(f"delete_skill: NO PERMISSIon u: {user.id} v_id: [{visible_id}]")
        return jsonify({'status': 'failed', 'msg': 'not allowed to delete'})

    success = db_interface.delete_skill(skill_obj)
    if success:
        return jsonify({'status': 'success', 'msg': f'deleted {visible_id}'})

    return jsonify({'status': 'failed', 'msg': 'try again later'})


@app.route('/skill_executed/<string:visible_id>', methods=['POST'])
def skill_executed(visible_id):
    req_info = get_req_info(request)

    guest_id = create_guest_id_if_not_set()

    req_data = request.data
    try:
        req_json = json.loads(req_data)  # noqa
    except Exception as e:
        print(f"skill_executed: failed loading req json e: {e}")
        resp = flask.make_response(jsonify({'status': 'failed', 'msg': 'failed loading json'}))
        set_guest_cookies(resp, guest_id)
        return resp

    current_url = req_json.get('current_url')
    trigger_method = req_json.get('trigger')  # click or keyboard shortcut

    user = is_logged_in_and_tokens_match(reason='skill_executed')
    user_id = None
    if user is not None:
        user_id = user.id

    print(f"skill_executed: u: {user_id} g_id: {guest_id} v_id: {visible_id}")

    skill_obj = db_interface.find_skill_by_visible_id(visible_id)
    if skill_obj is None:
        return jsonify({'status': 'failed', 'msg': f'invalid skill {visible_id}'})

    db_interface.record_user_event('s_ex', user_id, guest_id, req_info, {'s': skill_obj.id, 'url': current_url, 't': trigger_method})

    resp = flask.make_response(jsonify({'status': 'success'}))
    set_guest_cookies(resp, guest_id)
    return resp


@app.route('/vote_skill/<string:visible_id>', methods=['POST'])
def vote_skill(visible_id):
    _ = get_req_info(request)

    guest_id = create_guest_id_if_not_set()

    req_data = request.data
    try:
        req_json = json.loads(req_data)  # noqa
    except Exception as e:
        print(f"vote_skill: failed loading req json e: {e}")
        resp = flask.make_response(jsonify({'status': 'failed', 'msg': 'failed loading json'}))
        set_guest_cookies(resp, guest_id)
        return resp

    current_url = req_json.get('current_url')  # know if people like/hate the skill on a particular site
    vote = req_json.get('vote')  # +1 or -1

    user = is_logged_in_and_tokens_match(reason='vote_skill')
    user_id = None
    if user is not None:
        user_id = user.id

    print(f"vote_skill: u: {user_id} g_id: {guest_id} v_id: {visible_id} v: {vote}")

    skill_obj = db_interface.find_skill_by_visible_id(visible_id)
    if skill_obj is None:
        return jsonify({'status': 'failed', 'msg': f'invalid skill {visible_id}'})

    # TODO: check if the user had previously voted this skill, FROM THE SAME URL,
    # and update that instead of a creating a new entry

    db_interface.vote_skill(skill_obj.id, vote, user_id, guest_id, current_url)

    resp = flask.make_response(jsonify({'status': 'success'}))
    set_guest_cookies(resp, guest_id)
    return resp


@app.route('/test_text', methods=['GET', 'POST'])
def test_text(name=None):
    _ = get_req_info(request)
    return "this is test text"


@app.route('/test_json', methods=['GET', 'POST'])
def test_json(name=None):
    _ = get_req_info(request)
    return jsonify({"test_msg1": "hey from msg1", "test_msg2": "ey from msg2"})


@app.route('/test_time', methods=['GET', 'POST'])
def test_time(name=None):
    _ = get_req_info(request)
    date_now = datetime.datetime.now()
    now = f'{date_now:%Y-%m-%d %H:%M:%S%z} (GMT)'
    return now

# Account login and registration ----------------------------------------------------------


def is_logged_in():
    try:
        email = request.cookies.get(EMAIL_COOKIE)
        username = request.cookies.get(USERNAME_COOKIE)
        token = request.cookies.get(TOKEN_COOKIE)
        token_series_id = request.cookies.get(TOKEN_COOKIE_SERIES_ID)
        if email is None and username is None and token is None and token_series_id is None:
            # attempt to read login data from request instead of cookies (chromeext)
            email = request.args.get(EMAIL_COOKIE)
            username = request.args.get(USERNAME_COOKIE)
            token = request.args.get(TOKEN_COOKIE)
            token_series_id = request.args.get(TOKEN_COOKIE_SERIES_ID)
            print(f'is_logged_in: using {email} u: {username}')

        print(f'is_logged_in: check {email} u: {username}')

        if email and username:
            return True, email, username, token, token_series_id
        else:
            return False, None, None, None, None
    except Exception:
        return False, None, None


def get_guest_id():
    guest_id = request.cookies.get(GUEST_ID_COOKIE)
    return guest_id


def create_guest_id_if_not_set():
    guest_id = get_guest_id()
    if guest_id is None:
        guest_id = secrets.token_urlsafe(32)
        print(f"create_guest_id_if_not_set: created guest_id: {guest_id}")

    return guest_id


memo_email_token_map = {}


@app.route('/clear_memo_email')
def clear_memo_email():
    global memo_email_token_map

    req_info = get_req_info(request)

    user = is_logged_in_and_tokens_match(reason='resend_email_link')
    if user is None or user.email != 'fersarr@gmail.com':
        return jsonify({'refused': 'not done'}), 200

    code = request.args.get('code')
    if code == EDIT_KEY:
        print(f"clear_memo_email: done by {req_info}")
        memo_email_token_map = {}
        return jsonify({'success': 'done'}), 200
    else:
        print(f"clear_memo_email: bad code {code} by {req_info}")
        return jsonify({'refused': 'not done'}), 200


def is_logged_in_and_tokens_match(reason=None):
    global memo_email_token_map
    logged_in, email, username, token, token_series_id = is_logged_in()
    if logged_in:
        # print(f'loggedin data received. Verifying')
        if memo_value := memo_email_token_map.get(email):
            # the credentials have recently been used, fetched from memory instead of DB
            memo_date = memo_value[3]
            date_now = datetime.datetime.now()
            if date_now - datetime.timedelta(hours=24) <= memo_date:  # still valid?
                if (email == memo_value[0] and
                        token == memo_value[1] and
                        token_series_id == memo_value[2]):
                    # print(f"tokens_match: from cache for {email}")
                    return memo_value[4]

            # delete the expired, out-of-date (changed pw?) or incorrect entry
            # print(f"tokens_match: deleting cache for {email}")
            del memo_email_token_map[email]

        # print(f"tokens_match: checking db for {email}")
        matched_tokens, user = db_interface.email_matches_token(email, token, token_series_id, reason=reason)
        if matched_tokens and user is not None:
            # expunge the user, so we can still access it after the db session is closed
            db_interface.expunge_object(user)
            memo_email_token_map[email] = (email, token, token_series_id, datetime.datetime.now(), user)
            return user

    # print(f'is_logged_in_and_tokens_match: not logged in')
    return None


def take_to_login(request, req_info, clear_login_cookies=False, status_text='', status_color=None):

    registering = True if request.args.get('registering') == 'true' else False

    sign_in_title = 'Sign in'
    page_name = 'login'

    guest_id = create_guest_id_if_not_set()
    save_page_view_event(request, page_name, None, guest_id, req_info)

    invite_by_name = ''

    # invited by someone?
    if invite_code := request.args.get('invite'):
        if user_obj := db_interface.find_user_by_referral_code(invite_code):
            invite_by_name = user_obj.username
            sign_in_title = f"Welcome<br/><label class='smaller_text'>Invited by {invite_by_name}</label>"

    # When toggling between login/register screens (just change of words)
    # we need to keep the other url parameters the same
    url_params = []
    if invite_code:
        url_params.append(f"invite={invite_code}")

    url_params = "&".join(url_params)

    login_or_register = 'Sign in'
    if registering:
        login_or_register = 'Register'
        sign_in_title = 'Register'

    page_title = f"{login_or_register} - Webbu"

    resp = flask.make_response(render_template(
        'login_register.html',
        status_text=status_text,
        status_color=status_color,
        sign_in_title=sign_in_title,
        invite_code=invite_code,
        invite_by_name=invite_by_name,
        registering=registering,
        login_or_register=login_or_register,
        page_title=page_title,
        url_params=url_params,
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    ))

    set_guest_cookies(resp, guest_id)

    if clear_login_cookies:
        clear_cookies(resp)

    return resp


@app.route('/login')
def login_register(name=None):
    req_info = get_req_info(request)
    logged_in, email, username, token, token_series_id = is_logged_in()

    if logged_in:
        return redirect('/profile')

    return take_to_login(request, req_info)


@app.route('/do_register_email', methods=['POST'])
def do_register_email():

    _ = get_req_info(request)
    data = request.form
    print(f'do_register_email: data: {data}')
    email = data['email'].lower()
    first_name = data['first_name']
    last_name = data['last_name']
    google_token = data['google_token']  # noqa TODO: if google token valid, mark the email as verified. verify docs: https://developers.google.com/identity/sign-in/web/backend-auth

    email_verified = False  # later with proper google login we can auto verify

    invite_code = data.get('invite_code', None)

    print(f"do_register_email: invites: {invite_code}")

    resp_json, user_and_token_data = db_interface.add_user_email_only(
        email,
        first_name,
        last_name,
        email_verified,
    )

    if user_and_token_data:
        # new user created successfully
        token, token_series_id, username, new_user = user_and_token_data

        resp = flask.make_response(jsonify(resp_json))
        set_login_cookies(resp, email, token, token_series_id, username)
        return resp
    else:
        # A validation error or already-existing user that must use the email magic_link
        return flask.make_response(jsonify(resp_json))


def set_login_cookies(resp, email, token, token_series_id, username):
    secure_token = False  # cant do it for dev if no https
    expire_date = datetime.datetime.now() + datetime.timedelta(days=90)

    resp.set_cookie(TOKEN_COOKIE, value=token, httponly=True, secure=secure_token, expires=expire_date)
    resp.set_cookie(TOKEN_COOKIE_SERIES_ID, value=token_series_id, httponly=True, secure=secure_token, expires=expire_date)
    resp.set_cookie(EMAIL_COOKIE, value=email, httponly=False, secure=secure_token, expires=expire_date)

    # setting this one to httponly = False so that javascript can also access it to check if the user is logged in
    resp.set_cookie(USERNAME_COOKIE, value=username, httponly=False, secure=secure_token, expires=expire_date)


def set_guest_cookies(resp, guest_id):
    expire_date = datetime.datetime.now() + datetime.timedelta(days=720)

    # samesite = None so that it can be sent as 3rd party cookies (TODO: probably not needed)
    # secure = True is needed for samesite=None
    resp.set_cookie(GUEST_ID_COOKIE, value=guest_id, httponly=True, secure=True, expires=expire_date, samesite='None')


def clear_cookies(resp):
    # clear cookies by setting their expiry date to unix timestamp 0 (past)
    resp.set_cookie(EMAIL_COOKIE, '', expires=0)
    resp.set_cookie(TOKEN_COOKIE, '', expires=0)
    resp.set_cookie(TOKEN_COOKIE_SERIES_ID, '', expires=0)
    resp.set_cookie(USERNAME_COOKIE, '', expires=0)


@app.route('/logout')
def logout():
    '''
    Log out: clear all session/cookie details and take to main page
    '''
    req_info = get_req_info(request)
    logged_in, email, username, token, token_series_id = is_logged_in()
    print(f'logout: {email}')

    # clear from cache too in case the cached user object has an issue
    # so that we have a way to help users on the fly
    try:
        del memo_email_token_map[email]
    except Exception:
        print(f"logout: failed deleting {email} from memo_email_token_map")

    return take_to_login(request, req_info, clear_login_cookies=True)


@app.route('/login_link', methods=['GET'])
def login_link():
    '''
    When users click the login magic link in their email
    they appear here with email+token1+token2
    We should verify the tokens and then create new ones and delete the old ones
    '''
    req_info = get_req_info(request)
    email = request.args.get('email').lower()
    token = request.args.get('token1')
    token_series_id = request.args.get('token2')
    print(f'login_link: {email} tkns: {token}, {token_series_id}')
    matched_tokens, user = db_interface.email_matches_token(email, token, token_series_id, delete_if_found=True, reason='login_link')
    if matched_tokens:

        # set email as verified
        db_interface.set_email_as_verified(user)
        # create new tokens that will be more long-term
        success, new_token, new_token_series_id = db_interface.generate_remember_me_token(user.id)
        if success:
            resp = flask.make_response(redirect('/profile'))
            set_login_cookies(resp, email, new_token, new_token_series_id, user.username)
            return resp
        else:
            print(f"login_link: Error. Could not create new permament tokens for {email}")
            msg = f"Error. Could not log {email} in. Please try to log in again."
            return take_to_login(request, req_info, status_text=msg, status_color='red')
    else:
        print(f"login_link: Error. Email {email} and tokens do not match. ({token}, {token_series_id})")
        msg = f"Error. Email {email} and tokens do not match. Please try to log in again."
        return take_to_login(request, req_info, status_text=msg, status_color='red')


@app.route('/profile', methods=['GET'])
def user_profile():
    _ = get_req_info(request)
    '''
    From this page, the user can see their created skills
    '''

    user_msg = request.args.get('user_msg')

    user = is_logged_in_and_tokens_match()
    if user is None:
        print(f'user_profile: not logged in, redirecting')
        # avoid infinite loops /profile -> /login - > /profile by logging out (cookies)
        # this happens when deleting a user in the DB but not clearing cookies
        return redirect('/logout')

    skill_instruct_tuples = db_interface.get_user_skills(user.id)

    if skill_instruct_tuples is None:
        skill_instruct_tuples = []
    else:
        for skill_instruct_tuple in skill_instruct_tuples:
            print(f"user_profile: found skills: {skill_instruct_tuple}")

    return render_template(
        'profile.html',
        username=user.username,
        skill_instruct_tuples=skill_instruct_tuples,
        user_msg=user_msg,
        file_ts=get_timestamp_for_file(),
        header_scripts=header_scripts,
    )
















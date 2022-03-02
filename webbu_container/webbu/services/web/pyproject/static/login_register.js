function is_field_empty(field) {

    if (field.value !== "") {
        return false;
    }

    return true;
}


function validateEmail(email) {
    const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
}


function login_or_register_form(event) {
    event.preventDefault(); //  prevent the default form action for Ajax form submissions
    login_or_register();
    return false;  // prevent form submission that reloads page
}


function login_or_register() {

    email_field = document.getElementById("email_login_input");
    unset_border_colors(email_field);

    status_div = "by_email_status_div";
    status_text = "by_email_status_text";

    empty_field_msg = 'Please fill in the required field'
    if (is_field_empty(email_field)) {
        set_status(empty_field_msg, 'red', email_field, status_div, status_text);
        return;
    }

    email_value = email_field.value;
    if (!validateEmail(email_value)) {
        bad_email_msg = 'Invalid email format (no @ for example)'
        set_status(bad_email_msg, 'red', email_field, status_div, status_text);
        return;
    }

    make_login(email_value, "", "", "");
}


function make_login(email_value, first_name, last_name, google_token) {

    email_field = document.getElementById("email_login_input"); // TODO: should be different for google signin
    status_div = "by_email_status_div";
    status_text = "by_email_status_text";


    invite_code = document.getElementById("invite_code").value;

    var register_data = {}
    register_data.email = email_value;
    register_data.first_name = first_name;
    register_data.last_name = last_name;
    register_data.google_token = google_token;

    register_data.invite_code = invite_code;

    console.log('make_login: registering: ' + register_data);
    console.log(register_data);

    progress_color = "#cb8763";  // orange-ish

    set_status('One moment...', progress_color, email_field, status_div, status_text);

    $.post("/do_register_email", register_data,
        function(data, status){

            console.log('make_login: response status: ' + status + ', data:');
            console.log(data);

            if ('error' in data) {
                console.log('make_login: register error');
                wrong_field_to_mark = null;

                if ('non-unique email' === data['error_code']) {
                    wrong_field_to_mark = email_field;
                    // TODO:
                    // email has already been registered so send a
                    // magic link to the email address to enable login
                }

                set_status(data['error'], 'red', wrong_field_to_mark, status_div, status_text);

            } else if ('added' in data) {
                console.log('make_login: register success');
                set_status('Success!', 'green', null, status_div, status_text);

                // send to profile now that user is logged in
                window.location.replace("/profile");

            } else if ('added_email_token' in data) {
                console.log('Sent email magic link');
                set_status(data['msg'], 'green', null, status_div, status_text);

                if (google_token !== null && google_token !== "") {
                    // its a sign-in via google (not register)
                    // sign out now from it since we track the state separately
                    googleSignOut();
                }


            } else if ('added-info' in data) {
                console.log('added-info success');
                set_status('Success!', 'green', null, status_div, status_text);

            } else {
                console.log('register response: else');
            }
        }
    ).fail(function(response) {
        console.log('make_login: register failed:');
        console.log(response);
        set_status("There was an error, please try again.", 'red', null, status_div, status_text);
    });

    return;
}

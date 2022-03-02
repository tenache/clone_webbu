function hideFeedbackModalBox() {
    var modal = document.getElementById("feedback_modal_box");
    modal.style.display = "none";
}


function showFeedbackModalBox() {
    // clear previous text
    console.log('show feedback modal box');
    feedback_result = document.getElementById('feedback_result');
    feedback_result.innerHTML = "";

    // Get the modal
    var modal = document.getElementById("feedback_modal_box");
    modal.style.display = "block";

    // make the input methods visible in case they were made invisible after sending feedback
    change_visibility_feedback_elements('block');
}


window.onclick = function(event) {
    // When the user clicks anywhere outside of the modal, close it
    var modal = document.getElementById("feedback_modal_box");
    if (event.target == modal) {
        modal.style.display = "none";
    }
}


function change_visibility_feedback_elements(block_or_none) {
    // make the input forms in the feedback dialog disappear
    console.log('change_visibility_feedback_elements: ' + block_or_none);
    var feedback_title = document.getElementById("feedback_title");
    var send_feedback_button = document.getElementById('send_feedback_button');
    var feedback_ta = document.getElementById("ta_feedback");
    var email_field = document.getElementById("feedback_email");
    feedback_title.style.display = block_or_none;
    send_feedback_button.style.display = block_or_none;
    feedback_ta.style.display = block_or_none;
    email_field.style.display = block_or_none;
}


function sendFeedback(capture_work) {

    var feedback_ta = document.getElementById("ta_feedback");
    var email_field = document.getElementById("feedback_email");

    var instructions_text = 'not_in_app';
    var results_text = 'not_in_app';
    var code_text = 'not_in_app';
    if (capture_work === true ) {
        // only needed when sending feedback from the text2code app
        instructions_text = document.getElementById("ta_humanlang").value;
        results_text = document.getElementById("ta_result").value;
        code_text = document.getElementById("ta_code").value;
    }

    feedback_text = feedback_ta.value
    email = email_field.value
    console.log('Sending feedback: ' + feedback_text + ' inst: ' + feedback_text);

    req_data = {}
    req_data.feedback_text = feedback_text
    req_data.email = email
    req_data.instructions_text = instructions_text
    req_data.results_text = results_text
    req_data.code_text = code_text

    feedback_result.innerHTML = "Sending..."
    change_visibility_feedback_elements('none');

    $.post("/send_feedback", req_data,
        function(data, status){
            /* we will probably not wait for this response, since we send the user
            to the registration form while the email alone is being registered */
            console.log('response status: ' + status + ', data:');
            console.log(data);
            if ('error' in data) {
                console.log('register email error');

            } else {
                console.log('No error in resp');

                feedback_result.innerHTML = "Sent! Thank you for your feedback. We'll write back shortly."

            }

        }
    );
}


function hideMessagesModalBox() {
    var modal = document.getElementById("messages_modal_box");
    modal.style.display = "none";
}


function showMessagesModalBox(message) {
    // set the text
    message_for_user = document.getElementById('message_for_user');
    message_for_user.innerHTML = message;

    // Get the modal
    var modal = document.getElementById("messages_modal_box");
    modal.style.display = "block";
}

function navigation_menu_responsive() {
  var x = document.getElementById("myTopnav");
  if (x.className === "topnav") {
    x.className += " responsive";
  } else {
    x.className = "topnav";
  }
}


function createNotificationRow(msg, notification_id) {

    notificationRow = document.createElement("div");
    notificationRow.id = "notification_row_" + notification_id
    notificationRow.setAttribute("class", "notification_row");

    notificationText = document.createElement("p");
    notificationText.setAttribute("class", "notification_msgs");
    notificationText.innerHTML = msg;

    close_button = document.createElement("span");
    close_button.setAttribute("class", "close_notification");
    close_button.setAttribute("onClick", "javascript: hideNotification('" + notificationRow.id + "')");
    close_button.innerHTML = "&times;"

    notificationRow.append(notificationText);
    notificationRow.append(close_button);

    return notificationRow;
}


function showNotification(msg) {
    notificationDiv = document.getElementById('notification_msgs_div');

    // clear the animation so that even if there are 2 equal
    // notifications in a row (no change) it still shakes
    notificationDiv.style.animation = "none";
    // force DOM reflow (https://stackoverflow.com/questions/27637184/what-is-dom-reflow)
    // other methods triggering reflow: https://gist.github.com/paulirish/5d52fb081b3570c81e3a
    notificationDiv.focus();
    notificationDiv.style.display = 'block';

    var repeatedMsg = false;
    notificationElements = document.getElementsByClassName("notification_msgs");
    for (var i = 0; i < notificationElements.length; i++) {
        var notifElem = notificationElements[i];
        if (notifElem.innerHTML === msg) {
            repeatedMsg = true;
            console.log("Repeated notif detected. Not adding more")
        }
    }
    if (!repeatedMsg) {
        notificationRow = createNotificationRow(msg, notificationDiv.childElementCount);
        notificationDiv.append(notificationRow);
    }

    notificationDiv.style.animation = "shake 0.2s ease-in-out 0s 2";
}


function hideNotification(notification_row_id) {
    notificationRow = document.getElementById(notification_row_id);
    notificationRow.style.display = 'none';

    // clear this so it shakes the next time
    notificationDiv = document.getElementById('notification_msgs_div');
    notificationDiv.style.animation = "";
}


function setCookie(name, value, exdays) {
  var d = new Date();
  d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
  var expires = "expires=" + d.toUTCString();
  document.cookie = name + "=" + value + ";" + expires + ";path=/";
}


function getCookie(name) {
    var dc = document.cookie;

    var prefix = name + "=";
    var begin = dc.indexOf("; " + prefix);
    if (begin == -1) {
        begin = dc.indexOf(prefix);
        if (begin != 0) return null;
    } else {
        begin += 2;
        var end = document.cookie.indexOf(";", begin);
        if (end == -1) {
            end = dc.length;
        }
    }
    // because unescape has been deprecated, replaced with decodeURI
    //return unescape(dc.substring(begin + prefix.length, end));
    var cookie_value = decodeURI(dc.substring(begin + prefix.length, end));

    if (name === "email" && cookie_value.charAt(0) === '"') {
        // having a @ in the cookie value results in the value getting wrapped with quotes
        // remove first and last character since they are quotes for emails
        // "fer@gmail.com" -> fer@gmail.com
        // https://stackoverflow.com/questions/14582334/how-to-create-cookie-without-quotes-around-value
        // However, right now email cookie is httponly=true
        cookie_value = cookie_value.slice(1,-1);
    }

    return cookie_value
}


function change_menu_button_visibility(menu_link_name, visible) {

    menu_link = document.getElementById(menu_link_name);

    if (menu_link === null ) {
        // some pages might not have the logout link
        // console.log('did not change visibility for ' + menu_link_name + ', ' + visible);
        return;
    }
    //console.log('changing2 visibility for ' + menu_link_name + ', ' + visible);

    if (visible === false) {
        // just make it disappear, same for desktop/mobile
        menu_link.style.display = 'none';
    } else {
        if (window.matchMedia("(max-width: 600px)").matches) {
             //matching media-query in menu.css
            // empty so it inherits inherit from menu.css .topnav.responsive a in mobile
            // without this, on mobile, the menu button appears next to the menu icon, instead
            // having it under the expandable menu
            menu_link.style.display = '';
            //console.log('mobile menu button');
        } else {
            // not mobile: make the logout_link appear by setting display to block
            menu_link.style.display = 'block';
            //console.log('desktop menu button');
        }
    }
}


function initial_checks() {
    console.log('initial checks')

    username_cookie = getCookie("username");

    if (username_cookie == null) {  // not logged in
        console.log('not logged in');
        change_menu_button_visibility('logout_link', false);
        change_menu_button_visibility('profile_link', false);
        change_menu_button_visibility('create_link', false);
    } else {
        console.log('logged in');
        change_menu_button_visibility('logout_link', true);
        change_menu_button_visibility('profile_link', true);
        change_menu_button_visibility('create_link', true);
        change_menu_button_visibility('signin_link', false);
    }
}


function signOut() {
    $.ajax({
      url: "/logout",
      type: 'GET',
      success: function(json) {
        console.log("Logout success: " + json.country);
      },
      error: function(err) {
        console.log("Logout error: " + err);
      }
    });
    try {
        // we only load gapi in the login page
        // TODO: load dynamically?
        googleSignOut();
    } catch (err) {
        console.log('googleSignOut not done now');
    }
    window.location.replace("login_register");  // profile->login.
}

function googleSignOut() {
    var auth2 = gapi.auth2.getAuthInstance();
    auth2.signOut().then(function () {
      console.log('User signed out via Google.');
    });
}


function unset_border_colors(elem) {
    // if the user attempted a register but failed and a field got market,
    // we should clear the marked fields for the second attempt so that
    // it is visible which fields were wrong in the 2nd (without including 1st)
    elem.style.borderColor = ''
}


function set_status(text, color, field_to_mark, status_div, status_text) {

    console.log('setting status: ' + text);
    status_div = document.getElementById(status_div);
    status_div.style.backgroundColor = color;
    status_div.style.display = "block";

    status_text = document.getElementById(status_text);
    status_text.textContent = text

    if (field_to_mark !== null) {
        field_to_mark.style.borderColor = color;
    }
}

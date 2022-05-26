

function init_js() {
    // pressing Enter adds the row
    document.getElementById("step_param").addEventListener('keyup', function (e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            add_step_row();
        }
    });

    document.getElementById("step_param2").addEventListener('keyup', function (e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            add_step_row();
        }
    });

    // pressing Enter adds the row
    document.getElementById("instruction_text").addEventListener('keyup', function (e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            add_instruction_row();
        }
    });
}


function add_step_row() {
    var step_type = document.getElementById('step_dropdown').value;
    var step_param = document.getElementById('step_param').value;
    var step_param2 = document.getElementById('step_param2').value;

    console.log('add_step_row: ' + step_type + ', ' + step_param + ', ' + step_param2);

    if (step_type === "") {
        showNotification("Choose an action type from the dropdown first", 'notification_msg_steps', 'orange');
        return;
    }
    
    created_steps_container = document.getElementById('created_steps');

    var new_step_row = document.createElement("div");
    new_step_row.id = 'new_step_row_' + (created_steps_container.childElementCount + 1);
    new_step_row.className = 'created_step_row';

    var new_step_type = document.createElement("p");
    new_step_type.className = 'created_step_type';
    new_step_type.innerHTML = step_type;
    new_step_row.appendChild(new_step_type);

    var new_step_param = document.createElement("p");
    new_step_param.className = 'created_step_param';
    new_step_param.innerHTML = step_param;
    new_step_row.appendChild(new_step_param);

    var new_step_param2 = document.createElement("p");
    new_step_param2.className = 'created_step_param2';
    new_step_param2.innerHTML = step_param2;
    if (step_param2) {
        new_step_param2.style.display = 'inline-block'; /* only some steps have param2 */
    }
    new_step_row.appendChild(new_step_param2);

    var new_step_delete_button = document.createElement("img");
    new_step_delete_button.className = 'delete_step_row_button';
    new_step_delete_button.src = '/static/imgs/trash_white.svg';
    new_step_delete_button.setAttribute("onClick", 'delete_step_row("' + new_step_row.id + '")');
    new_step_row.appendChild(new_step_delete_button);

    created_steps_container.appendChild(new_step_row);

}


function delete_step_row(new_step_row_id) {
    console.log('removing ' + new_step_row_id);
    var step_row = document.getElementById(new_step_row_id);
    step_row.remove();
}


function showNotification(message, notification_element='notification_msg', color='black') {
    document.getElementById(notification_element).innerHTML = message;
    document.getElementById(notification_element).style.display = 'block';
    document.getElementById(notification_element).style.color = color;
}


function hideNotification(notification_element='notification_msg') {
    document.getElementById(notification_element).style.display = 'none';
    document.getElementById(notification_element).innerHTML = '';
}


function showLoading() {
    document.getElementById('loading_animation').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading_animation').style.display = 'none';
}


function collect_all_steps() {
    all_inputs = []
    input_divs = document.getElementsByClassName("created_step_row"); // in appareance order
    for (idx = 0; idx < input_divs.length; ++idx) {
        var curr_div = input_divs[idx];
        var step_type = curr_div.getElementsByClassName("created_step_type")[0].innerHTML;
        var step_param = curr_div.getElementsByClassName("created_step_param")[0].innerHTML;
        var step_param2 = curr_div.getElementsByClassName("created_step_param2")[0].innerHTML;

        console.log("input: " + step_type + ", " + step_param + ", " + step_param2);
        all_inputs.push({'t': step_type, 'p': step_param, 'p2': step_param2});
    }

    return all_inputs;
}

function collect_all_instructions() {
    all_instructs = []
    divs = document.getElementsByClassName("created_instruction_row"); // in appareance order
    for (idx = 0; idx < divs.length; ++idx) {
        var instruction = divs[idx].getElementsByClassName("created_instruction_text")[0].innerHTML;
        all_instructs.push(instruction);
    }

    return all_instructs;
}


function save_skill_req() {
    // clear the text areas
    var hosts = document.getElementById('hosts_input').value;

    // add the input variables to the human_text
    all_steps = collect_all_steps()
    all_instructions = collect_all_instructions()

    if (all_steps.length == 0) {
        showNotification('Add 1 or more steps', 'notification_msg', 'red');
        return;
    }

    if (all_instructions.length == 0) {
        showNotification('Add 1 or more instructions', 'notification_msg', 'red');
        return;
    }

    req_data = {};
    req_data.steps = JSON.stringify(all_steps);
    req_data.instructions = JSON.stringify(all_instructions);
    req_data.hosts = hosts;

    var skill_visible_id = null;
    try {
        skill_visible_id = document.getElementById('v_id_title').innerHTML;
    } catch (err) {}

    console.log('save_skill_req: skill_visible_id: ' + skill_visible_id);
    if (skill_visible_id) {
        req_data.visible_id = skill_visible_id;
    }

    showLoading();
    showNotification('Saving skill...', 'notification_msg', 'green');

    $.post("/save_skill", req_data,
        function(data, status){
            /* we will probably not wait for this response, since we send the user
            to the registration form while the email alone is being registered */
            console.log('response status: ' + status + ', data:');
            console.log(data);
            hideLoading();
            if ('status' in data && data['status'] === 'failed') {
                console.log(data);

                try {
                    showNotification('Error: ' + data['msg'], 'notification_msg', 'red');
                } catch {}

            } else {
                console.log('No error in resp');
                window.location = '/s/' + data['saved_skill'] + '?user_msg=Skill saved!';
                //showNotification('Done! 🎉', 'notification_msg', 'black');


            }

        }
    ).fail(function(response) {
        console.log('save_skill_req: request failed:');
        console.log(response);
        hideLoading();
        showNotification('Error: ' + response.responseText, 'notification_msg', 'red');
    });
}


function step_dropdown_changed(dropdown) {
    let value = dropdown.value;
    hideNotification('notification_msg_steps');

    param_field = document.getElementById('step_param');
    param_field.value = "";

    param_field2 = document.getElementById('step_param2');
    param_field2.value = "";
    param_field2.style.display = 'none';  // invisible

    if ( value === "type_text") {
        param_field.placeholder = 'Type the text'
    } else if ( value === "open_url" || value === "fetch_json" ) {
        param_field.placeholder = 'Type the URL'
    } else if ( value === "delay" ) {
        param_field.placeholder = 'Type the delay in seconds'
    } else if ( value === "shortcut" ) {
        param_field.placeholder = 'Type the shortcut keys, separated by +'
    } else if ( value === "submit_form" ) {
        param_field.placeholder = "Type the form's selector or empty if it's active"
    } else if ( value === "click" ) {
        param_field.placeholder = "Type the selector for the DOM element or empty if it's active"
    } else if ( value === "focus" ) {
        param_field.placeholder = "Type the selector for the DOM element or empty if it's active"
    } else if ( value === "gsheet_cell" ) {
        param_field.placeholder = "Type the cell's name (e.g. B5)"
    } else if ( value === "copy_text" ) {
        param_field.placeholder = "Type the text selector or empty if it's the active element"
    } else if ( value === "change_style" ) {
        param_field.placeholder = "DOM selector"
        param_field2.placeholder = "style value (CSS)"
        param_field2.style.display = 'inline-block';
    } else if ( value === "backend_steps" ) {
        param_field.placeholder = "Type the id of the steps"
    }
}


function add_instruction_row() {
    var instruction_text = document.getElementById('instruction_text').value;

    if (instruction_text === "") {
        showNotification("Type something before adding the instruction", 'notification_msg_instructions', 'orange');
        return;
    }

    hideNotification('notification_msg_instructions');

    console.log('add_instruction_row: ' + instruction_text);
    
    created_instructions_container = document.getElementById('created_instructions');

    var new_row = document.createElement("div");
    new_row.id = 'new_instruction_row_' + (created_instructions_container.childElementCount + 1);
    new_row.className = 'created_instruction_row';

    var new_instruct = document.createElement("p");
    new_instruct.className = 'created_instruction_text';
    new_instruct.innerHTML = instruction_text;
    new_row.appendChild(new_instruct);

    var new_delete_button = document.createElement("img");
    new_delete_button.className = 'created_instruction_delete_button';
    new_delete_button.src = '/static/imgs/trash_white.svg';
    new_delete_button.setAttribute("onClick", 'delete_instruction_row("' + new_row.id + '")');
    new_row.appendChild(new_delete_button);

    created_instructions_container.appendChild(new_row);
}


function delete_instruction_row(row_id) {
    console.log('removing instruct ' + row_id);
    var row_to_del = document.getElementById(row_id);
    row_to_del.remove();
}


function delete_skill(skill_visible_id) {
    console.log('delete_skill: ' + skill_visible_id);
    req_data = {};
    fetch('/delete_skill/' + skill_visible_id, {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(response_json => {
        console.log('delete_skill: success resp:');
        console.log(response_json);
        window.location = '/profile?user_msg=Deleted skill'

    }).catch((error) => {
        console.log('delete_skill: failed');
        console.log(error);
    });
}











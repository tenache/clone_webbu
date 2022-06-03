import re

'''
This file contains backend steps but people can also create frontend-only steps
using webbu.app/create
'''

backend_steps = {}


def register_steps(func):
    backend_steps[func.__name__] = func
    return func


@register_steps
def helloworld(user_query, page_content):
    '''
    instruction: print hello world from the backend
    '''

    return [{
        't': 'display_msg',  # display msg on webbu extension
        'p': f'hello world from backend. The query was {user_query}',
        'p2': '',
    }, {
        't': 'type_text',  # type on current HTML elem
        'p': 'hello world from backend',
        'p2': '',
    }]


@register_steps
def change_background_color(user_query, page_content):
    '''
    instruction: make the background violet
    '''

    colors = {'red', 'blue', 'gray', 'orange', 'black', 'yellow',
              'white', 'purple', 'brown', 'violet', 'pink', 'green'}

    colors_regex = '|'.join(colors)

    regexes = [
        fr".*(?:make|change)(?: the)? background(?: color)? ({colors_regex}).*",
    ]

    print(regexes)

    for regex in regexes:
        if match := re.match(regex, user_query):
            requested_color = match.group(1)
            return [{
                't': 'change_style',  # display msg on webbu extension
                'p': 'body',
                'p2': f"background-color: {requested_color}",
            }]

    return []

'''
This file contains backend steps but people can also create frontend-only steps
using webbu.app/create
'''

backend_steps = {}


def register_steps(func):
    backend_steps[func.__name__] = func
    return func


@register_steps
def helloworld():
    '''
    instruction: print hello world from the backend
    '''

    return [{
        't': 'display_msg',  # display msg on webbu extension
        'p': 'hello world from backend',
        'p2': '',
    }, {
        't': 'type_text',  # type on current HTML elem
        'p': 'hello world from backend',
        'p2': '',
    }]
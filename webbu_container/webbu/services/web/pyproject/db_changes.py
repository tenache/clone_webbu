from pyproject import db


def drop_all():
    print(f'dropping all')
    db.drop_all()  # CAREFUL!


def change_db():
    '''
    Run this inside the web container as follows:

    If you call db.create_all(), the new tables are added without modifying the data for existing ones

    # pwd
    from /usr/src/app

    call
    PYTHONPATH=.:web py_conda_env/bin/python web/pyproject/db_changes.py
    *Note 2 paths in PYTHONPATH

    Changing DB
    changed DB
    '''

    print('Changing DB')
    # drop_all()  # CAREFUL!

    db.create_all()
    db.session.commit()

    print('changed DB')


if __name__ == '__main__':
    change_db()

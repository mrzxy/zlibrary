from database.config import init_db, close_db


def run():
    pass
if __name__ == '__main__':
    try:
        db = init_db()
        run()
    except Exception as e:
        print(e)
    finally:
        close_db(db)
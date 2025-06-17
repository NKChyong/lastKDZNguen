from typing import Generator

def get_db() -> Generator[None, None, None]:
    db = None
    try:
        yield db
    finally:
        if db:
            db.close()

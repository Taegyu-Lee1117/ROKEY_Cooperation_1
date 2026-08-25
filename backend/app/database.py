import os
from collections.abc import Generator

import psycopg
from psycopg.rows import dict_row


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return url


def get_connection() -> Generator[psycopg.Connection, None, None]:
    with psycopg.connect(database_url(), row_factory=dict_row) as connection:
        yield connection


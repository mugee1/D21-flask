import sqlite3                               # SQLite(파일 하나로 된 작은 데이터베이스)를 다루는 파이썬 기본 도구예요
from pathlib import Path                     # 파일 위치(경로)를 쉽게 다루는 도구예요

# 이 파일(db.py)이 있는 D21-flask 폴더 안에 reviews.db 파일을 만들어요 (어디서 서버를 켜도 같은 자리)
DB_PATH = Path(__file__).parent / "reviews.db"

# 후기 표를 만드는 SQL이에요. IF NOT EXISTS: 표가 이미 있으면 그냥 넘어가요 (후기가 지워지지 않아요)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,                             -- 후기 번호 (1, 2, 3… 자동으로 매겨요)
    class_id   INTEGER NOT NULL,                                              -- 어느 클래스의 후기인지 (NOT NULL: 꼭 있어야 해요)
    nickname   TEXT    NOT NULL CHECK (length(nickname) BETWEEN 1 AND 20),    -- 닉네임 (1~20자만 들어가요)
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),               -- 별점 (1~5만 들어가요)
    content    TEXT    NOT NULL CHECK (length(content) BETWEEN 1 AND 500),    -- 후기 내용 (1~500자만 들어가요)
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))        -- 저장 시각 (안 넣으면 지금 시각을 자동으로 적어요)
)
"""

# 찾아보기 쉽게 "클래스 번호" 칸에 색인(책 맨 뒤 찾아보기 같은 것)을 붙여요 → 후기가 많아져도 빨리 찾아요
CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_reviews_class ON reviews (class_id, created_at)"


def connect():                               # reviews.db 파일과 연결해 주는 함수예요
    conn = sqlite3.connect(DB_PATH)          # 파일을 열어요 (파일이 없으면 새로 만들어요)
    conn.row_factory = sqlite3.Row           # 꺼낸 줄을 row["nickname"]처럼 칸 이름으로 읽을 수 있게 해요
    return conn                              # 연결을 돌려줘요


def init_db():                               # 표를 만드는 함수예요 (서버가 켜질 때 한 번 불러요)
    conn = connect()                         # DB에 연결하고
    try:                                     # 아래 일을 해 보고
        conn.execute(CREATE_TABLE_SQL)       # 표를 만들어요 (이미 있으면 넘어가요)
        conn.execute(CREATE_INDEX_SQL)       # 색인도 만들어요 (이미 있으면 넘어가요)
        conn.commit()                        # "저장" 도장을 찍어요 (commit 안 하면 반영이 안 돼요)
    finally:                                 # 중간에 에러가 나더라도 꼭
        conn.close()                         # 연결을 닫아요 (파일을 열어 둔 채로 두지 않기)


def add_review(class_id, nickname, rating, content):   # 후기 하나를 표에 넣는 함수예요
    conn = connect()                         # DB에 연결하고
    try:
        conn.execute(
            "INSERT INTO reviews (class_id, nickname, rating, content) VALUES (?, ?, ?, ?)",   # ? 자리에 값이 순서대로 들어가요
            (class_id, nickname, rating, content),   # ? 4개에 들어갈 값 4개 (사용자가 적은 글을 SQL에 직접 붙이지 않아서 안전해요)
        )                                    # created_at은 안 넣었으니 SQLite가 지금 시각을 자동으로 적어요
        conn.commit()                        # "저장" 도장을 찍어요
    finally:
        conn.close()                         # 연결을 닫아요


def get_reviews(class_id):                   # 그 클래스의 후기를 최신순으로 꺼내는 함수예요
    conn = connect()                         # DB에 연결하고
    try:
        rows = conn.execute(
            """
            SELECT nickname, rating, content,
                   substr(created_at, 1, 16) AS created   -- "2026-11-11 14:30:05" 앞 16글자 → "2026-11-11 14:30" (초는 빼요)
            FROM reviews
            WHERE class_id = ?                            -- 이 클래스 번호의 후기만
            ORDER BY created_at DESC, id DESC             -- 최신 시각이 위로, 같은 초면 나중에 들어온 번호가 위로
            """,
            (class_id,),                     # ? 1개에 들어갈 값 (값이 하나여도 끝에 쉼표를 붙여야 묶음(튜플)이 돼요)
        ).fetchall()                         # 찾은 줄을 전부 꺼내요
        return [dict(row) for row in rows]   # 한 줄씩 사전(dict)으로 바꿔서 리스트로 돌려줘요 (화면에서 r.nickname처럼 써요)
    finally:
        conn.close()                         # 연결을 닫아요


def get_review_stats(class_id):              # 그 클래스의 후기 수와 평균 별점을 계산하는 함수예요
    conn = connect()                         # DB에 연결하고
    try:
        row = conn.execute(
            """
            SELECT COUNT(*)              AS count,   -- 후기가 몇 줄인지 세요 (없으면 0)
                   ROUND(AVG(rating), 1) AS avg      -- 별점 평균을 소수 첫째 자리까지 반올림해요 (없으면 NULL → 파이썬에선 None)
            FROM reviews
            WHERE class_id = ?                       -- 이 클래스 번호의 후기만
            """,
            (class_id,),                     # ? 자리에 들어갈 클래스 번호
        ).fetchone()                         # 결과는 항상 딱 한 줄이라 fetchone(한 줄만 꺼내기)을 써요
        return dict(row)                     # 예: {"count": 3, "avg": 4.3} / 후기가 없으면 {"count": 0, "avg": None}
    finally:
        conn.close()                         # 연결을 닫아요

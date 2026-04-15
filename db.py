import json
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

load_dotenv()

DEFAULT_SOUND = "myinstants_sounds/default.mp3"

db_name = os.getenv("POSTGRESQL_DBNAME")
db_user = os.getenv("POSTGRESQL_USER")
db_password = os.getenv("POSTGRESQL_PASSWORD")
host = os.getenv("POSTGRESQL_HOST")
port = int(os.getenv("POSTGRESQL_PORT"))


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            database=db_name,
            host=host,
            user=db_user,
            password=db_password,
            port=port,
        )
        self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
    ID SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    sound VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS statistic (
    ID SERIAL PRIMARY KEY,
    sound_id VARCHAR(255) UNIQUE NOT NULL, 
    sound_name VARCHAR(255) NOT NULL,
    rating INT DEFAULT 0,
    owner VARCHAR(255)
);"""
        )

    def query(self, query, params=None):
        cur = self.conn.cursor()
        try:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchall()
        except Exception as e:
            print(f"Query error: {e}")
            return None

    def get_sound(self, user_id: str) -> str | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT sound FROM users WHERE user_id = %s", (user_id,))
            res = cur.fetchone()
            if res:
                return res[0]
            return None
        except Exception as e:
            print(f"Error in get_sound: {e}")
            return None

    def add_user(self, user_id: str) -> bool:
        try:
            if self.get_sound(user_id) is not None:
                return False

            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO users (user_id, sound) VALUES (%s, %s)",
                (user_id, DEFAULT_SOUND),
            )
            return True
        except Exception as e:
            print(f"Error in add_user: {e}")
            return False

    def edit_value(self, user_id: str, value: str) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE users SET sound = %s WHERE user_id = %s", (value, user_id)
            )
            return True
        except Exception as e:
            print(f"Error in edit_value: {e}")
            return False

    def reset(self, user_id: str) -> bool:
        return self.edit_value(user_id, DEFAULT_SOUND)

    def sound_rating(self, sound_id: str) -> int | None:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT rating FROM statistic WHERE sound_id = %s", (sound_id,))
            res = cur.fetchone()
            if res:
                return res[0]
            return None
        except Exception as e:
            print(f"Error in sound_rating: {e}")
            return None

    def add_sound(self, sound_id: str, sound_name: str, owner=None) -> bool:
        try:
            cur = self.conn.cursor()
            # Проверяем, существует ли уже звук
            cur.execute("SELECT 1 FROM statistic WHERE sound_id = %s", (sound_id,))
            if cur.fetchone():
                return False

            cur.execute(
                "INSERT INTO statistic (sound_id, sound_name, rating, owner) VALUES (%s, %s, 0, %s)",
                (sound_id, sound_name, owner),
            )
            return True
        except Exception as e:
            print(f"Error in add_sound: {e}")
            return False

    def plus_one(self, sound_id: str) -> bool:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE statistic SET rating = rating + 1 WHERE sound_id = %s",
                (sound_id,),
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error in plus_one: {e}")
            return False

    def get_top(self, num: int) -> list[dict]:
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT sound_id, sound_name, rating FROM statistic ORDER BY rating DESC LIMIT %s",
                (num,),
            )
            res = cur.fetchall()
            res = [{"path": s[0], "name": s[1], "rating": s[2]} for s in res]
            return res
        except Exception as e:
            print(f"Error in get_top: {e}")
            return []

    def get_own(self, user_id):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT sound_id, sound_name, rating FROM statistic WHERE owner = %s",
                (user_id,),
            )
            res = cur.fetchall()
            res = [{"path": s[0], "name": s[1], "rating": s[2]} for s in res]
            return res
        except Exception as e:
            print(f"Error in get_own: {e}")
            return []

    def delete_sound(self, sound_id):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "DELETE FROM statistic WHERE sound_id = %s",
                (sound_id,),
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error in plus_one: {e}")
            return False


db = Database()

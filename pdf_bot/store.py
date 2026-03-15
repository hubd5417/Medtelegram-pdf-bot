from telegram import User

from pdf_bot.constants import LANGUAGE, LANGS_SHORT

# In-memory storage
USERS = {}


def create_user(tele_user: User) -> None:
    user_id = tele_user.id
    user_lang_code = tele_user.language_code
    lang_code = "en_GB"

    if (
        user_lang_code is not None
        and user_lang_code != "en"
        and user_lang_code in LANGS_SHORT
    ):
        lang_code = LANGS_SHORT[user_lang_code]

    if user_id not in USERS:
        USERS[user_id] = {
            LANGUAGE: lang_code
        }


def get_user_data(user_id: int):
    return USERS.get(user_id, {})


def set_user_language(user_id: int, lang_code: str):
    if user_id not in USERS:
        USERS[user_id] = {}
    USERS[user_id][LANGUAGE] = lang_code


def increment_task(user_id: int, task: str):
    if user_id not in USERS:
        USERS[user_id] = {}

    USERS[user_id][task] = USERS[user_id].get(task, 0) + 1


def get_all_users():
    return USERS

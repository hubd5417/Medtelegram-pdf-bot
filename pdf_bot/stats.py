import os
import tempfile
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from pdf_bot.store import get_all_users, increment_task
from pdf_bot.constants import LANGUAGE, LANGUAGES

load_dotenv()
DEV_TELE_ID = int(os.environ.get("DEV_TELE_ID", "0"))


def update_stats(update, task):
    increment_task(update.effective_message.from_user.id, task)


def get_stats(update, context):
    users = get_all_users()
    num_users = 0
    num_tasks = 0
    counts = defaultdict(int)
    langs = defaultdict(int)

    for user_id, user in users.items():
        if DEV_TELE_ID and user_id == DEV_TELE_ID:
            continue

        num_users += 1
        for key, value in user.items():
            if key == LANGUAGE:
                lang = value
                if lang == "en":
                    lang = "en_GB"
                langs[lang] += 1
            else:
                num_tasks += value
                counts[key] += value

    update.effective_message.reply_text(
        f"Total users: {num_users:,}\n"
        f"Total tasks: {num_tasks:,}"
    )

    text = "Language stats:\n"
    for key, value in LANGUAGES.items():
        if value in langs:
            text += f"{key}: {langs[value]:,}\n"

    update.effective_message.reply_text(text)

    if counts:
        send_plot(update, counts)


def send_plot(update, counts):
    tasks = sorted(counts.keys())
    nums = [counts[x] for x in tasks]
    y_pos = list(range(len(tasks)))

    plt.rcdefaults()
    _, ax = plt.subplots()

    ax.barh(y_pos, nums, align="center")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tasks)
    ax.set_xlabel("Counts")
    ax.set_ylabel("Tasks")
    ax.invert_yaxis()
    ax.set_title("PDF Bot Statistics")
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        plt.savefig(tf.name)
        with open(tf.name, "rb") as img:
            update.effective_message.reply_photo(img)

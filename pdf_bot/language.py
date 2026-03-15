import gettext

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pdf_bot.constants import LANGUAGE, LANGUAGES
from pdf_bot.store import get_user_data, set_user_language


def send_lang(update, context, query=None):
    lang = get_lang(update, context, query)

    langs = [
        InlineKeyboardButton(key, callback_data=key)
        for key, value in sorted(LANGUAGES.items(), key=lambda x: x[1])
        if value != lang
    ]

    keyboard_size = 2
    keyboard = [
        langs[i:i + keyboard_size] for i in range(0, len(langs), keyboard_size)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    _ = set_lang(update, context, query)
    update.effective_message.reply_text(
        _("Select your language"), reply_markup=reply_markup
    )


def get_lang(update, context, query=None):
    if context.user_data is not None and LANGUAGE in context.user_data:
        return context.user_data[LANGUAGE]

    if query is None:
        user_id = update.effective_message.from_user.id
    else:
        user_id = query.from_user.id

    user = get_user_data(user_id)

    if not user or LANGUAGE not in user:
        lang = "en_GB"
    else:
        lang = user[LANGUAGE]
        if lang == "en":
            lang = "en_GB"

    context.user_data[LANGUAGE] = lang
    return lang


def store_lang(update, context, query):
    lang_code = LANGUAGES[query.data]
    set_user_language(query.from_user.id, lang_code)

    context.user_data[LANGUAGE] = lang_code
    _ = set_lang(update, context, query)
    query.message.edit_text(_("Your language has been set to {}").format(query.data))


def set_lang(update, context, query=None):
    lang = get_lang(update, context, query)
    t = gettext.translation(
        "pdf_bot",
        localedir="locale",
        languages=[lang],
        fallback=True,
    )
    return t.gettext

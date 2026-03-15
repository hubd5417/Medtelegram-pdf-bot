import logging
import os
import sys

from dotenv import load_dotenv
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    Update,
)
from telegram.chataction import ChatAction
from telegram.error import Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PreCheckoutQueryHandler,
    Updater,
)
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request

from pdf_bot import *

load_dotenv()

APP_URL = os.environ.get("APP_URL")
if APP_URL and not APP_URL.endswith("/"):
    APP_URL += "/"

PORT = int(os.environ.get("PORT", "8443"))
TELE_TOKEN = os.environ.get("TELE_TOKEN_BETA", os.environ.get("TELE_TOKEN"))
DEV_TELE_ID = int(os.environ.get("DEV_TELE_ID", "0"))

if not TELE_TOKEN:
    raise RuntimeError("TELE_TOKEN is missing")

TIMEOUT = 20
CALLBACK_DATA = "callback_data"


def main():
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("ocrmypdf").setLevel(logging.WARNING)

    redirect_logging()
    format_string = "{record.level_name}: {record.message}"
    StreamHandler(sys.stdout, format_string=format_string, level="INFO").push_application()
    log = Logger()

    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=8)
    pdf_bot = MQBot(TELE_TOKEN, request=request, mqueue=q)

    updater = Updater(
        bot=pdf_bot,
        use_context=True,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
    )

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_msg, run_async=True))
    dispatcher.add_handler(CommandHandler("help", help_msg, run_async=True))
    dispatcher.add_handler(CommandHandler("setlang", send_lang, run_async=True))
    dispatcher.add_handler(CommandHandler("support", send_support_options, run_async=True))

    if DEV_TELE_ID:
        dispatcher.add_handler(CommandHandler("send", send_msg, Filters.user(DEV_TELE_ID)))
        dispatcher.add_handler(CommandHandler("stats", get_stats, Filters.user(DEV_TELE_ID)))

    dispatcher.add_handler(CallbackQueryHandler(process_callback_query, run_async=True))

    dispatcher.add_handler(
        MessageHandler(Filters.reply & TEXT_FILTER, receive_custom_amount, run_async=True)
    )

    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check, run_async=True))

    dispatcher.add_handler(
        MessageHandler(Filters.successful_payment, successful_payment, run_async=True)
    )

    dispatcher.add_handler(
        MessageHandler(Filters.entity(MessageEntity.URL), url_to_pdf, run_async=True)
    )

    dispatcher.add_handler(compare_cov_handler())
    dispatcher.add_handler(merge_cov_handler())
    dispatcher.add_handler(photo_cov_handler())
    dispatcher.add_handler(text_cov_handler())
    dispatcher.add_handler(watermark_cov_handler())

    dispatcher.add_handler(file_cov_handler())
    dispatcher.add_handler(feedback_cov_handler())

    dispatcher.add_error_handler(error_callback)

    if APP_URL:
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELE_TOKEN,
            webhook_url=APP_URL + TELE_TOKEN,
        )
        log.notice("Bot started webhook")
    else:
        updater.start_polling()
        log.notice("Bot started polling")

    updater.idle()


def start_msg(update: Update, context: CallbackContext):
    update.effective_message.chat.send_action(ChatAction.TYPING)

    create_user(update.effective_message.from_user)

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Welcome to PDF Bot!\n\nType /help to see how to use the bot"),
        parse_mode=ParseMode.HTML,
    )


def help_msg(update, context):
    update.effective_message.chat.send_action(ChatAction.TYPING)
    _ = set_lang(update, context)

    keyboard = [
        [InlineKeyboardButton(_("Set Language 🌎"), callback_data=SET_LANG)],
        [
            InlineKeyboardButton(_("Join Channel"), url=f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text(
        _("Send me a PDF, photo, or URL to convert it."),
        reply_markup=reply_markup,
    )


def process_callback_query(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    query = update.callback_query
    data = query.data

    if CALLBACK_DATA not in context.user_data:
        context.user_data[CALLBACK_DATA] = set()

    if data not in context.user_data[CALLBACK_DATA]:
        context.user_data[CALLBACK_DATA].add(data)

        if data == SET_LANG:
            send_lang(update, context, query)

        elif data in LANGUAGES:
            store_lang(update, context, query)

        if data == PAYMENT:
            send_support_options(update, context, query)

        context.user_data[CALLBACK_DATA].remove(data)

    query.answer()


def send_msg(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.effective_message.reply_text("Usage: /send <telegram_id> <message>")
        return

    tele_id = int(context.args[0])
    message = " ".join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
        update.effective_message.reply_text("Message sent")
    except Exception:
        update.effective_message.reply_text("Failed to send message")


def error_callback(update: Update, context: CallbackContext):
    if isinstance(context.error, Unauthorized):
        return

    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == "__main__":
    main()

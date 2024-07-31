import datetime
import json
import os

import asyncio

from telegram import Update
import telegram
from telegram.ext import Application, ContextTypes, MessageHandler

# check if the config file exists
if not os.path.exists('config.ini'):
    print("config.ini not found, please see README.md for instructions on how to configure the bot")
    exit(1)


import configparser
config = configparser.RawConfigParser()
config.read('config.ini')

TELEGRAM_API_TOKEN = config.get('bot', 'apitoken')
TIME_SECONDS = int(config.get('bot', 'seconds'))
CHAT_ID = int(config.get('bot', 'chatid'))


class MessageIds:
    """
    Tracks the message ids that should be deleted after a certain amount of time.
    We need to store the message ids in a database, so we can delete them after a restart of the bot (telegram api does not provide a way to get message history in a chat)
    """

    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect('mesages.sqlite3')
        self.cursor = self.conn.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS message_ids (chat_id INTEGER, message_id INTEGER, timestamp REAL)')
        self.conn.commit()

    def add(self, chat_id, message_id):
        timestamp = datetime.datetime.now().timestamp()
        self.cursor.execute('INSERT INTO message_ids (chat_id, message_id, timestamp) VALUES (?, ?, ?)', (chat_id, message_id, timestamp))
        self.conn.commit()

    def remove(self, chat_id, message_id):
        self.cursor.execute('DELETE FROM message_ids WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
        self.conn.commit()

    def get(self, chat_id, message_id):
        self.cursor.execute('SELECT timestamp FROM message_ids WHERE chat_id = ? AND message_id = ?', (chat_id, message_id))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None

    @property
    def message_ids(self):
        self.cursor.execute('SELECT * FROM message_ids')
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()


messageIds = MessageIds()



async def delete_message(chat_id, message_id: int, bot, delete_seconds) -> None:
    """
    Deletes the message after {delete_seconds} seconds.
    """
    print(f"  new       chatid:{chat_id} msgid:{message_id} expiresin:{delete_seconds}s")
    messageIds.add(chat_id, message_id)
    await asyncio.sleep(delete_seconds)
    try:
        await bot.delete_message(chat_id, message_id)
        print(f"  deleted   chatid:{chat_id} msgid:{message_id}")
    except telegram.error.BadRequest as e:
        print(f"  message was probably already deleted    chatid:{chat_id} msgid:{message_id} error:{e.message}")
        messageIds.remove(chat_id, message_id)  # remove the message from the database, so the deletion is not scheduled again after a restart



def log_to_file(msg) -> None:
    """
    Log the message to a file.
    """
    with open("messages.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def dictionarize(message_obj):
    """
    Recursively converts python-telegram-bot object to dict, so it can be saved as json
    """

    if not message_obj:
        return {}

    ret_obj = {}

    keys = [
        'text',
        'username',
        'first_name',
        'sender_user_name',
        'caption',
        'type',
        'title',
        'chat_id',
        'message_id',
        'id',
        'media_group_id',
        'mime_type',
        'is_bot',
        'file_name',
        'file_id',
        'file_unique_id',
        'file_size',
        'width',
        'height',
        'duration',
        'supergroup_chat_created',
        'group_chat_created',
        'delete_chat_photo',
        'channel_chat_created'
    ]
    nested_keys = [
        'forward_origin',
        'from_user',
        'sender_user',
        'chat',
        'photo',
        'video',
        'document'
    ]

    if hasattr(message_obj, "date"):
        ret_obj["date"] = message_obj.date.isoformat()

    for key in keys:
        if hasattr(message_obj, key):
            ret_obj[key] = getattr(message_obj, key)

    for key in nested_keys:
        if hasattr(message_obj, key):
            attr = getattr(message_obj, key)

            # if tuple, convert to list
            if isinstance(attr, tuple):
                attr = list(attr)
                for i, item in enumerate(attr):
                    attr[i] = dictionarize(item)
                ret_obj[key] = attr
            else:
                ret_obj[key] = dictionarize(attr)

    if hasattr(message_obj, "api_kwargs"):
        ret_obj["api_kwargs"] = dict(message_obj["api_kwargs"])

    return ret_obj




async def timed_reply(msg, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Helper function to reply to a message and delete the reply after {TIME_SECONDS} seconds
    """
    reply = await update.message.reply_text(msg)
    msg_chat_id = update.message.chat.id
    print(f"  replied to chatid:{msg_chat_id} msgid:{update.message.message_id} with chatid:{msg_chat_id} msgid:{reply.message_id}")
    asyncio.create_task(delete_message(msg_chat_id, reply.message_id, context.bot, TIME_SECONDS))
    

async def on_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Deletes the message after X seconds.
    Customize this code to your needs - a few commented-out examples are provided :)
    """
    msg_chat_id = update.message.chat.id
    if msg_chat_id != CHAT_ID:
        print(f"  unknown chat id '{msg_chat_id}', ignoring the message")
        return
    

    """
    EXAMPLE - filter out bad words
    """
    # blacklist = ["badword92215687", "badword5565685987"]
    # for word in blacklist:
    #     if word in update.message.text:
    #         print(f"  blacklisted word '{word}' found in chatid:{msg_chat_id} msgid:{update.message.message_id}")
    #         await context.bot.delete_message(msg_chat_id, update.message.message_id)
    #         return


    # delete message after X seconds
    asyncio.create_task(delete_message(update.message.chat_id, update.message.message_id, context.bot, TIME_SECONDS))

    """
    ---- POST ACTIONS HERE ----
    even if the part below part crashes, the message will be deleted correctly :)
    you can customize this part to your needs
    """


    """
    EXAMPLE - reply to the message
    """
    # await timed_reply(f"I will delete your message in {TIME_SECONDS} seconds", update, context)

    """
    EXAMPLE - log the message to a file
    """
    # message_obj = dictionarize(update.message)
    # log_to_file(json.dumps(message_obj))


async def startup_tasks(application):
    """
    Schedule the deletion of messages that were saved in the message_ids.json file.
    If the messages should have been deleted already, delete them now.
    """
    print("Scheduling deletion of messages sent before this bot was restarted..")

    ids = messageIds.message_ids
    for chat_id, message_id, timestamp in ids:
        delete_in_seconds = TIME_SECONDS - (datetime.datetime.now().timestamp() - timestamp)
        if delete_in_seconds > 0:
            asyncio.create_task(delete_message(chat_id, message_id, application.bot, delete_in_seconds))
        else:
            asyncio.create_task(delete_message(chat_id, message_id, application.bot, 0))

    print("Scheduling done..")


def main() -> None:
    """
    Initializes the bot and runs it.
    """
    application = Application.builder().token(TELEGRAM_API_TOKEN).post_init(startup_tasks).build()

    # runs the `on_new_message` handler on every message or command
    application.add_handler(MessageHandler(None, on_new_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
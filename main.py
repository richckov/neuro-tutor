import time
import logging
import os
import typing

from concurrent.futures import ThreadPoolExecutor
from telebot import types
from telebot.types import Message
from openai.types.beta.threads import Run
import openai

from bot_instance import bot
from openai_client import client
from database import (setup_database, get_thread_id,
                      save_message, add_member_to_db,
                      set_user_active_status, is_user_active
                      )
from utils import split_text, escape_markdown, clean_response
from admin import admin_menu, show_users, show_balance, show_message
from const import INFO_ABOUT_BOT, ASSISTAND_ID
from image import take_image_prompt_from_user


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

setup_database()

user_threads = {}
executor = ThreadPoolExecutor(max_workers=10)


@bot.message_handler(commands=["start"])
def start(message: Message) -> None:
    markup = types.InlineKeyboardMarkup()
    buttom = types.InlineKeyboardButton(
        text='Хочу общаться',
        callback_data='ai',
    )
    create_image = types.InlineKeyboardButton(
        text='Генерация картинок',
        callback_data='create_image',
    )
    info = types.InlineKeyboardButton(
        text='Общая информация о проекте',
        callback_data='info',
    )
    markup.add(buttom)
    markup.add(create_image)
    markup.add(info)
    user_telegram_id = message.from_user.id
    telegram_username = message.from_user.username or "no_username"
    add_member_to_db(user_telegram_id, telegram_username)
    user_id = message.chat.id
    thread_id = get_thread_id(user_id)
    if not thread_id:
        try:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
        except Exception as e:
            logging.exception("Ошибка при создании потока: %s", e)
    bot.send_message(
        chat_id=user_id,
        text="Привет! Я математический помощник. Задавай свои вопросы!",
        reply_markup=markup
    )


@bot.message_handler(commands=['admin'])
def admin(message: Message) -> None:
    admin_menu(message)


def take_message_from_user(message: Message) -> None:
    markup = types.ReplyKeyboardMarkup(
        one_time_keyboard=True, resize_keyboard=True
    )
    markup.add(types.KeyboardButton('Закончить ответ'))
    bot.send_message(
        chat_id=message.chat.id,
        text="Режим диалога активирован!",
        reply_markup=markup
    )


def run_openai_with_retries(
        thread_id: str, assistant_id: str, retries: int = 3
        ) -> typing.Optional[Run]:
    for attempt in range(retries):
        try:
            return client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
        except openai.RateLimitError:
            wait_time = 2 ** attempt * 5
            logging.warning("⚠️ Rate limit: ждём %s сек...", wait_time)
            time.sleep(wait_time)
        except Exception as e:
            logging.exception("🚨 Ошибка при запросе в OpenAI: %s", e)
            return None
    logging.error("❌ Не удалось выполнить запрос после повторов.")
    return None


@bot.message_handler(func=lambda message: True)
def handle_message(message: Message) -> None:
    user_id = message.chat.id
    user_text = message.text[:4096]

    bot.send_chat_action(message.chat.id, 'typing')
    if not is_user_active(message.from_user.id):
        return

    if message.text == 'Закончить ответ':
        set_user_active_status(message.from_user.id, False)
        bot.send_message(
            chat_id=message.chat.id,
            text="Диалог завершен!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return start(message)

    thread_id = get_thread_id(user_id)
    if not thread_id:
        try:
            new_thread = client.beta.threads.create()
            thread_id = new_thread.id
        except Exception as e:
            logging.exception("Ошибка создания потока: %s", e)
            bot.send_message(
                user_id, "Ошибка: Не удалось создать поток для общения.",
            )
            return

    save_message(user_id, thread_id, "user", user_text)
    try:
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
    except Exception as e:
        logging.exception("Ошибка добавления сообщения в поток: %s", e)
        return

    executor.submit(process_openai_reply, user_id, thread_id)


def process_openai_reply(user_id: int, thread_id: str) -> None:
    run = run_openai_with_retries(thread_id, ASSISTAND_ID)
    if not run:
        bot.send_message(
            user_id,
            "⚠️ Не удалось получить ответ от OpenAI. Попробуйте позже."
        )
        return

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id,
        )
        if run_status.status in ["completed", "failed"]:
            break
        time.sleep(1)

    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = messages.data[0].content[0].text.value
        split_assistant_reply = split_text(assistant_reply)
        escaped_parts = [
            escape_markdown(part) for part in split_assistant_reply
        ]

        for part in escaped_parts:
            save_message(user_id, thread_id, "assistant", part)
            bot.send_message(
                user_id,
                part,
                parse_mode='MarkdownV2',
            )
    except Exception as e:
        logging.exception("Ошибка обработки ответа от OpenAI: %s", e)


@bot.message_handler(content_types=['voice'])
def handle_voice(message: Message) -> None:
    if not is_user_active(message.from_user.id):
        return

    user_id = message.chat.id
    thread_id = get_thread_id(user_id)

    if not thread_id:
        try:
            new_thread = client.beta.threads.create()
            thread_id = new_thread.id
        except Exception as e:
            logging.exception("Ошибка создания потока: %s", e)
            bot.send_message(user_id, "❌ Ошибка: не удалось создать поток.")
            return
    print("Голосовое сообщение получено!")

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        print(file_info)

        file_path = f"voice_{message.message_id}.ogg"
        print(file_path)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        with open(file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        print("Транскрипция:", transcript.text)
        save_message(user_id, thread_id, "user", transcript.text)
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=transcript.text
            )
        except Exception as e:
            logging.exception("Ошибка добавления сообщения в поток: %s", e)
            return
        executor.submit(process_openai_reply, user_id, thread_id)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@bot.message_handler(content_types=['photo'])
def handle_image(message: Message) -> None:
    if not is_user_active(message.from_user.id):
        return

    user_id = message.chat.id
    thread_id = get_thread_id(user_id)

    if not thread_id:
        try:
            new_thread = client.beta.threads.create()
            thread_id = new_thread.id
        except Exception as e:
            logging.exception("Ошибка создания потока: %s", e)
            bot.send_message(user_id, "❌ Ошибка: не удалось создать поток.")
            return

    try:
        # Получаем файл
        file_info = bot.get_file(message.photo[-1].file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

        caption = message.caption or "Что изображено на картинке?"

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[
                {"type": "text", "text": caption},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": file_url
                    }
                }
            ]
        )

        run = run_openai_with_retries(thread_id, ASSISTAND_ID)
        if not run:
            bot.send_message(
                user_id,
                "⚠️ Не удалось получить ответ. Попробуйте позже.",
            )
            return

        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id,
             )
            if run_status.status in ["completed", "failed"]:
                break
            time.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = messages.data[0].content[0].text.value

        cleaned_reply = clean_response(assistant_reply)
        formatted_parts = [
            escape_markdown(part) for part in split_text(cleaned_reply)
        ]

        for part in formatted_parts:
            save_message(user_id, thread_id, "assistant", part)
            bot.send_message(user_id, part, parse_mode='MarkdownV2')

    except Exception as e:
        logging.exception("Ошибка обработки изображения: %s", e)
        bot.reply_to(message, f"❌ Ошибка анализа изображения: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == 'ai')
def start_chat(call: Message) -> None:
    set_user_active_status(call.from_user.id, True)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    take_message_from_user(call.message)


def info(message: Message) -> None:
    markup = types.InlineKeyboardMarkup()
    back_menu = types.InlineKeyboardButton(
        text='В главное меню',
        callback_data='back_menu',
    )
    markup.add(back_menu)
    bot.send_message(
        text=INFO_ABOUT_BOT,
        chat_id=message.chat.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: Message) -> None:
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.data == 'ai':
        take_message_from_user(call.message)
    elif call.data == 'info':
        info(call.message)
    elif call.data == 'create_image':
        take_image_prompt_from_user(call.message)
    elif call.data == 'back_menu':
        start(call.message)
    elif call.data == 'show_users':
        show_users(call.message)
    elif call.data == 'show_balance':
        show_balance(call.message)
    elif call.data == 'show_history':
        show_message(call.message)
    elif call.data == 'menu_admin':
        admin(call.message)


if __name__ == "__main__":
    logging.info("Бот запущен...")
    bot.polling(none_stop=True)

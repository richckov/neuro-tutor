import time

from telebot import types
from telebot.types import Message

from database import (
    take_users, take_messages,
    take_user_telegram_id, delete_invalid_user
    )
from bot_instance import bot
from utils import split_text
from balance import checking_balance
from const import ADMIN_IDS


def admin_menu(message: Message) -> None:

    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(
            chat_id=message.chat.id,
            text="⛔ У вас нет прав администратора!")
        return

    markup = types.InlineKeyboardMarkup()
    show_users = types.InlineKeyboardButton(
        text='Показать пользователей',
        callback_data='show_users'
    )

    show_balance = types.InlineKeyboardButton(
        text='Показать баланс',
        callback_data='show_balance',
    )

    show_history = types.InlineKeyboardButton(
        'История сообщений', callback_data='show_history',
    )
    setup_mailing = types.InlineKeyboardButton(
        text='Запустить рассылку', callback_data='take_mailing_message',
    )

    markup.add(show_users)
    markup.add(show_history)
    markup.add(show_balance)
    markup.add(setup_mailing)

    bot.send_message(
        chat_id=message.chat.id,
        text="🔐 Админ-панель:",
        reply_markup=markup
    )


def show_users(message: Message) -> None:
    menu_markup = types.InlineKeyboardMarkup()
    menu_admin = types.InlineKeyboardButton(
        text='Главное меню', callback_data='menu_admin',
    )
    menu_markup.add(menu_admin)

    users = take_users()

    split_users = split_text(users)

    bot.send_message(
        chat_id=message.chat.id,
        text=split_users,
        reply_markup=menu_markup,
    )


def show_balance(message: Message) -> None:
    menu_markup = types.InlineKeyboardMarkup()
    menu_admin = types.InlineKeyboardButton(
        text='Главное меню', callback_data='menu_admin',
    )
    menu_markup.add(menu_admin)

    bot.send_message(
        text=checking_balance(),
        chat_id=message.chat.id,
        reply_markup=menu_markup,
    )


def show_message(message: Message) -> None:
    menu_markup = types.InlineKeyboardMarkup()
    menu_admin = types.InlineKeyboardButton(
        text='Главное меню', callback_data='menu_admin',
    )
    menu_markup.add(menu_admin)

    messages = take_messages()

    split_messages = split_text(messages)

    bot.send_message(
        chat_id=message.chat.id,
        text=split_messages,
        reply_markup=menu_markup
    )


def take_mailing_message(message: Message):
    bot.send_message(
        chat_id=message.chat.id,
        text="Введите сообщение для рассылки всем пользователям"
    )
    bot.register_next_step_handler(message, mailing)


def mailing(message: Message) -> None:
    users = take_user_telegram_id()
    msg = message.text
    if not users:
        bot.send_message(message.chat.id, "❌ Нет пользователей для рассылки")
        return
    success = 0
    errors = 0
    error_details = []

    for user in users:
        chat_id = user[0]
        try:
            # Проверка валидности chat_id
            if not isinstance(chat_id, int):
                errors += 1
                error_details.append(f"Invalid ID: {chat_id}")
                continue

            # Отправка с задержкой 0.5 сек для избежания лимитов API
            bot.send_message(chat_id=chat_id, text=msg)
            success += 1
            time.sleep(0.5)

        except Exception as e:
            errors += 1
            error_details.append(f"{chat_id}: {str(e)}")
            # Удаляем невалидного пользователя из БД
            delete_invalid_user(chat_id)

    # Формируем отчет
    report = (
        f"📊 Результат рассылки:\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {errors}\n"
        f"⚙ Детали ошибок:\n" + "\n".join(error_details[:5])  # Первые 5 ошибок
    )

    # Отправляем отчет администратору
    bot.send_message(
        chat_id=ADMIN_IDS[0],
        text=report[:4000]  # Обрезаем до лимита Telegram
    )
    try:
        for user in users:
            bot.send_message(
                chat_id=user[0],
                text=msg
            )
    except Exception as e:
        bot.send_message(
            chat_id=ADMIN_IDS[0],
            text=f'Ошибка при отправке рассылки: {e}'
        )

from telebot import types
from telebot.types import Message

from database import take_users, take_messages
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

    markup.add(show_users)
    markup.add(show_history)
    markup.add(show_balance)

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

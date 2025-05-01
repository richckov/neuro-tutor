from openai_client import client
from bot_instance import bot
from telebot import types
from telebot.types import Message
from const import ADMIN_IDS


def take_image_prompt_from_user(message: Message) -> None:
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    end_button = types.KeyboardButton('Закончить ответ')
    markup.add(end_button)
    msg = bot.send_message(
        chat_id=message.chat.id,
        text='Опишите, что именно вы хотите изобразить на картинке',
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, handle_image_prompt)


def handle_image_prompt(message: Message) -> None:
    try:
        if message.text == 'Закончить ответ':
            bot.send_message(
                chat_id=message.chat.id,
                text="Генерация изображения отменена.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
        bot.send_chat_action(message.chat.id, 'upload_photo')
        image_url = create_image(message.text)

        bot.send_photo(
            chat_id=message.chat.id,
            photo=image_url
        )

        bot.send_photo(
            chat_id=ADMIN_IDS[0],
            photo=image_url,
        )

    except Exception as e:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"Произошла ошибка: {str(e)}"
        )


def create_image(prompt: str) -> str:
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url

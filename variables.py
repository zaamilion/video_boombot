from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
DEFAULT_SOUND = "myinstants_sounds/default.mp3"
# Конфигурация
API_TOKEN = os.environ.get("TELEGRAM_API_KEY")
BOT_URL = os.environ.get("BOT_URL")

links = [
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExMHc2bWR4MngyZ2FtZHR0YndkeHh4M2xtMjVnY2ZodmJwZW9rN3pwZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/GRPy8MKag9U1U88hzY/giphy.gif",
    "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3BsMml3cjgzMjF2MHZ5NDZhOG1yd25wN2NoeWV1YWN1cGI5bnliaCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/S2IfEQqgWc0AH4r6Al/giphy.gif",
    "https://media.giphy.com/media/Cmr1OMJ2FN0B2/giphy.gif?cid=790b7611nw4ohbhoi8dtntopsv0gj7qwtq63yvzgw02ooif3&ep=v1_gifs_search&rid=giphy.gif&ct=g",
    "https://media.giphy.com/media/fX5cZemSfX1cMZYuUJ/giphy.gif?cid=790b7611nw4ohbhoi8dtntopsv0gj7qwtq63yvzgw02ooif3&ep=v1_gifs_search&rid=giphy.gif&ct=g",
]

bot = Bot(token=API_TOKEN)


# markups

from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

builder = ReplyKeyboardBuilder()
builder.button(text="🔄 Режим: Звук")
builder.row(KeyboardButton(text="🎵 Топ звуков"), KeyboardButton(text="🔥 Популярные"))
builder.row(KeyboardButton(text="🔍 Поиск"))
builder.row(KeyboardButton(text="👤 Мои звуки"))
main_sound_menu_markup = builder.as_markup(resize_keyboard=True)


builder = ReplyKeyboardBuilder()
builder.button(text="🔄 Режим: Взрыв")
main_explosion_menu_markup = builder.as_markup(resize_keyboard=True)

builder = InlineKeyboardBuilder()
builder.button(text="Попробовать на примере", callback_data="default")
default_note_markup = builder.as_markup()

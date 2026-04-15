import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from aiogram import Bot, Dispatcher, F, types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    FSInputFile,
    InputFile,
)
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_audioclips,
    CompositeAudioClip,
)
from aiogram.utils.chat_action import ChatActionMiddleware
import random
import find_sounds  # Импортируем ваш модуль
from dotenv import load_dotenv
import variables
from db import Database
import shutil
import handlers
from variables import bot

load_dotenv()
# Конфигурация
API_TOKEN = os.getenv("TELEGRAM_API_KEY")


# Инициализация бота

dp = Dispatcher()
dp.include_router(handlers.router)
dp.message.middleware(ChatActionMiddleware())


async def main():
    await dp.start_polling(bot)
    print("work")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from aiogram import Bot, Dispatcher, F, types, Router
from aiogram.filters import Command, StateFilter, or_f
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
from db import db
from utils import *

import utils


class SoundStates(StatesGroup):
    waiting_for_upload = State()
    waiting_for_query = State()
    browsing_search = State()
    browsing_top = State()  # Новое состояние для топа
    browsing_popular = State()  # Новое состояние для популярных
    browsing_own = State()

    # Добавляем под-состояния для режимов
    class Modes(StatesGroup):
        sound_mode = State()  # Режим добавления звука
        explosion_mode = State()  # Режим взрыва


router = Router()


@router.message(Command("start"), F.text.len() == 6)
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(SoundStates.Modes.sound_mode)
    db.add_user(str(message.from_user.id))

    await message.answer_animation(
        animation=random.choice(variables.links),
        caption="🎬 <b>Добро пожаловать в ШиномонтажBot!</b>\n\n"
        "Я могу добавить конец вашего видео-кружка любой звук или БУУМ.\n\n"
        "<b>Как использовать:</b>\n"
        '1. Нажмите "🔍 Поиск" или введите /change_sound\n'
        "2. Выберите звук из предложенных\n"
        "3. Отправьте мне видео-кружок\n\n"
        "Или измените режим и получите видео-кружок с неожаданным концом...\n\n"
        "Попробуйте прямо сейчас!",
        parse_mode="HTML",
        reply_markup=variables.main_sound_menu_markup,
    )


@router.message(Command("start"), F.text.len() > 6)
async def set_sound_cmd(message: types.Message, state: FSMContext):
    await state.set_state(SoundStates.Modes.sound_mode)
    db.add_user(str(message.from_user.id))
    path = "myinstants_sounds/" + message.text[7:] + ".mp3"
    db.edit_value(str(message.from_user.id), path)
    await message.answer(
        f"✅ Звук выбран!\n"
        "Теперь отправьте мне видео-кружок, и я добавлю этот звук в конец!",
        parse_mode="HTML",
        reply_markup=variables.main_sound_menu_markup,
    )


@router.message(F.text == "🔄 Режим: Звук")
async def cmd_sound_mode(message: types.Message, state: FSMContext):
    await state.set_state(SoundStates.Modes.explosion_mode)
    await message.answer(
        "✅ Режим изменен на Взрыв",
        reply_markup=variables.main_explosion_menu_markup,
    )


@router.message(F.text == "🔄 Режим: Взрыв")
async def cmd_sound_mode(message: types.Message, state: FSMContext):
    await state.set_state(SoundStates.Modes.sound_mode)
    await message.answer(
        "✅ Режим изменен на Звук",
        reply_markup=variables.main_sound_menu_markup,
    )


@router.message(Command("change_sound"))
@router.message(F.text == "🔍 Поиск")
async def cmd_change_mode(message: Message, state: FSMContext):
    # Создаем клавиатуру с примером запроса
    await message.answer(
        "🔍 <b>Поиск звуков</b>\n\n"
        "Введите название или описание звука, который вы хотите добавить в видео.\n"
        "Например:\n"
        "• <i>Tralalero Tralala</i>\n"
        "• <i>Смешной звук</i>\n"
        "• <i>Сигма бой</i>\n\n",
        parse_mode="HTML",
    )
    await state.set_state(SoundStates.waiting_for_query)


async def show_sound_browser(
    message: Message, sounds: list, title: str, state: FSMContext, page: int = 0
):
    PAGE_SIZE = 5  # Количество звуков на странице

    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    data["sounds"] = sounds
    await state.set_data(data)
    # Добавляем кнопки для звуков текущей страницы
    for idx, sound in enumerate(sounds[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]):
        db.add_sound(sound["path"], sound["name"])
        builder.row(
            InlineKeyboardButton(
                text=f"🎵 {sound['name']}",
                callback_data=f"preview_{title}_{page}_{idx}",
            )
        )

    # Кнопки навигации
    nav_buttons = []
    mode = title
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"browse_{mode}_{page-1}"
            )
        )
    if (page + 1) * PAGE_SIZE < len(sounds):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"browse_{mode}_{page+1}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    if await state.get_state() == SoundStates.browsing_own:
        builder.row(
            InlineKeyboardButton(text="📤 Загрузить новый звук", callback_data="upload")
        )

    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_browser"))

    await message.answer(
        f"<b>{title}</b> (страница {page+1}):",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await state.update_data(current_sounds=sounds, current_page=page)


# Новые хендлеры для топ и популярных звуков
@router.message(F.text == "🎵 Топ звуков")
async def show_top_sounds(message: Message, state: FSMContext):
    top_sounds = utils.get_top_sounds()
    data = await state.get_data()
    data["sounds"] = top_sounds
    await state.set_data({"sounds": data})
    await state.set_state(SoundStates.browsing_top)
    await show_sound_browser(message, top_sounds, "Топ звуков", state)


@router.message(F.text == "🔥 Популярные")
async def show_popular_sounds(message: Message, state: FSMContext):
    popular_sounds = await find_sounds.get_popular()
    data = await state.get_data()
    data["sounds"] = popular_sounds
    await state.set_data(data)
    await state.set_state(SoundStates.browsing_popular)
    await show_sound_browser(message, popular_sounds, "Популярные звуки", state)


@router.message(F.text == "👤 Мои звуки")
async def show_user_sounds(message: Message, state: FSMContext):
    sounds = db.get_own(str(message.from_user.id))
    data = await state.get_data()
    data["sounds"] = sounds
    await state.set_data(data)
    await state.set_state(SoundStates.browsing_own)
    await show_sound_browser(message, sounds, "Ваши звуки", state)


@router.callback_query(F.data == "upload")
async def upload_sound(callback: CallbackQuery, state: FSMContext):
    # Удаляем предыдущее сообщение с кнопками (если есть)
    try:
        await callback.message.delete()
    except:
        pass

    # Отправляем инструкцию
    await callback.message.answer(
        "🎵 <b>Загрузка звука</b>\n\n"
        "Отправьте мне аудиофайл в формате MP3 (до 1MB), который вы хотите добавить в библиотеку.\n\n"
        "<i>Файл должен быть коротким (до 15 секунд) и хорошего качества.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
            ]
        ),
    )

    await state.set_state(SoundStates.waiting_for_upload)
    await callback.answer()


@router.message(SoundStates.waiting_for_upload, F.audio)
async def handle_audio_upload(message: Message, state: FSMContext):
    # Проверяем формат и размер файла
    print(message.caption)
    if not message.audio.file_name.endswith(".mp3"):
        await state.set_state(SoundStates.waiting_for_upload)
        await message.answer("❌ Файл должен быть в формате MP3")
        await message.delete()
        return

    if message.audio.file_size > 1_000_000:  # 1MB
        await state.set_state(SoundStates.waiting_for_upload)
        await message.answer("❌ Файл слишком большой (максимум 1MB)")
        await message.delete()
        return
    if message.caption is None:
        await state.set_state(SoundStates.waiting_for_upload)
        await message.answer("❌ Добавьте название звука")
        await message.delete()
        return
    try:
        # Скачиваем файл
        file_id = message.audio.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Сохраняем файл
        download_path = utils.add_sound(message.caption, str(message.from_user.id))
        if not download_path:
            await state.set_state(SoundStates.waiting_for_upload)
            await message.answer("❌ Попробуйте другое название")
            await message.delete()
            return
        await bot.download_file(file_path, download_path)

        # Проверяем длину аудио (примерная реализация)
        audio_length = await get_audio_length(download_path)
        if audio_length > 15.0:  # 15 секунд
            os.remove(download_path)
            db.delete_sound(download_path)
            await state.get_state(SoundStates.waiting_for_upload)
            await message.answer("❌ Слишком длинное аудио (максимум 15 секунд)")
            await message.delete()
            return
        await message.answer(
            f"✅ <b>{message.caption}</b> успешно загружен!\n"
            f"Поделиться звуком: {variables.BOT_URL}?start={Path(download_path).stem}\n\n"
            "Теперь вы можете выбрать его в списке звуков.",
            parse_mode="HTML",
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке: {str(e)}")
        os.remove(download_path)
        db.delete_sound(download_path)


# Вспомогательная функция для проверки длины аудио


# Обработчики для навигации
@router.callback_query(F.data.startswith("browse_"))
async def browse_page(callback: CallbackQuery, state: FSMContext):
    _, mode, page = callback.data.split("_")
    page = int(page)
    sounds = (await state.get_data())["sounds"]

    await callback.message.delete()
    await show_sound_browser(callback.message, sounds, mode, state, page)


# Обработчик предпрослушивания
@router.callback_query(F.data.startswith("preview_"))
async def preview_sound(callback: CallbackQuery, state: FSMContext):
    _, mode, page, idx = callback.data.split("_")
    page = int(page)
    idx = int(idx)

    data = await state.get_data()
    sounds = data.get("current_sounds", [])
    sound = sounds[page * 5 + idx]

    # Отправляем звук для предпрослушивания
    await callback.message.answer_voice(
        voice=FSInputFile(sound["path"]),
        caption=f"Прослушивание: {sound['name']}\n\n Поделиться звуком: {variables.BOT_URL}?start={Path(sound['path']).stem}\n\nХотите выбрать этот звук?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Выбрать",
                        callback_data=f"select_browsed_{mode}_{page}_{idx}",
                    ),
                    InlineKeyboardButton(text="↩️ Назад", callback_data=f"back"),
                ]
            ]
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "back")
async def back_to_browse(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SoundStates.browsing_top)
    await callback.message.delete()


# Обработчик выбора звука
@router.callback_query(F.data.startswith("select_browsed_"))
async def select_browsed_sound(callback: CallbackQuery, state: FSMContext):
    print(callback.data.split("_"))
    _, _, mode, page, idx = callback.data.split("_")
    page = int(page)
    idx = int(idx)

    data = await state.get_data()
    sounds = data.get("current_sounds", [])
    sound = sounds[page * 5 + idx]

    db.edit_value(str(callback.from_user.id), sound["path"])

    await callback.message.answer(
        f"✅ Выбран звук: <b>{sound['name']}</b>\n"
        f"Поделиться звуком: {variables.BOT_URL}?start={Path(sound['path']).stem}\n\n"
        "Теперь отправьте мне видео-кружок!",
        parse_mode="HTML",
        reply_markup=variables.default_note_markup,
    )
    await callback.message.delete()
    await state.set_state(SoundStates.Modes.sound_mode)


# Обработчик закрытия браузера
@router.callback_query(F.data == "close_browser")
async def close_browser(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(SoundStates.Modes.sound_mode)
    await callback.answer("Браузер звуков закрыт")


@router.message(SoundStates.waiting_for_query)
async def process_sound_query(message: Message, state: FSMContext):
    query = message.text
    if not query or len(query) < 2:
        await message.answer(
            "❌ Слишком короткий запрос. Попробуйте что-то более конкретное."
        )
        return

    # Показываем анимацию загрузки
    search_msg = await message.answer(
        "🔍 Ищу звуки по запросу: <b>" + query + "</b>...", parse_mode="HTML"
    )

    try:
        sounds = await find_sounds.main(query)

        if not sounds:
            await search_msg.edit_text(
                "😕 Ничего не найдено по запросу: <b>" + query + "</b>\n\n"
                "Попробуйте:\n"
                "• Изменить формулировку\n"
                "• Использовать английские слова\n"
                "• Попробовать более популярный звук",
                parse_mode="HTML",
            )
            return
        data = await state.get_data()
        data["sounds"] = sounds
        await state.set_data(data)
        await state.set_state(SoundStates.browsing_search)
        await show_sound_browser(message, sounds, "Поиск...", state)

    except Exception as e:
        print(e)
        await search_msg.edit_text(
            "⚠️ Произошла ошибка при поиске звуков.\n"
            "Попробуйте еще раз или измените запрос."
        )
        await state.set_state(SoundStates.Modes.sound_mode)


async def process_sound_selection(callback: CallbackQuery, state: FSMContext):
    return
    sound_idx = int(callback.data.split("_")[-1])

    data = await state.get_data()
    sounds = data.get("sounds", [])
    builder = InlineKeyboardBuilder()
    builder.button(text="Попробовать на примере", callback_data="default")
    if 0 <= sound_idx < len(sounds):
        name, path = sounds[sound_idx]
        db.edit_value(str(callback.from_user.id), path)
        # Отправляем мини-превью звука
        ref_path = path.split("/")[-1][:-4]
        await callback.message.answer(
            f"✅ Выбран звук: <b>{name}</b>\n"
            f"Поделиться звуком: {variables.BOT_URL}?start={ref_path}\n\n"
            "Теперь отправьте мне видео-кружок, и я добавлю этот звук в конец!",
            parse_mode="HTML",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )

        await callback.message.delete()  # Удаляем сообщение с выбором
    else:
        await callback.answer("⚠️ Неверный выбор звука")

    await state.set_state(SoundStates.Modes.sound_mode)


# Обработчик кнопки "Заново"
"""@router.callback_query(SoundStates.waiting_for_selection, F.data == "search_again")
async def process_search_again(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название трека для поиска:")
    await state.set_state(SoundStates.waiting_for_query)"""


# Обработчик кнопки "Сброс"
"""@router.callback_query(SoundStates.waiting_for_selection, F.data == "reset_sound")
async def process_reset_sound(callback: CallbackQuery, state: FSMContext):
    db.reset(str(callback.from_user.id))
    await callback.message.edit_text("Звук сброшен до значения по умолчанию")
    await state.set_state(SoundStates.Modes.sound_mode)"""


@router.callback_query(F.data == "default")
async def handle_default(callback: types.CallbackQuery, state: FSMContext):
    progress_msg = await callback.message.answer(
        "⏳ <b>Начинаю обработку видео...</b>\n\n" "Это займет несколько секунд...",
        parse_mode="HTML",
    )
    await process_video_note(callback.message, state, True, callback.from_user.id)

    # Удаляем сообщение о прогрессе
    try:
        await progress_msg.delete()
    except:
        pass


@router.message(or_f(F.video, F.video_note))
async def handle_video_note(message: types.Message, state: FSMContext):
    # Отправляем сообщение о начале обработки
    try:

        cur_mode = await state.get_state()
        print(cur_mode)
        if not cur_mode or cur_mode == SoundStates.Modes.sound_mode:
            progress_msg = await message.answer(
                "⏳ <b>Начинаю обработку видео...</b>\n\n"
                "Это займет несколько секунд...",
                parse_mode="HTML",
            )
            sound = db.get_sound(str(message.from_user.id))
            if sound != variables.DEFAULT_SOUND:
                db.plus_one(sound)
                print("plus")
            res = await process_video_note(message, state)
            print("res")
        elif cur_mode == SoundStates.Modes.explosion_mode:
            progress_msg = await message.answer(
                "⏳ <b>Начинаю обработку видео...</b>\n\n"
                "Это займет несколько секунд...",
                parse_mode="HTML",
            )
            res = await process_add_boom(message)
    # Удаляем сообщение о прогрессе
    except Exception as e:
        await message.answer(f"⚠️ Произошла ошибка при обработке: {str(e)}")
    finally:
        try:
            await progress_msg.delete()
        except:
            pass

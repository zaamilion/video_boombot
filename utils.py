import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    FSInputFile,
    InputFile,
)
import moviepy
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
)
import mutagen.mp3
from db import db
import shutil
from variables import bot
from transliterate import translit

from mutagen.mp3 import MP3


# Показать список звуков для выбора
async def show_sound_selection(message: Message, sounds: list, query: str):
    builder = InlineKeyboardBuilder()

    # Ограничиваем количество вариантов, чтобы не перегружать пользователя
    max_display = 5
    for idx, (name, path) in enumerate(sounds[:max_display]):
        db.add_sound(path, name)
        builder.add(
            InlineKeyboardButton(
                text=f"🎵 {name[:20] + '...' if len(name) > 20 else name}",
                callback_data=f"select_sound_{idx}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="🔄 Искать заново", callback_data="search_again"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="reset_sound"),
    )
    await message.answer(
        f"🎧 <b>Найдены звуки по запросу</b>: <i>{query}</i>\n\n"
        "Выберите звук из списка ниже:\n"
        f"(первые {max_display} результатов)",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    return sounds[:max_display]


async def process_video_note(
    message: Message, state: FSMContext, default=False, user_id=0
):
    # Создаем уникальные имена временных файлов
    input_path = None
    output_path = None
    video_clip = None
    audio_clip = None

    try:
        # Скачиваем видео
        if not default:
            await bot.send_chat_action(
                message.from_user.id, ChatAction.RECORD_VIDEO_NOTE
            )
            current_sound = db.get_sound(str(message.from_user.id))
            if message.video_note:
                file_id = message.video_note.file_id
            else:
                file_id = message.video.file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path

            with NamedTemporaryFile(suffix=".mp4", delete=False) as temp_input:
                input_path = temp_input.name
                await bot.download_file(file_path, destination=input_path)
        else:
            await bot.send_chat_action(
                message.from_user.id, ChatAction.RECORD_VIDEO_NOTE
            )
            shutil.copy("./default/default.mp4", f"./default/default_{user_id}.mp4")
            current_sound = db.get_sound(str(user_id))
            input_path = f"./default/default_{user_id}.mp4"
        output_path = f"{input_path}_processed.mp4"

        # Загружаем видео
        video_clip = VideoFileClip(input_path)

        video_clip.audio = video_clip.audio.with_volume_scaled(0.3)

        # Обработка аудио
        if os.path.exists(current_sound):
            audio_clip = AudioFileClip(current_sound)
            audio_clip = audio_clip.with_duration(
                min(audio_clip.duration, video_clip.duration)
            )
            # Создаем новый аудиоклип
            if video_clip.audio:
                # Комбинируем оригинальное аудио (уже с пониженной громкостью) и новый звук
                final_audio = CompositeAudioClip(
                    [
                        video_clip.audio,
                        audio_clip.with_start(
                            max(0, video_clip.audio.duration - audio_clip.duration)
                        ),
                    ]
                )
            else:
                # Если в видео нет звука, просто добавляем новый звук в конец
                final_audio = audio_clip.with_start(video_clip.duration)

            # Устанавливаем новый аудиопоток (совместимый способ)
            video_clip = video_clip.with_audio(final_audio)

        # Сохраняем видео
        video_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=video_clip.fps,
            threads=4,
            preset="fast",
            logger=None,
            ffmpeg_params=["-movflags", "faststart"],  # Для оптимизации
        )

        # Отправляем результат
        with open(output_path, "rb") as video_file:
            await message.answer_video_note(FSInputFile(output_path))

    except Exception as e:
        error_msg = f"Ошибка обработки видео: {str(e)}"
        print(f"Full error: {type(e)} - {str(e)}")
        import traceback

        traceback.print_exc()
        await message.answer("Не удалось обработать видео. Попробуйте другое видео.")

    finally:
        # Закрываем все ресурсы в правильном порядке
        for clip in [video_clip, audio_clip]:
            if clip:
                try:
                    clip.close()
                except:
                    pass

        # Удаляем временные файлы с несколькими попытками
        pathes = [output_path]
        if not default:
            pathes.append(input_path)
        for path in pathes:
            if path and os.path.exists(path):
                os.remove(path)


in_work = []


async def process_add_boom(message: types.message):
    if message.from_user.id not in in_work:
        in_work.append(message.from_user.id)
    else:
        return
    try:
        if message.video_note:
            file_id = message.video_note.file_id  # Get file id
        else:
            file_id = message.video.file_id
        file = await bot.get_file(file_id)  # Get file path
        await bot.download_file(file.file_path, f"./videos/{message.from_user.id}.mp4")
        result = await genering(message.from_user.id)
        if result is True:
            file = types.FSInputFile(f"./results/{message.from_user.id}.mp4")
            await bot.send_video_note(message.from_user.id, file)
        else:
            pass
    except Exception as e:
        pass
    finally:
        in_work.remove(message.from_user.id)
        try:
            os.remove(f"./videos/{message.from_user.id}.mp4")
        except:
            pass


async def genering(user_id: int) -> bool:
    try:
        user_video_path = f"./videos/{user_id}.mp4"
        boom_video_path = "./assets/boom.mp4"

        clip_1 = moviepy.VideoFileClip(user_video_path)
        clip_2 = moviepy.VideoFileClip(boom_video_path)

        size = clip_1.size
        clip_2 = clip_2.resized(size)

        Mearged_video = moviepy.concatenate_videoclips([clip_1, clip_2])

        Mearged_video.write_videofile(f"./results/{user_id}.mp4")
        Mearged_video.close()
        clip_1.close()
        clip_2.close()
        return True
    except Exception as e:
        print(e)
        return False


def get_top_sounds(limit=20):
    return db.get_top(limit)


def get_popular_sounds(limit=20):
    return []


def get_transliter(name):
    return translit(name, "ru", reversed=True)


def add_sound(name, user_id):
    path = "myinstants_sounds/" + get_transliter(name) + ".mp3"
    if db.add_sound(path, name, user_id):
        return path
    else:
        return None


async def get_audio_length(file_path):
    try:
        audio = MP3(file_path)
        print(audio)
        return audio.info.length
    except:
        return 0

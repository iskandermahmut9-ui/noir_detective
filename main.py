import asyncio
import logging
import os
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from google import genai
from google.genai import types as g_types

# =============== НАСТРОЙКИ ===============
# 1. Читаем ключи из настроек сервера (Render)
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 2. Проверяем, на месте ли ключи
if not TG_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ ОШИБКА: Ключи не найдены! Проверь Environment Variables на Render.")

# 3. ИСПОЛЬЗУЕМ РАБОЧУЮ МОДЕЛЬ (исправлено)
MODEL_ID = "gemini-flash-latest" 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Инициализация бота
bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
client = None # Клиент Gemini будет создан при запуске

# Хранилище истории диалогов (в памяти)
user_histories = {}

# --- СИСТЕМНАЯ ИНСТРУКЦИЯ (МОЗГИ БОТА) ---
SYSTEM_INSTRUCTION = """
Ты — ведущий текстового квеста в жанре "Нуар-Детектив" (1940-е, дождь, джаз, ч/б кино).
Твоя задача:
1. Вести игру, описывать сцены мрачно и атмосферно.
2. Предлагать игроку выбор или спрашивать "Твои действия?".
3. Генерировать описание для картинки (image_prompt) на АНГЛИЙСКОМ языке.

ТЫ ОБЯЗАН ОТВЕЧАТЬ СТРОГО В ФОРМАТЕ JSON:
{
  "text": "Текст сюжета на русском языке...",
  "image_prompt": "visual description of the scene, noir style, black and white, dramatic lighting, 8k"
}
"""

async def generate_response(user_id, user_input):
    """Отправляет запрос в Gemini и получает JSON с сюжетом и картинкой"""
    try:
        # Если пользователя нет в базе — создаем пустую историю
        if user_id not in user_histories:
            user_histories[user_id] = []

        # Добавляем сообщение игрока в историю
        user_histories[user_id].append(
            g_types.Content(role="user", parts=[g_types.Part.from_text(text=user_input)])
        )

        # Ограничиваем память (последние 20 сообщений), чтобы не перегружать
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        # Запрос к Gemini
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=user_histories[user_id],
            config=g_types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json" # Заставляем отвечать JSON-ом
            )
        )
        
        # Разбираем ответ (JSON -> Python)
        result_json = json.loads(response.text)
        story_text = result_json.get("text", "Ошибка генерации текста.")
        img_prompt = result_json.get("image_prompt", None)

        # Сохраняем ответ бота в историю
        user_histories[user_id].append(
            g_types.Content(role="model", parts=[g_types.Part.from_text(text=response.text)])
        )

        return story_text, img_prompt

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        # Если произошла ошибка, возвращаем текст ошибки, чтобы ты видел в боте
        return f"🕵️‍♂️ *Сбой в архивах...* (Ошибка: {e})", None

def get_image_url(prompt):
    """Создает ссылку на картинку через Pollinations (бесплатно)"""
    if not prompt:
        return None
    # Очищаем промпт для URL
    clean_prompt = prompt.replace(" ", "%20")
    seed = random.randint(1, 10000)
    # Формируем ссылку
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}%20noir%20style%20monochrome?width=1024&height=1024&seed={seed}&nologo=true"
    return url

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Очищаем историю при старте
    user_histories[message.from_user.id] = []
    
    await message.answer("🎷 *Загрузка дела...*")
    
    # Первый ход игры
    text, img_prompt = await generate_response(message.from_user.id, "Начни игру. Я детектив, сижу в своем кабинете, идет дождь.")
    
    # Отправка ответа
    if img_prompt:
        await message.answer_photo(
            photo=get_image_url(img_prompt),
            caption=text
        )
    else:
        await message.answer(text)

@dp.message()
async def handle_all_messages(message: types.Message):
    # Показываем статус "отправка фото", чтобы юзер понимал, что бот думает
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    
    text, img_prompt = await generate_response(message.from_user.id, message.text)
    
    if img_prompt:
        try:
            await message.answer_photo(
                photo=get_image_url(img_prompt),
                caption=text
            )
        except Exception as e:
            logging.error(f"Ошибка отправки фото: {e}")
            await message.answer(text) # Если фото не грузится, шлем просто текст
    else:
        await message.answer(text)

# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---
async def main():
    global client
    # Инициализация клиента Google Gemini
    client = genai.Client(api_key=GEMINI_KEY)
    
    logging.info(f"✅ Бот запущен! Используем модель: {MODEL_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
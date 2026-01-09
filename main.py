import asyncio
import logging
import os
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from google import genai
from google.genai import types as g_types

# =============== НАСТРОЙКИ ===============
# os.getenv берет ключ из настроек сервера (Render), а не из этого файла
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Проверка на всякий случай
if not TG_TOKEN:
    print("Ошибка: Токен Telegram не найден!")
if not GEMINI_KEY:
    print("Ошибка: Ключ Gemini не найден!")

# Настройка модели
MODEL_ID = "gemini-1.5-flash" # Рабочая лошадка

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
client = None # Инициализируем позже

# Хранилище истории (в памяти для MVP)
user_histories = {}

# --- СИСТЕМНЫЙ ПРОМПТ ---
SYSTEM_INSTRUCTION = """
Ты — ведущий текстового квеста в жанре "Нуар-Детектив" (1940-е, дождь, джаз, черно-белое кино).
Твоя задача:
1. Вести игру, описывать сцены мрачно и атмосферно.
2. Предлагать игроку выбор или спрашивать "Твои действия?".
3. Генерировать описание для картинки (image_prompt) на АНГЛИЙСКОМ языке, описывающее текущую сцену.

ТЫ ОБЯЗАН ОТВЕЧАТЬ В ФОРМАТЕ JSON:
{
  "text": "Текст сюжета на русском языке...",
  "image_prompt": "visual description of the scene, noir style, black and white, dramatic lighting, 8k"
}
"""

async def generate_response(user_id, user_input):
    """Генерация ответа через Gemini с памятью"""
    try:
        # Инициализация истории, если нет
        if user_id not in user_histories:
            user_histories[user_id] = []

        # Добавляем сообщение юзера
        user_histories[user_id].append(
            g_types.Content(role="user", parts=[g_types.Part.from_text(text=user_input)])
        )

        # Ограничиваем память (последние 20 сообщений, чтобы не забить контекст)
        if len(user_histories[user_id]) > 20:
            user_histories[user_id] = user_histories[user_id][-20:]

        # Запрос к Gemini
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=user_histories[user_id],
            config=g_types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json" # ВАЖНО: Форсируем JSON
            )
        )
        
        # Парсим ответ
        result_json = json.loads(response.text)
        story_text = result_json.get("text", "Ошибка генерации текста.")
        img_prompt = result_json.get("image_prompt", "noir detective city")

        # Сохраняем ответ бота в историю
        user_histories[user_id].append(
            g_types.Content(role="model", parts=[g_types.Part.from_text(text=response.text)])
        )

        return story_text, img_prompt

    except Exception as e:
        logging.error(f"Gemini Error: {e}")
        return "🕵️‍♂️ *Архивы повреждены...* (Ошибка AI, попробуй еще раз).", None

def get_image_url(prompt):
    """Генерация ссылки на картинку через Pollinations (бесплатно, без ключей)"""
    # Очищаем промпт и кодируем для URL
    clean_prompt = prompt.replace(" ", "%20")
    # Добавляем seed, чтобы картинки были разными
    seed = random.randint(1, 10000)
    # Формируем URL. Pollinations генерирует на лету.
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}%20noir%20style%20monochrome?width=1024&height=1024&seed={seed}&nologo=true"
    return url

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_histories[message.from_user.id] = [] # Сброс истории
    await message.answer("🎷 *Игра началась...*")
    
    # Первый ход
    text, img_prompt = await generate_response(message.from_user.id, "Начни игру. Я детектив в своем кабинете.")
    
    if img_prompt:
        # Отправляем фото с подписью
        await message.answer_photo(
            photo=get_image_url(img_prompt),
            caption=text,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.answer(text)

@dp.message()
async def handle_all_messages(message: types.Message):
    # Показываем статус "печатает..."
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
    
    text, img_prompt = await generate_response(message.from_user.id, message.text)
    
    if img_prompt:
        try:
            await message.answer_photo(
                photo=get_image_url(img_prompt),
                caption=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            # Если картинка не загрузилась, шлем просто текст
            logging.error(f"Image Error: {e}")
            await message.answer(text)
    else:
        await message.answer(text)

# --- ЗАПУСК ---
async def main():
    global client
    # Инициализация клиента Gemini
    client = genai.Client(api_key=GEMINI_KEY)
    
    logging.info("✅ Бот Нуар-Детектив запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import logging
import os
import json
import random
from aiohttp import web # Добавили библиотеку для "обманки"
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from google import genai
from google.genai import types as g_types

# =============== НАСТРОЙКИ (ЧИТАЕМ 4 КЛЮЧА) ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
GEMINI_KEY_NOIR = os.getenv("GEMINI_KEY_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GEMINI_KEY_SOUL = os.getenv("GEMINI_KEY_SOUL")

# Если ключей нет, код не упадет сразу, но выведет ошибку в лог
if not all([TG_TOKEN_NOIR, GEMINI_KEY_NOIR, TG_TOKEN_SOUL, GEMINI_KEY_SOUL]):
    logging.error("❌ ВНИМАНИЕ! Не все ключи найдены. Проверь Environment Variables!")

MODEL_ID = "gemini-flash-latest"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# =============== ЛОГИКА 1: ДЕТЕКТИВ ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
client_noir = None
histories_noir = {}

SYSTEM_NOIR = """
Ты — ведущий квеста "Нуар-Детектив".
1. Описывай сцены мрачно.
2. К КАЖДОМУ ОТВЕТУ генерируй image_prompt на АНГЛИЙСКОМ.
3. ОТВЕЧАЙ ТОЛЬКО В JSON: { "text": "...", "image_prompt": "..." }
"""

async def generate_noir(user_id, text):
    try:
        if user_id not in histories_noir: histories_noir[user_id] = []
        histories_noir[user_id].append(g_types.Content(role="user", parts=[g_types.Part.from_text(text=text)]))
        if len(histories_noir[user_id]) > 20: histories_noir[user_id] = histories_noir[user_id][-20:]

        resp = client_noir.models.generate_content(
            model=MODEL_ID, contents=histories_noir[user_id],
            config=g_types.GenerateContentConfig(system_instruction=SYSTEM_NOIR, response_mime_type="application/json")
        )
        res_json = json.loads(resp.text)
        histories_noir[user_id].append(g_types.Content(role="model", parts=[g_types.Part.from_text(text=resp.text)]))
        return res_json.get("text"), res_json.get("image_prompt")
    except Exception as e:
        return f"🕵️‍♂️ *Сбой связи...* ({e})", None

def get_image_url(prompt):
    if not prompt: return None
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}%20noir%20style?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    text, prompt = await generate_noir(msg.from_user.id, "Начни игру. Я детектив.")
    if prompt: await msg.answer_photo(get_image_url(prompt), caption=text)
    else: await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    await bot_noir.send_chat_action(msg.chat.id, "upload_photo")
    text, prompt = await generate_noir(msg.from_user.id, msg.text)
    if prompt: await msg.answer_photo(get_image_url(prompt), caption=text)
    else: await msg.answer(text)

# =============== ЛОГИКА 2: ПСИХОЛОГ СОУЛ ===============
bot_soul = Bot(token=TG_TOKEN_SOUL, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_soul = Dispatcher()
client_soul = None
histories_soul = {}

SYSTEM_SOUL = """
Ты — друг Соул. Тон: теплый, поддерживающий.
Задавай вопросы. Отвечай обычным текстом.
"""

async def generate_soul(user_id, text):
    try:
        if user_id not in histories_soul: histories_soul[user_id] = []
        histories_soul[user_id].append(g_types.Content(role="user", parts=[g_types.Part.from_text(text=text)]))
        if len(histories_soul[user_id]) > 40: histories_soul[user_id] = histories_soul[user_id][-40:]

        resp = client_soul.models.generate_content(
            model=MODEL_ID, contents=histories_soul[user_id],
            config=g_types.GenerateContentConfig(system_instruction=SYSTEM_SOUL)
        )
        histories_soul[user_id].append(g_types.Content(role="model", parts=[g_types.Part.from_text(text=resp.text)]))
        return resp.text
    except Exception as e:
        return "Прости, я отвлекся... Повтори? (Ошибка сети)"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    await msg.answer("Привет! Я Соул. Как ты? ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== "ОБМАНКА" ДЛЯ RENDER ===============
async def health_check(request):
    return web.Response(text="Bot is alive!")

async def start_dummy_server():
    # Создаем мини-сайт, который просто говорит "Я жив"
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render сам выдает порт через переменную PORT, используем его
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"✅ Фейковый сервер запущен на порту {port}")

# =============== ГЛАВНЫЙ ЗАПУСК ===============
async def main():
    global client_noir, client_soul
    
    # Инициализируем Gemini клиентов
    if GEMINI_KEY_NOIR: client_noir = genai.Client(api_key=GEMINI_KEY_NOIR)
    if GEMINI_KEY_SOUL: client_soul = genai.Client(api_key=GEMINI_KEY_SOUL)

    # 1. Запускаем "обманку" (веб-сервер)
    await start_dummy_server()

    # 2. Запускаем обоих ботов
    logging.info("🚀 ЗАПУСК МУЛЬТИ-СИСТЕМЫ...")
    await asyncio.gather(
        dp_noir.start_polling(bot_noir),
        dp_soul.start_polling(bot_soul)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Боты остановлены")
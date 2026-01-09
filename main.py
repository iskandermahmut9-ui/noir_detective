import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from google import genai
from google.genai import types as g_types

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
GEMINI_KEY_NOIR = os.getenv("GEMINI_KEY_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GEMINI_KEY_SOUL = os.getenv("GEMINI_KEY_SOUL")

# Логирование всех ключей (безопасно, показывает только первые 4 символа)
def log_key_status(name, key):
    if key: logging.info(f"✅ {name} найден: {key[:4]}...")
    else: logging.error(f"❌ {name} НЕ НАЙДЕН!")

MODEL_ID = "gemini-flash-latest"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (LITE) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
client_noir = None
histories_noir = {}

SYSTEM_NOIR = """
Ты — ведущий квеста "Нуар-Детектив" (1940-е).
Веди игру, описывай сцены. Отвечай просто текстом.
"""

async def generate_noir(user_id, text):
    try:
        if not client_noir: return "🕵️‍♂️ Ошибка: Мозг детектива не подключен (нет ключа)."
        
        if user_id not in histories_noir: histories_noir[user_id] = []
        histories_noir[user_id].append(g_types.Content(role="user", parts=[g_types.Part.from_text(text=text)]))
        if len(histories_noir[user_id]) > 30: histories_noir[user_id] = histories_noir[user_id][-30:]

        resp = client_noir.models.generate_content(
            model=MODEL_ID, contents=histories_noir[user_id],
            config=g_types.GenerateContentConfig(system_instruction=SYSTEM_NOIR)
        )
        histories_noir[user_id].append(g_types.Content(role="model", parts=[g_types.Part.from_text(text=resp.text)]))
        return resp.text
    except Exception as e:
        logging.error(f"Error Noir: {e}") # ВАЖНО: Пишем ошибку в лог
        return f"🕵️‍♂️ Сбой архивов: {e}"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    text = await generate_noir(msg.from_user.id, "Начни игру.")
    await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    await bot_noir.send_chat_action(msg.chat.id, "typing")
    text = await generate_noir(msg.from_user.id, msg.text)
    await msg.answer(text)

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
        # ПРОВЕРКА: Если ключа нет, сразу говорим об этом
        if not client_soul:
            logging.error("❌ ПОПЫТКА ЗАПРОСА БЕЗ КЛИЕНТА (client_soul is None)")
            return "⚠️ Ошибка настройки: Мой ключ Gemini не найден в Render."

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
        # ВАЖНО: ТЕПЕРЬ МЫ УВИДИМ РЕАЛЬНУЮ ОШИБКУ В ЛОГАХ RENDER
        logging.error(f"🔥 ОШИБКА СОУЛА: {e}")
        return f"Прости, я отвлекся... (Тех. ошибка: {e})"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    await msg.answer("Привет! Я Соул. Как ты? ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ЗАПУСК ===============
async def health_check(request): return web.Response(text="Bots alive!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    global client_noir, client_soul
    
    logging.info("--- ПРОВЕРКА КЛЮЧЕЙ ---")
    log_key_status("TG_NOIR", TG_TOKEN_NOIR)
    log_key_status("GEMINI_NOIR", GEMINI_KEY_NOIR)
    log_key_status("TG_SOUL", TG_TOKEN_SOUL)
    log_key_status("GEMINI_SOUL", GEMINI_KEY_SOUL)

    if GEMINI_KEY_NOIR: client_noir = genai.Client(api_key=GEMINI_KEY_NOIR)
    if GEMINI_KEY_SOUL: client_soul = genai.Client(api_key=GEMINI_KEY_SOUL)

    await start_dummy_server()
    logging.info("🚀 ЗАПУСК МУЛЬТИ-СИСТЕМЫ...")
    
    await asyncio.gather(
        dp_noir.start_polling(bot_noir),
        dp_soul.start_polling(bot_soul)
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
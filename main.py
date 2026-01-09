import asyncio
import logging
import os
import random
import time
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

# === ИСПОЛЬЗУЕМ НОВУЮ БИБЛИОТЕКУ (для работы с двумя ключами) ===
from google import genai
from google.genai import types as g_types
from google.genai.errors import ClientError # Для отлова ошибок лимитов

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
GEMINI_KEY_NOIR = os.getenv("GEMINI_KEY_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GEMINI_KEY_SOUL = os.getenv("GEMINI_KEY_SOUL")

# ✅ ИСПРАВЛЕНИЕ 1: Используем стабильную модель 1.5 Flash
MODEL_ID = "gemini-1.5-flash"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Логирование ключей
def log_key_status(name, key):
    if key: logging.info(f"✅ {name} найден: {key[:4]}...")
    else: logging.error(f"❌ {name} НЕ НАЙДЕН!")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
client_noir = None
histories_noir = {}

SYSTEM_NOIR = """
Ты — ведущий квеста "Нуар-Детектив" (1940-е).
Веди игру, описывай сцены. Отвечай просто текстом.
"""

async def generate_noir(user_id, text):
    if not client_noir: return "🕵️‍♂️ Ошибка: Нет ключа API."
    
    # Инициализация истории
    if user_id not in histories_noir: histories_noir[user_id] = []
    histories_noir[user_id].append(g_types.Content(role="user", parts=[g_types.Part.from_text(text=text)]))
    # Чистим память (последние 20 сообщений)
    if len(histories_noir[user_id]) > 20: histories_noir[user_id] = histories_noir[user_id][-20:]

    # ✅ ИСПРАВЛЕНИЕ 2: Retry Logic (Повторные попытки при ошибке 429)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client_noir.models.generate_content(
                model=MODEL_ID,
                contents=histories_noir[user_id],
                config=g_types.GenerateContentConfig(system_instruction=SYSTEM_NOIR)
            )
            bot_response = resp.text
            histories_noir[user_id].append(g_types.Content(role="model", parts=[g_types.Part.from_text(text=bot_response)]))
            return bot_response

        except ClientError as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logging.warning(f"⚠️ Лимит запросов (429). Ждем 10 сек... Попытка {attempt+1}/{max_retries}")
                await asyncio.sleep(10) # Ждем и пробуем снова
                continue
            else:
                logging.error(f"Error Noir: {e}")
                return f"🕵️‍♂️ Сбой архивов: {e}"
        except Exception as e:
            logging.error(f"Unknown Error Noir: {e}")
            return f"Ошибка: {e}"
    
    return "🕵️‍♂️ Система перегружена. Попробуй через минуту."

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    text = await generate_noir(msg.from_user.id, "Начни игру. Введи меня в курс дела.")
    await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    await bot_noir.send_chat_action(msg.chat.id, "typing")
    text = await generate_noir(msg.from_user.id, msg.text)
    await msg.answer(text)

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) ===============
bot_soul = Bot(token=TG_TOKEN_SOUL, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_soul = Dispatcher()
client_soul = None
histories_soul = {}

SYSTEM_SOUL = """
Ты — друг Соул. Тон: теплый, поддерживающий, эмпатичный.
Задавай вопросы, чтобы человек раскрылся. Отвечай мягко.
"""

async def generate_soul(user_id, text):
    if not client_soul: return "⚠️ Ошибка: Нет ключа API."

    if user_id not in histories_soul: histories_soul[user_id] = []
    histories_soul[user_id].append(g_types.Content(role="user", parts=[g_types.Part.from_text(text=text)]))
    if len(histories_soul[user_id]) > 30: histories_soul[user_id] = histories_soul[user_id][-30:]

    # ✅ ИСПРАВЛЕНИЕ 2: Retry Logic для Соула
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client_soul.models.generate_content(
                model=MODEL_ID,
                contents=histories_soul[user_id],
                config=g_types.GenerateContentConfig(system_instruction=SYSTEM_SOUL)
            )
            bot_response = resp.text
            histories_soul[user_id].append(g_types.Content(role="model", parts=[g_types.Part.from_text(text=bot_response)]))
            return bot_response

        except ClientError as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logging.warning(f"⚠️ Soul Лимит (429). Ждем 10 сек... Попытка {attempt+1}")
                await asyncio.sleep(10)
                continue
            else:
                logging.error(f"🔥 Error Soul: {e}")
                return f"Прости, я отвлекся... (Ошибка API: {e})"
        except Exception as e:
            logging.error(f"Unknown Error Soul: {e}")
            return f"Ошибка: {e}"

    return "Прости, мысли путаются (слишком много запросов). Давай чуть позже? ☕️"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    await msg.answer("Привет! Я Соул. Как ты себя чувствуешь сегодня? ☕️")

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
    
    logging.info("--- ЗАПУСК 2.0 (Fixed) ---")
    log_key_status("TG_NOIR", TG_TOKEN_NOIR)
    log_key_status("GEMINI_NOIR", GEMINI_KEY_NOIR)
    log_key_status("TG_SOUL", TG_TOKEN_SOUL)
    log_key_status("GEMINI_SOUL", GEMINI_KEY_SOUL)

    # Инициализация клиентов (Новая библиотека)
    if GEMINI_KEY_NOIR: client_noir = genai.Client(api_key=GEMINI_KEY_NOIR)
    if GEMINI_KEY_SOUL: client_soul = genai.Client(api_key=GEMINI_KEY_SOUL)

    await start_dummy_server()
    logging.info("🚀 БОТЫ ЗАПУЩЕНЫ И ГОТОВЫ К РАБОТЕ")
    
    await asyncio.gather(
        dp_noir.start_polling(bot_noir),
        dp_soul.start_polling(bot_soul)
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
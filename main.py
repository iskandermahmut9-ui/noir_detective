import asyncio
import logging
import os
import random
import google.generativeai as genai 
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from google.api_core import exceptions as google_exceptions

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
GEMINI_KEY_NOIR = os.getenv("GEMINI_KEY_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GEMINI_KEY_SOUL = os.getenv("GEMINI_KEY_SOUL")

# 🚨 ВАЖНО: Мы переходим на самую базовую модель. Она есть у всех.
# Если заработает она - значит проблема была в доступах к Flash.
MODEL_NAME = "gemini-pro"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
genai_lock = asyncio.Lock()

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = "Роль: Нуар-детектив. Стиль: краткий, циничный, 1940-е."

async def generate_noir(user_id, text):
    if not GEMINI_KEY_NOIR: return "🕵️‍♂️ Нет ключа."
    
    if user_id not in histories_noir: 
        histories_noir[user_id] = [
            {"role": "user", "parts": ["Ты детектив?"]},
            {"role": "model", "parts": ["Да. И у меня похмелье."]}
        ]
    histories_noir[user_id].append({"role": "user", "parts": [text]})
    # Держим короткую память для стабильности
    if len(histories_noir[user_id]) > 10: histories_noir[user_id] = histories_noir[user_id][-10:]

    async with genai_lock:
        try:
            genai.configure(api_key=GEMINI_KEY_NOIR)
            model = genai.GenerativeModel(MODEL_NAME) # Без системной инструкции (для совместимости)
            
            # Добавляем промпт прямо в сообщение
            full_prompt = f"{SYSTEM_NOIR}\nUser: {text}"
            
            chat = model.start_chat(history=histories_noir[user_id][:-1])
            response = await chat.send_message_async(full_prompt)
            
            ans = response.text
            histories_noir[user_id].append({"role": "model", "parts": [ans]})
            return ans
        except Exception as e:
            logging.error(f"Error Noir: {e}")
            return f"🕵️‍♂️ Ошибка: {e}"

# ✅ ИСПРАВЛЕНА ССЫЛКА НА КАРТИНКУ (Pollinations New API)
def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто... (Версия Pro)*")
    text = await generate_noir(msg.from_user.id, "Кто ты?")
    await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    await bot_noir.send_chat_action(msg.chat.id, "typing")
    text = await generate_noir(msg.from_user.id, msg.text)
    await msg.answer(text)

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) ===============
bot_soul = Bot(token=TG_TOKEN_SOUL, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_soul = Dispatcher()
histories_soul = {}

SYSTEM_SOUL = "Роль: Друг-психолог. Стиль: теплый, добрый."

async def generate_soul(user_id, text):
    if not GEMINI_KEY_SOUL: return "⚠️ Нет ключа."
    if user_id not in histories_soul: histories_soul[user_id] = []
    histories_soul[user_id].append({"role": "user", "parts": [text]})
    if len(histories_soul[user_id]) > 10: histories_soul[user_id] = histories_soul[user_id][-10:]

    async with genai_lock:
        try:
            genai.configure(api_key=GEMINI_KEY_SOUL)
            model = genai.GenerativeModel(MODEL_NAME)
            
            full_prompt = f"{SYSTEM_SOUL}\nUser: {text}"
            
            chat = model.start_chat(history=histories_soul[user_id][:-1])
            response = await chat.send_message_async(full_prompt)
            ans = response.text
            histories_soul[user_id].append({"role": "model", "parts": [ans]})
            return ans
        except Exception as e:
            logging.error(f"Error Soul: {e}")
            return f"Ошибка: {e}"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    await msg.answer("Привет! Я Соул. (Версия Pro) ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ЗАПУСК ===============
async def health_check(request): return web.Response(text="Bots Alive")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК GEMINI PRO (SAFETY MODE) ---")
    await start_dummy_server()
    # Удаляем старые вебхуки, чтобы убрать конфликт
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)
    
    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
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

# Используем точное имя стабильной модели
MODEL_NAME = "gemini-1.5-flash"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# 🔒 ЗАМОК: Старая библиотека не умеет работать с двумя ключами одновременно
# Мы будем переключать ключи "по очереди" с помощью этого замка.
genai_lock = asyncio.Lock()

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = "Ты — ведущий квеста 'Нуар-Детектив' (1940-е). Веди игру, описывай мрачные сцены, дождь, улики. Отвечай кратко и стильно."

async def generate_noir(user_id, text):
    if not GEMINI_KEY_NOIR: return "🕵️‍♂️ Ошибка: Нет ключа API."
    
    # История сообщений в формате старой библиотеки
    if user_id not in histories_noir: 
        histories_noir[user_id] = [
            {"role": "user", "parts": ["Вводная: мы в детективном агентстве."]},
            {"role": "model", "parts": ["Понял. Дождь барабанит по стеклу..."]}
        ]
    
    histories_noir[user_id].append({"role": "user", "parts": [text]})
    if len(histories_noir[user_id]) > 20: 
        histories_noir[user_id] = histories_noir[user_id][-20:]

    # Входим в защищенный блок кода
    async with genai_lock:
        try:
            # 1. Настраиваем библиотеку на ключ Нуара
            genai.configure(api_key=GEMINI_KEY_NOIR)
            
            # 2. Создаем модель
            model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_NOIR)
            
            # 3. Запускаем чат с историей (кроме последнего сообщения, которое отправим сейчас)
            chat = model.start_chat(history=histories_noir[user_id][:-1])
            
            # 4. Генерируем ответ
            response = await chat.send_message_async(text)
            
            ans = response.text
            histories_noir[user_id].append({"role": "model", "parts": [ans]})
            return ans

        except google_exceptions.ResourceExhausted:
            return "🕵️‍♂️ (Кашель) Слишком много дел... Дай мне минуту перевести дух. (Лимит 429)"
        except Exception as e:
            logging.error(f"Error Noir: {e}")
            return f"🕵️‍♂️ Ошибка связи: {e}"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    text = await generate_noir(msg.from_user.id, "Начни игру. Кто я и где я?")
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

SYSTEM_SOUL = "Ты — друг Соул. Тон: теплый, поддерживающий, эмпатичный. Задавай вопросы, чтобы человек раскрылся."

async def generate_soul(user_id, text):
    if not GEMINI_KEY_SOUL: return "⚠️ Ошибка: Нет ключа API."

    if user_id not in histories_soul: histories_soul[user_id] = []
    histories_soul[user_id].append({"role": "user", "parts": [text]})
    if len(histories_soul[user_id]) > 30: histories_soul[user_id] = histories_soul[user_id][-30:]

    # Входим в защищенный блок кода
    async with genai_lock:
        try:
            # 1. Настраиваем библиотеку на ключ Соула
            genai.configure(api_key=GEMINI_KEY_SOUL)
            model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_SOUL)
            
            chat = model.start_chat(history=histories_soul[user_id][:-1])
            response = await chat.send_message_async(text)
            
            ans = response.text
            histories_soul[user_id].append({"role": "model", "parts": [ans]})
            return ans

        except google_exceptions.ResourceExhausted:
            return "Прости, я немного устал... Давай помолчим минутку? (Лимит API)"
        except Exception as e:
            logging.error(f"Error Soul: {e}")
            return f"Я тебя не слышу... (Ошибка: {e})"

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
async def health_check(request): return web.Response(text="Bots alive (Old Lib)!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК ПОСЛЕ РАБОТЫ НАД ОШИБКАМИ ---")
    await start_dummy_server()
    await asyncio.gather(
        dp_noir.start_polling(bot_noir),
        dp_soul.start_polling(bot_soul)
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
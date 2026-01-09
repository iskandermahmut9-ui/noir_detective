import asyncio
import logging
import os
import random
import time
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

# ВОЗВРАЩАЕМ ВЕРСИЮ С LATEST - она обычно работает стабильнее с API ключами
MODEL_NAME = "gemini-1.5-flash-latest"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
genai_lock = asyncio.Lock()

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = "Ты — ведущий квеста 'Нуар-Детектив'. Атмосфера 40-х. Дождь, джаз, опасность. Отвечай кратко."

async def generate_noir(user_id, text):
    if not GEMINI_KEY_NOIR: return "🕵️‍♂️ Нет ключа."
    
    if user_id not in histories_noir: 
        histories_noir[user_id] = [
            {"role": "user", "parts": ["Вводная: я детектив в своем офисе."]},
            {"role": "model", "parts": ["За окном дождь смывает грехи этого города..."]}
        ]
    histories_noir[user_id].append({"role": "user", "parts": [text]})
    if len(histories_noir[user_id]) > 15: histories_noir[user_id] = histories_noir[user_id][-15:]

    # === ЗАЩИТА ОТ 429 (Лимитов) ===
    # Мы пробуем 3 раза. Если ошибка лимита - ждем и пробуем снова.
    async with genai_lock:
        for attempt in range(3):
            try:
                genai.configure(api_key=GEMINI_KEY_NOIR)
                model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_NOIR)
                chat = model.start_chat(history=histories_noir[user_id][:-1])
                response = await chat.send_message_async(text)
                
                ans = response.text
                histories_noir[user_id].append({"role": "model", "parts": [ans]})
                return ans
            
            except google_exceptions.ResourceExhausted:
                logging.warning(f"⚠️ Noir поймал лимит (429). Ждем 30 сек... Попытка {attempt+1}")
                await asyncio.sleep(30) # ЖДЕМ ОСВОБОЖДЕНИЯ ЛИМИТА
                continue # Идем на следующий круг цикла
            
            except Exception as e:
                logging.error(f"Error Noir: {e}")
                return f"🕵️‍♂️ Сбой связи: {e}"
        
    return "🕵️‍♂️ Слишком много запросов. Попробуй через минуту."

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://pollinations.ai/p/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

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

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) ===============
bot_soul = Bot(token=TG_TOKEN_SOUL, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_soul = Dispatcher()
histories_soul = {}

SYSTEM_SOUL = "Ты — друг Соул. Поддерживай, сочувствуй, задавай мягкие вопросы."

async def generate_soul(user_id, text):
    if not GEMINI_KEY_SOUL: return "⚠️ Нет ключа."
    if user_id not in histories_soul: histories_soul[user_id] = []
    histories_soul[user_id].append({"role": "user", "parts": [text]})
    if len(histories_soul[user_id]) > 20: histories_soul[user_id] = histories_soul[user_id][-20:]

    # === ЗАЩИТА ОТ 429 (Лимитов) ===
    async with genai_lock:
        for attempt in range(3):
            try:
                genai.configure(api_key=GEMINI_KEY_SOUL)
                model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_SOUL)
                chat = model.start_chat(history=histories_soul[user_id][:-1])
                response = await chat.send_message_async(text)
                
                ans = response.text
                histories_soul[user_id].append({"role": "model", "parts": [ans]})
                return ans

            except google_exceptions.ResourceExhausted:
                logging.warning(f"⚠️ Soul поймал лимит (429). Ждем 30 сек... Попытка {attempt+1}")
                await asyncio.sleep(30)
                continue
            
            except Exception as e:
                logging.error(f"Error Soul: {e}")
                return f"Ошибка: {e}"

    return "Я пока не могу ответить (лимит запросов). Спроси чуть позже."

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
async def health_check(request): return web.Response(text="Bots Running")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ВОЗВРАТ К ИСТОКАМ + ЗАЩИТА ОТ ЛИМИТОВ ---")
    await start_dummy_server()
    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
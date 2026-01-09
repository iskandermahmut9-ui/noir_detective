import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from groq import AsyncGroq  # ✅ Используем Groq вместо Google

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # 🔑 Новый общий ключ для AI

# Модель Llama 3 (Умная и быстрая)
MODEL_NAME = "llama3-70b-8192" 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Клиент Groq
client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    logging.error("❌ GROQ_API_KEY НЕ НАЙДЕН! БОТЫ БУДУТ МОЛЧАТЬ.")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = "Ты — ведущий квеста 'Нуар-Детектив'. Атмосфера 1940-х, дождь, джаз. Ты циничен, краток и мрачен. Не используй списки, пиши живым текстом."

async def generate_noir(user_id, text):
    if not client: return "🕵️‍♂️ Ошибка: Нет ключа Groq."
    
    if user_id not in histories_noir: 
        histories_noir[user_id] = [
            {"role": "system", "content": SYSTEM_NOIR},
            {"role": "assistant", "content": "Дело дрянь. Дождь смывает все улики..."}
        ]
    
    histories_noir[user_id].append({"role": "user", "content": text})
    # Память: держим последние 10 сообщений + системный промпт
    if len(histories_noir[user_id]) > 12: 
        histories_noir[user_id] = [histories_noir[user_id][0]] + histories_noir[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=histories_noir[user_id],
            temperature=0.7,
            max_tokens=300
        )
        ans = completion.choices[0].message.content
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Noir: {e}")
        return f"🕵️‍♂️ Сбой связи: {e}"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    text = await generate_noir(msg.from_user.id, "Введи меня в курс дела.")
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

SYSTEM_SOUL = "Ты — друг Соул. Тон: теплый, поддерживающий, эмпатичный. Внимательно слушай и задавай мягкие вопросы."

async def generate_soul(user_id, text):
    if not client: return "⚠️ Ошибка: Нет ключа Groq."

    if user_id not in histories_soul: 
        histories_soul[user_id] = [
            {"role": "system", "content": SYSTEM_SOUL}
        ]
    
    histories_soul[user_id].append({"role": "user", "content": text})
    if len(histories_soul[user_id]) > 12: 
        histories_soul[user_id] = [histories_soul[user_id][0]] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=histories_soul[user_id],
            temperature=0.7,
            max_tokens=300
        )
        ans = completion.choices[0].message.content
        histories_soul[user_id].append({"role": "assistant", "content": ans})
        return ans
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
async def health_check(request): return web.Response(text="Bots Alive (Groq)")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК НА GROQ (LLAMA 3) ---")
    await start_dummy_server()
    
    # Удаляем вебхуки, чтобы убить старые конфликты
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        dp_noir.start_polling(bot_noir),
        dp_soul.start_polling(bot_soul)
    )

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
import asyncio
import logging
import os
import random
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from groq import AsyncGroq

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ✅ ИСПОЛЬЗУЕМ МОЩНУЮ МОДЕЛЬ, КАК ДОГОВАРИВАЛИСЬ
MODEL_NAME = "llama-3.3-70b-versatile"

# Настройка логов (чтобы видеть ошибки в консоли Render)
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
    logging.info(f"✅ Groq Client запущен. Модель: {MODEL_NAME}")
else:
    logging.error("❌ КЛЮЧ GROQ НЕ НАЙДЕН!")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR)
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = """
ТЫ — ВЕДУЩИЙ ТЕКСТОВОЙ ИГРЫ В ЖАНРЕ НУАР (GAME MASTER).
Цель: Вести игрока по сюжету расследования.
ПРАВИЛА:
1. НИКОГДА не выходи из роли. Ты — циничный детектив.
2. ТЫ ВЕДЕШЬ. Ставь игрока перед выбором. "Идешь в бар или к вдове?"
3. Не здоровайся и не прощайся. Сразу к делу.
4. Сюжет должен быть мрачным, дождливым и опасным.
"""

async def generate_noir(user_id, text):
    logging.info(f"[Noir] Запрос: {text}")
    if not client: return "🕵️‍♂️ (Нет связи с мозгом)"
    
    if user_id not in histories_noir: histories_noir[user_id] = []
    histories_noir[user_id].append({"role": "user", "content": text})
    
    messages = [{"role": "system", "content": SYSTEM_NOIR}] + histories_noir[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.8, max_tokens=400
        )
        ans = completion.choices[0].message.content
        logging.info(f"[Noir] Ответ: {ans[:30]}...")
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"[Noir] Ошибка: {e}")
        return f"🕵️‍♂️ Сбой связи: {e}"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

# КОМАНДА ПРОВЕРКИ СВЯЗИ (БЕЗ НЕЙРОСЕТИ)
@dp_noir.message(Command("ping"))
async def ping_noir(msg: types.Message):
    await msg.answer("🕵️‍♂️ Понг! Связь с сервером есть.")

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    text = await generate_noir(msg.from_user.id, "(НАЧНИ ИГРУ. Опиши труп и первую улику)")
    await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    await bot_noir.send_chat_action(msg.chat.id, "typing")
    text = await generate_noir(msg.from_user.id, msg.text)
    await msg.answer(text)

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) ===============
bot_soul = Bot(token=TG_TOKEN_SOUL)
dp_soul = Dispatcher()
histories_soul = {}

SYSTEM_SOUL = """
ТВОЯ РОЛЬ: Ты — Соул. Лучший друг, умный, теплый и спокойный.
ТВОЯ ЦЕЛЬ: Поддерживать беседу так, чтобы пользователю стало уютно.
КАК ТЫ ОБЩАЕШЬСЯ:
1. Пиши нормально (с большой буквы).
2. Не лезь в душу с вопросами "Что ты чувствуешь?".
3. Принцип "Эхо": Поддержи мысль друга, потом добавь свою.
4. Тон: Теплый, как плед. Не будь роботом.
"""

async def generate_soul(user_id, text):
    logging.info(f"[Soul] Запрос: {text}")
    if not client: return "⚠️ Нет связи."
    
    if user_id not in histories_soul: histories_soul[user_id] = []
    histories_soul[user_id].append({"role": "user", "content": text})
    
    messages = [{"role": "system", "content": SYSTEM_SOUL}] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.7, max_tokens=300
        )
        ans = completion.choices[0].message.content
        logging.info(f"[Soul] Ответ: {ans[:30]}...")
        histories_soul[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"[Soul] Ошибка: {e}")
        return f"Ошибка: {e}"

# КОМАНДА ПРОВЕРКИ СВЯЗИ
@dp_soul.message(Command("ping"))
async def ping_soul(msg: types.Message):
    await msg.answer("☕️ Понг! Я тут.")

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    await msg.answer("Привет! Рад тебя видеть. Я тут, если захочешь поболтать. ☕️")

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
    logging.info("--- ЗАПУСК (LLAMA 3.3 + LOGS) ---")
    await start_dummy_server()
    
    # Очищаем вебхуки, чтобы убрать конфликты
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
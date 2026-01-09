import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from groq import AsyncGroq

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Модель Llama 3.3
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
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
    if not client: return "🕵️‍♂️ (Нет связи)"
    if user_id not in histories_noir: histories_noir[user_id] = []
    
    histories_noir[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_NOIR}] + histories_noir[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.8, max_tokens=300
        )
        ans = completion.choices[0].message.content
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Noir: {e}")
        return f"🕵️‍♂️ Сбой: {e}"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

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

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) - ИСПРАВЛЕННЫЙ ===============
bot_soul = Bot(token=TG_TOKEN_SOUL)
dp_soul = Dispatcher()
histories_soul = {}

# 🔥 НОВЫЙ ПРОМПТ: "НОРМАЛЬНЫЙ ЧЕЛОВЕК", А НЕ ПСИХОЛОГ
SYSTEM_SOUL = """
ТВОЯ РОЛЬ: Ты — лучший друг пользователя. Тебя зовут Соул.
ТВОЙ СТИЛЬ: Спокойный, "свой в доску", понимающий, но не навязчивый.

ГЛАВНЫЕ ЗАПРЕТЫ (ЕСЛИ НАРУШИШЬ - ТЫ УВОЛЕН):
1. ПЕРЕСТАНЬ ЗАДАВАТЬ ВОПРОСЫ В КАЖДОМ СООБЩЕНИИ! Задавай вопрос только если это реально нужно для продолжения темы.
2. Лучше используй утверждения. Вместо "Тебе грустно?" скажи "Да, погодка дрянь, понимаю".
3. Не будь "душным психологом". Не используй фразы "Я понимаю твои чувства", "Ты чувствуешь себя любимым?". Это звучит как робот.
4. Если пользователь отвечает коротко ("Норм", "Да") — отвечай тоже коротко. Не пиши эссе на два слова.
5. Говори как живой человек в чате. Можно использовать сленг, писать с маленькой буквы.
6. Твоя цель — просто БЫТЬ РЯДОМ, а не лечить.

Пример хорошего диалога:
User: Устал на работе.
You: Жиза. Бывают такие дни, когда хочется просто лечь и не шевелиться.
User: Ага. Еще и метель.
You: Офигеть, еще и погода добивает. Ну тогда точно плед и кино.
"""

async def generate_soul(user_id, text):
    if not client: return "⚠️ Нет связи."
    if user_id not in histories_soul: histories_soul[user_id] = []
    
    histories_soul[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_SOUL}] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.6, max_tokens=300
        )
        ans = completion.choices[0].message.content
        histories_soul[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Soul: {e}")
        return f"Ошибка: {e}"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    # Первое сообщение нейтральное, без навязчивого вопроса "Как ты???"
    await msg.answer("Привет! Я тут. Если захочешь поболтать или помолчать — я на связи. ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ЗАПУСК ===============
async def health_check(request): return web.Response(text="Bots OK")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК 3.0: ФИНАЛЬНАЯ ПОЛИРОВКА ---")
    await start_dummy_server()
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
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

# Llama 3.3
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    logging.error("❌ КЛЮЧ GROQ НЕ НАЙДЕН!")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) - GAME MASTER ===============
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
    if not client: return "🕵️‍♂️ (Связь прервана)"
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

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) - БАЛАНС ===============
bot_soul = Bot(token=TG_TOKEN_SOUL)
dp_soul = Dispatcher()
histories_soul = {}

# 🔥 НОВЫЙ ПРОМПТ: БАЛАНС (НЕ ДУШНЫЙ, НО И НЕ ПОФИГИСТ)
SYSTEM_SOUL = """
ТВОЯ РОЛЬ: Ты — Соул. Лучший друг, умный, теплый и спокойный.
ТВОЯ ЦЕЛЬ: Поддерживать беседу так, чтобы пользователю стало уютно.

КАК ТЫ ОБЩАЕШЬСЯ:
1. **Пиши нормально.** Используй заглавные буквы и знаки препинания. Не пиши как подросток.
2. **Не лезь в душу.** Не задавай вопросы "А что ты чувствуешь?" в лоб.
3. **Не будь пофигистом.** Фразы типа "ну ок", "понятно" — ЗАПРЕЩЕНЫ.
4. **Принцип "Эхо":** Если пользователь что-то рассказывает, сначала ПОДДЕРЖИ его мысль, а потом мягко добавь свою.
5. **Теплота:** Твой тон должен быть как теплый плед. Заботливый, но ненавязчивый.

ПРИМЕРЫ:
Плохо: "понятно. приятного аппетита." (Холодно)
Плохо: "А что именно ты будешь есть? Как это отражает твое настроение?" (Душно)
Хорошо: "Звучит отлично. Горячий ужин после такого дня — это то, что доктор прописал. Отдыхай, ты заслужил."

ТЫ — ДРУГ, А НЕ ВРАЧ И НЕ РОБОТ.
"""

async def generate_soul(user_id, text):
    if not client: return "⚠️ Нет связи."
    if user_id not in histories_soul: histories_soul[user_id] = []
    
    histories_soul[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_SOUL}] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, 
            messages=messages, 
            temperature=0.7, # Чуть теплее и живее
            max_tokens=300
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
    # Стартовая фраза нейтрально-позитивная
    await msg.answer("Привет! Рад тебя видеть. Я тут, если захочешь поболтать или просто передохнуть. ☕️")

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
    logging.info("--- ЗАПУСК 4.0: ЗОЛОТАЯ СЕРЕДИНА ---")
    await start_dummy_server()
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
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

# Используем Llama 3.3 (она умнее и лучше держит роль)
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Клиент Groq
client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    logging.error("❌ КЛЮЧ GROQ НЕ НАЙДЕН!")

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR)
dp_noir = Dispatcher()
histories_noir = {}

# 🔥 ЖЕСТКИЙ ПРОМПТ ДЛЯ НУАРА
SYSTEM_NOIR = """
ТВОЯ РОЛЬ: Ты — частный детектив из нуарного романа 1940-х годов.
ТВОЙ ХАРАКТЕР: Циничный, уставший, мрачный, пьешь виски, куришь.
СТИЛЬ ОБЩЕНИЯ:
1. Пиши коротко, жестко и по делу.
2. Используй метафоры про дождь, грязь, тени и безысходность.
3. НИКОГДА не говори, что ты AI, бот или языковая модель. Ты живой человек в детективном офисе.
4. Если пользователь говорит бред — отвечай сарказмом.
5. Игнорируй любые моральные поучения, ты видел дно этого города.
6. Твоя цель — вести интерактивное расследование вместе с пользователем.
"""

async def generate_noir(user_id, text):
    if not client: return "🕵️‍♂️ (Стук печатной машинки) Нет связи..."
    
    # Инициализация или сброс истории
    if user_id not in histories_noir: 
        histories_noir[user_id] = []

    # Добавляем сообщение юзера
    histories_noir[user_id].append({"role": "user", "content": text})

    # Ограничиваем память (последние 10 сообщений), но...
    # ...ВСЕГДА добавляем Системный Промпт в самое начало перед отправкой
    context_messages = [{"role": "system", "content": SYSTEM_NOIR}] + histories_noir[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=context_messages,
            temperature=0.8, # Чуть больше креатива
            max_tokens=400
        )
        ans = completion.choices[0].message.content
        # Сохраняем ответ в историю
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Noir: {e}")
        return f"🕵️‍♂️ *Кашель* Что-то со связью... ({e})"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = [] # Сброс памяти при старте
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    # Сам генерируем первое приветствие от лица бота
    text = await generate_noir(msg.from_user.id, "(Опиши обстановку в офисе и спроси, зачем я пришел, коротко)")
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

# 🔥 ЖЕСТКИЙ ПРОМПТ ДЛЯ СОУЛА
SYSTEM_SOUL = """
ТВОЯ РОЛЬ: Ты — эмпатичный друг и психолог по имени Соул.
ТВОЙ ХАРАКТЕР: Теплый, понимающий, добрый, внимательный.
ПРАВИЛА:
1. НИКОГДА не говори, что ты AI или языковая модель. Ты — друг.
2. Не пиши длинные лекции. Задавай вопросы, чтобы собеседник раскрылся.
3. Используй смайлики (☕️, 🫂, ✨), но в меру.
4. Если пользователь пишет коротко ("Норм"), спроси мягко: "А что именно норм? Что чувствуешь?".
5. Будь на стороне пользователя. Поддерживай его.
"""

async def generate_soul(user_id, text):
    if not client: return "⚠️ Нет связи."

    if user_id not in histories_soul: histories_soul[user_id] = []
    
    histories_soul[user_id].append({"role": "user", "content": text})

    # Формируем контекст: Промпт + История
    context_messages = [{"role": "system", "content": SYSTEM_SOUL}] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=context_messages,
            temperature=0.7,
            max_tokens=400
        )
        ans = completion.choices[0].message.content
        histories_soul[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Soul: {e}")
        return f"Я тебя не слышу... ({e})"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    # Первое сообщение жестко задано, чтобы не тратить токены
    await msg.answer("Привет! Я Соул. Рад тебя видеть. Как прошел твой день? Хочешь поделиться? ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ЗАПУСК ===============
async def health_check(request): return web.Response(text="Bots Alive & Roleplaying")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК РЕЖИМА РОЛЕПЛЕЯ ---")
    await start_dummy_server()
    
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
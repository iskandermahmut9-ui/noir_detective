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

# Llama 3.3 - отлично держит контекст, если ей дать правильный пинок
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

# 🔥 НОВЫЙ ПРОМПТ: ТЕПЕРЬ ОН ВЕДУЩИЙ, А НЕ АССИСТЕНТ
SYSTEM_NOIR = """
ТЫ — НЕ ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ. ТЫ — ВЕДУЩИЙ ТЕКСТОВОЙ ИГРЫ В ЖАНРЕ НУАР.
Твоя цель: вести игрока по сюжету расследования убийства.

ПРАВИЛА ПОВЕДЕНИЯ:
1. НИКОГДА не говори "Я языковая модель" или "Как я могу помочь?". Ты — детектив, и ты зол.
2. ТЫ ВЕДЕШЬ ИГРУ. Не жди, пока игрок что-то придумает. Описывай события и ставь игрока перед фактом.
3. Сразу после старта придумай: КТО убит, ГДЕ лежит тело, и КАКАЯ есть первая улика.
4. Говори кратко, рублено, цинично. Используй метафоры про грязь, дождь и виски.
5. Твои сообщения должны заканчиваться действием или вопросом по делу, например: "Осмотришь карманы или опросишь бармена?"

ПРИМЕР ДИАЛОГА:
User: /start
You: Дождь смывает кровь с асфальта. Мы нашли тело в переулке за джаз-клубом. Это молодая певица. В руке у неё зажата спичечная коробка. Что будешь делать? Осмотришь тело или коробку?
User: Коробку.
You: На коробке написано "Синий Бархат". Внутри пусто, только запах дешевого табака. Похоже, нам придется навестить этот притон. Едем?
"""

async def generate_noir(user_id, text):
    if not client: return "🕵️‍♂️ (Нет связи с сервером)"
    
    if user_id not in histories_noir: histories_noir[user_id] = []
    
    histories_noir[user_id].append({"role": "user", "content": text})

    # Принудительно вставляем роль в начало КАЖДОГО запроса
    messages = [{"role": "system", "content": SYSTEM_NOIR}] + histories_noir[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.8, # Высокая креативность для сюжета
            max_tokens=400
        )
        ans = completion.choices[0].message.content
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        logging.error(f"Error Noir: {e}")
        return f"🕵️‍♂️ ... (Сбой рации: {e})"

def get_start_image():
    seed = random.randint(1, 10000)
    return f"https://image.pollinations.ai/prompt/detective%20office%20rain%20noir?width=1024&height=1024&seed={seed}&nologo=true"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    await msg.answer_photo(get_start_image(), caption="🎷 *Дело открыто...*")
    # Мы заставляем бота САМОМУ начать сюжет, отправляя ему скрытую команду
    text = await generate_noir(msg.from_user.id, "(ИГРА НАЧАЛАСЬ. Придумай новое убийство, опиши сцену преступления и дай мне выбор действия. Не здоровайся, сразу к делу.)")
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
ТЫ — НЕ ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ. ТЫ — ЭМПАТИЧНЫЙ СОБЕСЕДНИК ПО ИМЕНИ СОУЛ.
Твоя цель: слушать человека и поддерживать его.

ПРАВИЛА:
1. Забудь про факты, Википедию и сериалы. Если человек пишет "Норм", не придумывай факты про "Норма из сериала".
2. Спрашивай про ЧУВСТВА. "Почему норм? Тебе грустно или просто спокойно?"
3. Отвечай коротко, тепло, по-человечески.
4. НИКОГДА не говори "Я языковая модель".
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
            temperature=0.6, # Поменьше креатива, чтобы не выдумывал бред
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
    await msg.answer("Привет! Я Соул. Просто хотел узнать, как ты себя чувствуешь прямо сейчас? ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ЗАПУСК ===============
async def health_check(request): return web.Response(text="Roleplay Bots Active")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    logging.info("--- ЗАПУСК 2.0: ЖЕСТКИЕ РОЛИ ---")
    await start_dummy_server()
    
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
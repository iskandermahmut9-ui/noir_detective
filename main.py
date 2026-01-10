import asyncio
import logging
import os
import random
import sys
from datetime import datetime
import pytz # Библиотека часовых поясов
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from groq import AsyncGroq

# =============== НАСТРОЙКИ ===============
TG_TOKEN_NOIR = os.getenv("TG_TOKEN_NOIR")
TG_TOKEN_SOUL = os.getenv("TG_TOKEN_SOUL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") # Для само-пинга

# Модель Llama 3.3
MODEL_NAME = "llama-3.3-70b-versatile"

# Настройка времени (Москва)
TZ_MOSCOW = pytz.timezone('Europe/Moscow')

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=[logging.StreamHandler(sys.stdout)])

client = None
if GROQ_API_KEY:
    client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    logging.error("❌ КЛЮЧ GROQ НЕ НАЙДЕН!")

# Переменная, чтобы помнить, поздравили ли мы уже сегодня
last_auto_message_date = None

# =============== ЛОГИКА 1: ДЕТЕКТИВ (NOIR) ===============
bot_noir = Bot(token=TG_TOKEN_NOIR)
dp_noir = Dispatcher()
histories_noir = {}

SYSTEM_NOIR = """
ТЫ — ВЕДУЩИЙ НУАРНОГО ДЕТЕКТИВА.
1. НИКОГДА не выходи из роли.
2. ТЫ ВЕДЕШЬ. Ставь игрока перед выбором.
3. Не здоровайся. Сразу к делу.
"""

async def generate_noir(user_id, text):
    if not client: return "🕵️‍♂️ (Нет связи)"
    if user_id not in histories_noir: histories_noir[user_id] = []
    histories_noir[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": SYSTEM_NOIR}] + histories_noir[user_id][-10:]
    try:
        completion = await client.chat.completions.create(model=MODEL_NAME, messages=messages, temperature=0.8, max_tokens=400)
        ans = completion.choices[0].message.content
        histories_noir[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        return f"Сбой: {e}"

@dp_noir.message(CommandStart())
async def start_noir(msg: types.Message):
    histories_noir[msg.from_user.id] = []
    text = await generate_noir(msg.from_user.id, "(НАЧНИ ИГРУ. Опиши труп и улику)")
    await msg.answer(text)

@dp_noir.message()
async def msg_noir(msg: types.Message):
    text = await generate_noir(msg.from_user.id, msg.text)
    await msg.answer(text)

# =============== ЛОГИКА 2: ПСИХОЛОГ (SOUL) - УЛУЧШЕННЫЙ ===============
bot_soul = Bot(token=TG_TOKEN_SOUL)
dp_soul = Dispatcher()
histories_soul = {}

# 🔥 ПРОМПТ: БЕЗ АНГЛИЙСКОГО, КРАТКО, ПО-РУССКИ
SYSTEM_SOUL = """
ТВОЯ РОЛЬ: Ты — Соул. Хороший друг.
ТВОЯ ЦЕЛЬ: Быть рядом, но не надоедать.

СТРОГИЕ ПРАВИЛА:
1. **ЯЗЫК:** ТОЛЬКО РУССКИЙ. Никаких английских слов (feeling, fascinates и т.д.). Даже не думай.
2. **ОБЪЕМ:** Максимум 2-3 предложения. Не пиши поэмы. Если пользователь написал мало — ты пиши мало.
3. **ТОН:** Спокойный, взрослый. Пиши с большой буквы.
4. **НЕ ЛЕЗЬ В ДУШУ:** Не спрашивай "Что ты чувствуешь?" постоянно. Просто поддерживай разговор.
5. **ПРИМЕР:** - User: "Устал."
   - You: "Понимаю. День был долгий. Может, просто отдохнешь вечером?" (ЭТО ХОРОШО).
   - You: "О, я чувствую твою усталость feeling, это так fasciniruyet..." (ЭТО ПЛОХО, ЗАПРЕЩЕНО).
"""

async def generate_soul(user_id, text, system_prompt=SYSTEM_SOUL):
    if not client: return "⚠️ Нет связи."
    if user_id not in histories_soul: histories_soul[user_id] = []
    
    histories_soul[user_id].append({"role": "user", "content": text})
    messages = [{"role": "system", "content": system_prompt}] + histories_soul[user_id][-10:]

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.6, max_tokens=200 
        )
        ans = completion.choices[0].message.content
        histories_soul[user_id].append({"role": "assistant", "content": ans})
        return ans
    except Exception as e:
        return f"Ошибка: {e}"

@dp_soul.message(CommandStart())
async def start_soul(msg: types.Message):
    histories_soul[msg.from_user.id] = []
    # Сохраняем ID пользователя, чтобы писать ему первым (если сервер не перезагрузится)
    await msg.answer("Привет! Я Соул. Рад тебя видеть. ☕️")

@dp_soul.message()
async def msg_soul(msg: types.Message):
    # Если бот перезагружался, он мог забыть ID. Сохраним его снова при любом сообщении.
    if msg.from_user.id not in histories_soul:
        histories_soul[msg.from_user.id] = []
        
    await bot_soul.send_chat_action(msg.chat.id, "typing")
    ans = await generate_soul(msg.from_user.id, msg.text)
    await msg.answer(ans)

# =============== ФОНОВАЯ ЗАДАЧА: ИНИЦИАТИВА БОТА ===============
async def scheduler_task():
    global last_auto_message_date
    logging.info("📅 Планировщик запущен (Москва 11:00-19:00)")
    
    while True:
        try:
            # Получаем время по Москве
            now = datetime.now(TZ_MOSCOW)
            current_hour = now.hour
            today_str = now.strftime("%Y-%m-%d")

            # Проверяем условия:
            # 1. Время рабочее (с 11 до 19)
            # 2. Мы еще НЕ писали сегодня (last_auto_message != today)
            # 3. У нас есть кому писать (histories_soul не пуст)
            
            is_working_hours = 11 <= current_hour < 19
            is_new_day = last_auto_message_date != today_str
            
            if is_working_hours and is_new_day and histories_soul:
                logging.info(f"🔔 Время писать первым! (Время: {now})")
                
                # Берем всех известных пользователей (обычно это ты один)
                for user_id in list(histories_soul.keys()):
                    try:
                        # Генерируем ненавязчивое приветствие
                        prompt_init = "Ты пишешь первым, чтобы узнать как дела. Не будь навязчивым. Просто спроси 'Как проходит день?' или пожелай хорошего настроения. Кратко."
                        
                        # Тут мы немного читерим: отправляем пустой текст в историю, чтобы сработал генератор
                        # Но нам нужно сгенерировать сообщение БЕЗ входящего текста юзера.
                        messages = [{"role": "system", "content": SYSTEM_SOUL}, {"role": "user", "content": prompt_init}]
                        
                        completion = await client.chat.completions.create(
                            model=MODEL_NAME, messages=messages, temperature=0.7, max_tokens=100
                        )
                        greeting = completion.choices[0].message.content
                        
                        await bot_soul.send_message(user_id, greeting)
                        logging.info(f"✅ Отправлено проактивное сообщение юзеру {user_id}")
                    except Exception as e:
                        logging.error(f"Не удалось отправить сообщение: {e}")

                # Запоминаем, что сегодня мы уже отработали
                last_auto_message_date = today_str
            
            # Если сервер на Render, используем само-пинг, чтобы не спать
            if RENDER_EXTERNAL_URL:
                 import aiohttp
                 async with aiohttp.ClientSession() as session:
                    async with session.get(RENDER_EXTERNAL_URL) as resp:
                        pass # Просто дергаем сервер

        except Exception as e:
            logging.error(f"Scheduler Error: {e}")

        # Проверяем раз в 5 минут
        await asyncio.sleep(300)

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
    logging.info("--- ЗАПУСК (SOUL 2.0: NO ENGLISH + SCHEDULER) ---")
    await start_dummy_server()
    
    # Запускаем планировщик в фоне
    asyncio.create_task(scheduler_task())
    
    await bot_noir.delete_webhook(drop_pending_updates=True)
    await bot_soul.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(dp_noir.start_polling(bot_noir), dp_soul.start_polling(bot_soul))

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass
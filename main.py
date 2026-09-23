import os
import logging
import asyncio
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# --- КОНФИГУРАЦИЯ ---
# ВСТАВЬ СЮДА СВОЙ ТОКЕН И ID
BOT_TOKEN = "8933139840:AAFlZHUXZdTV_2igoAIkPs0uER4CEu8694o" 
ADMIN_ID = 855067842  # Твой ID

load_dotenv()

# Если запускаешь локально, можно переопределить через переменные окружения, 
# но для Render проще оставить так и менять прямо в файле перед деплоем, 
# либо использовать .env (если Render настроен на чтение .env).
# Для простоты в этом примере мы используем жестко заданные значения выше.

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- МАШИНА СОСТОЯНИЙ (FSM) ---
class DatePlaceState(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_date_time = State()
    waiting_for_place = State()

# --- КЛАВИАТУРЫ ---
def get_agreement_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Я согласна", callback_data="agree_yes")
    builder.button(text="Я точно согласна", callback_data="agree_strong")
    builder.adjust(1)
    return builder.as_markup()

# --- HTML ШАБЛОНЫ (ВСТРОЕННЫЕ) ---
# Чтобы не создавать лишние файлы, мы храним HTML прямо в коде.
# Это идеально для Варианта А.

HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Приглашение</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #ffebee; color: #c62828; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; text-align: center; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
        h1 { color: #d32f2f; margin-top: 0; }
        button { background: #d32f2f; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 12px; width: 100%; }
        button:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="card">
        <h1>💌 Приглашение на свидание</h1>
        <p>Ты — самое дорогое, что у меня есть. Хочу провести с тобой незабываемый вечер.</p>
        <button id="agreeBtn">Я согласна</button>
        <button id="strongAgreeBtn">Я точно согласна</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        function sendData(data) { tg.sendData(data); }
        document.getElementById('agreeBtn').onclick = () => sendData('agree_yes');
        document.getElementById('strongAgreeBtn').onclick = () => sendData('agree_strong');
    </script>
</body>
</html>
"""

HTML_DATE_TIME = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Дата и время</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #e3f2fd; color: #1565c0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; text-align: center; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
        h2 { color: #1565c0; margin-top: 0; }
        input, label { width: 100%; margin: 8px 0; display: block; }
        button { background: #1565c0; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 12px; width: 100%; }
        button:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="card">
        <h2>📅 Выбери дату и время</h2>
        <label for="date">Дата:</label>
        <input type="date" id="date">
        <label for="time">Время:</label>
        <input type="time" id="time">
        <button id="submitBtn">Подтвердить</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        const dateInput = document.getElementById('date');
        const timeInput = document.getElementById('time');
        const submitBtn = document.getElementById('submitBtn');
        
        // Минимальная дата - сегодня
        const today = new Date().toISOString().split('T');
        dateInput.min = today;

        submitBtn.onclick = () => {
            const date = dateInput.value;
            const time = timeInput.value;
            if (!date || !time) {
                tg.showAlert('Пожалуйста, выбери дату и время!');
                return;
            }
            // Формат: dt:YYYY-MM-DD|HH:MM
            const payload = `dt:${date}|${time}`;
            tg.sendData(payload);
        };
    </script>
</body>
</html>
"""

HTML_PLACE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Место встречи</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #e8f5e9; color: #2e7d32; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; text-align: center; }
        .card { background: white; padding: 24px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
        h2 { color: #2e7d32; margin-top: 0; }
        select, label { width: 100%; margin: 8px 0; display: block; }
        button { background: #2e7d32; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 12px; width: 100%; }
        button:active { transform: scale(0.98); }
    </style>
</head>
<body>
    <div class="card">
        <h2>📍 Где встретимся?</h2>
        <label for="place">Выбери место:</label>
        <select id="place">
            <option value="cafe">Уютное кафе</option>
            <option value="park">Городской парк</option>
            <option value="cinema">Кинотеатр</option>
            <option value="restaurant">Романтический ресторан</option>
            <option value="other">Другое (напишу в чате)</option>
        </select>
        <button id="submitBtn">Подтвердить</button>
    </div>
    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        const placeSelect = document.getElementById('place');
        const submitBtn = document.getElementById('submitBtn');

        submitBtn.onclick = () => {
            const place = placeSelect.value;
            const payload = `place:\${place}`;
            tg.sendData(payload);
        };
    </script>
</body>
</html>
"""

# --- ОБРАБОТЧИКИ БОТА (AIORGRAM) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(DatePlaceState.waiting_for_agreement)
    text = (
        "💌 Ты получила особое приглашение на свидание!\n\n"
        "Как ты на это смотришь?"
    )
    await message.answer(text, reply_markup=get_agreement_keyboard())

@dp.callback_query(F.data.in_(["agree_yes", "agree_strong"]), DatePlaceState.waiting_for_agreement)
async def process_agreement(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DatePlaceState.waiting_for_date_time)
    # Сохраняем тип согласия, если нужно
    await state.update_data(agreement_type=callback.data)
    
    text = "Отлично! Теперь выбери дату и время свидания."
    # Ссылка на наш встроенный веб-сервер (на Render это будет домен сервиса)
    # Мы используем относительный путь, так как aiohttp будет отдавать файлы по этим путям
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📆 Выбрать дату и время", web_app={"url": "/date"})]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("dt:"), DatePlaceState.waiting_for_date_time)
async def process_date_time(callback: types.CallbackQuery, state: FSMContext):
    # Парсим данные: dt:YYYY-MM-DD|HH:MM
    _, data = callback.data.split(":", 1)
    date_str, time_str = data.split("|")
    
    await state.update_data(date=date_str, time=time_str)
    await state.set_state(DatePlaceState.waiting_for_place)
    
    text = "Теперь выбери место, где мы встретимся."
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📍 Выбрать место", web_app={"url": "/place"})]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("place:"), DatePlaceState.waiting_for_place)
async def process_place(callback: types.CallbackQuery, state: FSMContext):
    _, place_val = callback.data.split(":", 1)
    
    # Получаем все сохраненные данные
    data = await state.get_data()
    date = data.get("date")
    time = data.get("time")
    agreement = data.get("agreement_type")
    
    # Формируем финальное сообщение
    final_text = (
        "🎉 До встречи! 🎉\n\n"
        f"Ты выбрала: <b>{date} в {time}</b> в месте: <b>{place_val}</b>.\n"
        "Люблю тебя <3"
    )
    
    await callback.message.edit_text(final_text, parse_mode="HTML")
    await state.clear()
    await callback.answer()

# --- ВЕБ-СЕРВЕР (AIOHTTP) ---
# Этот блок отвечает за отдачу HTML страниц для Mini App

async def handle_index(request):
    return web.Response(text=HTML_INDEX, content_type='text/html')

async def handle_date(request):
    return web.Response(text=HTML_DATE_TIME, content_type='text/html')

async def handle_place(request):
    return web.Response(text=HTML_PLACE, content_type='text/html')

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/date', handle_date)
    app.router.add_get('/place', handle_place)
    
    # Render требует, чтобы сервер слушал порт из переменной PORT
    port = int(os.environ.get('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- ЗАПУСК ---
async def main():
    # Запускаем веб-сервер в фоне
    web_task = asyncio.create_task(start_web_server())
    
    # Запускаем бота
    await dp.start_polling(bot)
    
    # Если бот упал, останавливаем сервер
    web_task.cancel()
    try:
        await web_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main())

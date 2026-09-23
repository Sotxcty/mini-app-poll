import os
import json
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Хранилище ответов (в памяти, для простоты) ---
user_answers = {}

# --- Хендлеры бота ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💌 Открыть приглашение",
        web_app={"url": "/app"}
    )
    await message.answer(
        "Нажми кнопку ниже, чтобы открыть приглашение 👇",
        reply_markup=builder.as_markup()
    )

# --- aiohttp: раздача HTML и приём ответов ---

async def handle_app(request):
    return web.FileResponse("index.html")

async def handle_submit(request):
    data = await request.json()
    user_id = data.get("user_id")
    step = data.get("step")
    choice = data.get("choice")

    print(f"Получены данные: user={user_id}, step={step}, choice={choice}")

    # Сохраняем ответ
    if user_id:
        uid = int(user_id)
        if uid not in user_answers:
            user_answers[uid] = {}
        user_answers[uid][step] = choice

        # Отправляем сообщение в чат от имени бота
        if step == "invitation":
            if choice == "agree":
                text = "Спасибо, что согласилась! 🎉 Теперь выбери, куда пойдём."
            elif choice == "strong_agree":
                text = "Ты сделала мой день! 😍 Теперь выбери, куда пойдём."
            else:
                text = "Спасибо за ответ! 💛"
            await bot.send_message(uid, text)

        elif step == "place":
            place_names = {
                "restaurant": "Ресторан 🍽️",
                "cinema": "Кино 🎬",
                "walk": "Прогулка 🌅"
            }
            place = place_names.get(choice, choice)
            text = f"Отлично! Ты выбрала: {place}. Всё запланирую, не переживай! 😘"
            await bot.send_message(uid, text)

    return web.json_response({"ok": True})

# --- Запуск ---

async def main():
    app = web.Application()
    app.router.add_get("/app", handle_app)
    app.router.add_post("/submit", handle_submit)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)

    # Запускаем aiohttp и aiogram polling одновременно
    await site.start()
    print(f"Сервер запущен на порту {port}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

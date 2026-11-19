import asyncio
import sqlite3
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from main import parse_eis_tenders
from database import add_tender

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_b2b_keyboard():          #keyboard buttons name
    kb = [
        [KeyboardButton(text="Мониторинг ЕИС"),KeyboardButton(text="Тех.поддержка")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_total_tenders_count():
    try:
        conn = sqlite3.connect("tenders.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tracked_tenders")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception:
        return 0


def get_tenders_page(page: int, limit: int = 10):
    conn = sqlite3.connect("tenders.db")
    cursor = conn.cursor()
    offset = (page - 1) * limit
    cursor.execute("SELECT id, customer, price FROM tracked_tenders LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_pagination_keyboard(page: int, total_pages: int):
    row_buttons = []
    if page > 1:
        row_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"page_{page-1}"))

    row_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

    if page < total_pages:
        row_buttons.append(InlineKeyboardButton(text="Вперед", callback_data=f"page_{page+1}"))

    return InlineKeyboardMarkup(inline_keyboard=[row_buttons])


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    user_name = message.from_user.full_name
    total_count = get_total_tenders_count()
    welcome_text = (
        f"**Аналитический модуль v1.0** приветствует вас, **{user_name}**.\n\n"
        f"Текущий статус системы:\n"
        f"Всего лотов под защитой хранилища: {total_count}\n"
        f"Используйте нижнее меню для управления бэкендом."
    )
    await message.answer(welcome_text, reply_markup=get_b2b_keyboard(), parse_mode="Markdown")


@dp.message(lambda message: message.text == "Мониторинг ЕИС")
async def handle_monitoring(message: Message):
    status_msg = await message.answer("Запуск ETL-контура...\nПодключаюсь к результатам ЕИС, пожалуйста подождите...")

    try:
        data = await parse_eis_tenders()

        if not data:
            await status_msg.delete()
            error_help = (
                "Внешний сбой канала связи с ЕИС Госзакупок.\n\n"
                "Сервер государственного сайта не ответил на наш запрос. "
                "Не переживайте, это стандартное поведение системы защиты сайта или сетевого туннеля.\n\n"
                "Что делать прямо сейчас:\n"
                "1. Если вы запускаете бота локально: переподключитесь к vpn.\n"
                "2. Нажмите кнопку 'Мониторинг ЕИС' повторно.\n"
                "3. Если ошибка повторяется многократно — возможно, на серверах ЕИС Госзакупок идут плановые технические работы. Попробуйте обновить пул лотов чуть позже."
            )
            await message.answer(error_help, parse_mode="Markdown")
            return

        for item in data:
            add_tender(item["id"], item["customer"], item["price"])

        await status_msg.delete()
        await send_tenders_page_message(chat_id=message.chat.id, page=1)

    except Exception as e:
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.answer(f"Произошла тех.ошибка: {str(e)}")


async def send_tenders_page_message(chat_id: int, page: int, edit_message_id: int = None):
    limit = 10
    total_tenders = get_total_tenders_count()
    total_pages = max((total_tenders + limit - 1) // limit, 1)
    page_data = get_tenders_page(page, limit)

    if not page_data:
        await bot.send_message(chat_id, "В базе данных пока нет лотов для отображения.")
        return

    report_text = f"**МОНИТОРИНГ ЕИС - СТРАНИЦА {page}**\n{'-'*30}\n"

    for row in page_data:
        t_id, customer, price = row
        formatted_price = price

        try:
            clean_num = price.replace("Р", "").replace("P", "").replace("₽", "").replace(" ", "").strip()
            price_float = float(clean_num)
            formatted_price = f"{price_float:,.2f}".replace(",", " ") + "₽"
        except Exception:
            if "₽" not in formatted_price:
                formatted_price = f"{formatted_price.strip()}₽"

        report_text += (
            f"**Лот:** `{t_id}`\n"
            f"**Заказчик:** {customer[:50]}...\n"
            f"**Сумма тендера:** `{formatted_price}`\n"
            f"{'-'*30}\n"
        )

    kb = get_pagination_keyboard(page, total_pages)

    if edit_message_id:
        await bot.edit_message_text(report_text, chat_id=chat_id, message_id=edit_message_id, reply_markup=kb, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, report_text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("page_"))
async def handle_pagination_callback(callback: CallbackQuery):
    target_page = int(callback.data.split("_")[1])
    await send_tenders_page_message(
        chat_id=callback.message.chat.id,
        page=target_page,
        edit_message_id=callback.message.message_id
    )
    await callback.answer()


@dp.message(lambda message: message.text == "Тех.поддержка")
async def handle_support(message: Message):
    support_text = (
        "**ЦЕНТР ПОДДЕРЖКИ И БАЗА ЗНАНИЙ СИСТЕМЫ**\n\n"
        "Этот раздел нацелен на решение часто возникающих проблем\n\n"
        "**Вопрос: Что значат значки в отчете мониторинга?**\n"
        "• `NEW` — закупка впервые обнаружена системой, занесена в базу данных.\n"
        "• `old` — лот уже скачивался ранее.\n\n"
        "**Вопрос: Почему вместо лотов я вижу сообщение о сбое сети?**\n"
        "• Государственный портал ЕИС Госзакупок часто перегружен или включает алгоритмы защиты. Самое эффективное решение — перезагрузить системный VPN на вашем сервере/устройстве, сменив страну IP-адреса, и повторить запрос через 15 секунд.\n\n"
    )
    await message.answer(support_text, parse_mode="Markdown")

async def main():
    print("Асинхронный B2B tg-bot успешно запущен в терминале")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

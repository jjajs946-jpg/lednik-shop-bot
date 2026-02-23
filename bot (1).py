import logging
import asyncio
import hashlib
import hmac
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, PreCheckoutQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, LabeledPrice
)
from aiogram.filters import CommandStart

# ========================================
# 🔧 НАСТРОЙКИ
# ========================================
BOT_TOKEN = "8582897108:AAGm1JIPzUW1I_AN_J_BE4-h2Oc_wm0qWiU"
ADMIN_ID   = 123456789   # ← ЗАМЕНИ НА СВОЙ TELEGRAM ID (узнай у @userinfobot)
WEBAPP_URL = "https://storied-tiramisu-b7f2b2.netlify.app"
PORT       = 8080
# ========================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

ALL_ITEMS = {
    "p90":      {"name": "П90",              "stars": 10,  "emoji": "🔫"},
    "zs9":      {"name": "ЖС9",              "stars": 10,  "emoji": "🎯"},
    "avm":      {"name": "АВМ",              "stars": 15,  "emoji": "⚡"},
    "amr":      {"name": "АМР",              "stars": 15,  "emoji": "💥"},
    "mk":       {"name": "МК Вышка",         "stars": 15,  "emoji": "🗼"},
    "gold_gun": {"name": "Золотые оружия",   "stars": 30,  "emoji": "🏆"},
    "full6":    {"name": "Фулл6",            "stars": 30,  "emoji": "👥"},
    "full_gold":{"name": "Фулл Золото",      "stars": 50,  "emoji": "👑"},
    "esc_2m":   {"name": "Сопровождение 2М", "stars": 50,  "emoji": "🛡️"},
    "esc_4m":   {"name": "Сопровождение 4М", "stars": 100, "emoji": "🛡️"},
    "esc_6m":   {"name": "Сопровождение 6М", "stars": 180, "emoji": "🛡️"},
    "esc_8m":   {"name": "Сопровождение 8М", "stars": 250, "emoji": "🛡️"},
    "esc_10m":  {"name": "Сопровождение 10М","stars": 300, "emoji": "💎"},
}


# ─── Проверка подписи Telegram WebApp ───────────────────────────────────────
def verify_init_data(init_data: str) -> bool:
    try:
        parsed = dict(x.split('=', 1) for x in init_data.split('&'))
        received_hash = parsed.pop('hash', '')
        data_check = '\n'.join(f'{k}={v}' for k, v in sorted(parsed.items()))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received_hash)
    except Exception:
        return False


# ─── HTTP сервер: создание инвойса ──────────────────────────────────────────
async def create_invoice_handler(request: web.Request) -> web.Response:
    # CORS
    if request.method == 'OPTIONS':
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })

    try:
        body = await request.json()
    except Exception:
        return web.json_response({'error': 'bad json'}, status=400,
                                 headers={'Access-Control-Allow-Origin': '*'})

    user_id   = body.get('user_id')
    item_id   = body.get('item_id')
    init_data = body.get('init_data', '')

    # Проверяем подпись (защита от подделки)
    if not verify_init_data(init_data):
        log.warning(f"Invalid init_data from user {user_id}")
        return web.json_response({'error': 'invalid signature'}, status=403,
                                 headers={'Access-Control-Allow-Origin': '*'})

    item = ALL_ITEMS.get(item_id)
    if not item:
        return web.json_response({'error': 'item not found'}, status=404,
                                 headers={'Access-Control-Allow-Origin': '*'})

    try:
        # Создаём инвойс через Telegram API
        invoice_link = await bot.create_invoice_link(
            title=f"{item['emoji']} {item['name']}",
            description=f"LEDNIK SHOP: {item['name']}",
            payload=f"{item_id}:{user_id}",
            currency="XTR",
            prices=[LabeledPrice(label=item['name'], amount=item['stars'])],
        )
        log.info(f"Invoice created for user {user_id}: {item['name']}")
        return web.json_response({'invoice_link': invoice_link},
                                 headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        log.error(f"Invoice creation error: {e}")
        return web.json_response({'error': str(e)}, status=500,
                                 headers={'Access-Control-Allow-Origin': '*'})


# ─── Telegram handlers ──────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🛒 Открыть магазин",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await message.answer(
        "💀 *LEDNIK SHOP — PUBG Black Market*\n\n"
        "Жми кнопку ниже — откроется магазин прямо здесь!\n"
        "Оплата звёздами внутри Telegram 🌟",
        parse_mode="Markdown",
        reply_markup=kb
    )


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    payload_parts = payment.invoice_payload.split(':')
    item_id = payload_parts[0]
    item = ALL_ITEMS.get(item_id, {"name": item_id, "emoji": "✅"})
    stars = payment.total_amount
    user  = message.from_user

    await message.answer(
        f"✅ *Оплата прошла!*\n\n"
        f"{item['emoji']} *{item['name']}*\n"
        f"⭐ Оплачено: *{stars} звёзд*\n\n"
        f"📦 Доставка в течение 1–24 часов.\n"
        f"По вопросам пиши сюда 👇",
        parse_mode="Markdown"
    )

    # Уведомление тебе
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 *НОВАЯ ПОКУПКА!*\n\n"
            f"👤 {user.full_name} (@{user.username or '—'})\n"
            f"🆔 ID: `{user.id}`\n"
            f"{item['emoji']} Товар: *{item['name']}*\n"
            f"⭐ Сумма: *{stars} звёзд*",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"Failed to notify admin: {e}")


# ─── Запуск ─────────────────────────────────────────────────────────────────
async def main():
    # HTTP сервер для WebApp
    app = web.Application()
    app.router.add_post('/create_invoice', create_invoice_handler)
    app.router.add_route('OPTIONS', '/create_invoice', create_invoice_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    log.info(f"HTTP server started on port {PORT}")

    # Telegram polling
    log.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

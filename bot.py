from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from datetime import datetime

import config
import database as db

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)

db.load_keys()

# клавиатура
def menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🚀 Купить VPN")
    kb.add("🔑 Мой доступ")
    kb.add("📜 Инструкция")
    if config.ADMIN_ID:
        kb.add("🛠 Админка")
    return kb

# проверка подписки
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(config.CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# старт
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🔐 Happ Key VPN\nВыберите действие:",
        reply_markup=menu()
    )

# выбор тарифа
@dp.message_handler(lambda m: m.text == "🚀 Купить VPN")
async def buy_menu(message: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("7 дней — 100⭐", callback_data="buy_week"))
    kb.add(types.InlineKeyboardButton("30 дней — 350⭐", callback_data="buy_month"))
    kb.add(types.InlineKeyboardButton("365 дней — 560⭐", callback_data="buy_year"))
    await message.answer("Выберите тариф:", reply_markup=kb)

# обработка выбора тарифа
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(call: types.CallbackQuery):
    user_id = call.from_user.id
    if not await check_sub(user_id):
        await call.message.answer("❌ Подпишись на канал!")
        return
    tariff = call.data.split("_")[1]
    price = config.PRICES[tariff]
    await bot.send_invoice(
        chat_id=user_id,
        title="Happ VPN",
        description=f"Подписка: {tariff}",
        payload=tariff,
        provider_token="",  # сюда вставь свой provider_token для Stars
        currency="XTR",
        prices=[types.LabeledPrice(label="VPN", amount=price)]
    )

# подтверждение оплаты
@dp.pre_checkout_query_handler(lambda q: True)
async def checkout(q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

# успешная оплата
@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def success(message: types.Message):
    user_id = message.from_user.id
    tariff = message.successful_payment.invoice_payload

    days_map = {"week": 7, "month": 30, "year": 365}
    days = days_map.get(tariff, 7)

    if db.get_user(user_id):
        await message.answer("⚠️ У тебя уже есть доступ")
        return

    key = db.get_key()
    if key:
        db.save_user(user_id, key, tariff, days)
        expires = datetime.now() + timedelta(days=days)
        await message.answer(
            f"✅ Оплата прошла!\n\n"
            f"🔑 Ключ: {key}\n"
            f"📅 Тариф: {tariff}\n"
            f"⏳ Действует до: {expires.date()}"
        )
    else:
        await message.answer("❌ Ключи закончились")

# мой доступ
@dp.message_handler(lambda m: m.text == "🔑 Мой доступ")
async def my_access(message: types.Message):
    data = db.get_user(message.from_user.id)
    if data:
        key, tariff, expires = data
        remaining = (expires - datetime.now()).days
        await message.answer(f"🔑 Ключ: {key}\n📅 Тариф: {tariff}\n⏳ Осталось дней: {remaining}")
    else:
        await message.answer("❌ Нет активной подписки")

# инструкция
@dp.message_handler(lambda m: m.text == "📜 Инструкция")
async def guide(message: types.Message):
    await message.answer(
        "📱 Скачай Happ VPN\n"
        "🔑 Вставь ключ\n"
        "🌐 Подключись"
    )

# админка
@dp.message_handler(lambda m: m.text == "🛠 Админка")
async def admin_panel(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Все пользователи")
    kb.add("➕ Продлить подписку")
    kb.add("🗂 Добавить ключи")
    kb.add("⬅️ Назад")
    await message.answer("🛠 Админка", reply_markup=kb)

# показать всех пользователей
@dp.message_handler(lambda m: m.text == "📊 Все пользователи")
async def list_users(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    users = db.all_users()
    text = ""
    for u in users:
        uid, key, tariff, expires = u
        expires_dt = datetime.fromisoformat(expires)
        remaining = (expires_dt - datetime.now()).days
        text += f"ID:{uid} | {key} | {tariff} | Осталось: {remaining}дн\n"
    await message.answer(text if text else "Нет пользователей")

# продлить подписку
@dp.message_handler(lambda m: m.text == "➕ Продлить подписку")
async def extend_sub(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    await message.answer("Введите ID пользователя и дни через пробел, например:\n123456789 30")

@dp.message_handler(lambda m: m.text and " " in m.text)
async def process_extend(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        user_id, days = map(int, message.text.split())
        new_expire = db.extend_user(user_id, days)
        if new_expire:
            await message.answer(f"✅ Подписка продлена до {new_expire.date()}")
        else:
            await message.answer("❌ Пользователь не найден")
    except:
        pass

# добавление ключей
@dp.message_handler(lambda m: m.text == "🗂 Добавить ключи")
async def add_keys(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    await message.answer("📤 Пришли ключи через запятую или в столбик")
    @dp.message_handler()
    async def receive_keys(msg: types.Message):
        keys = [k.strip() for k in msg.text.replace(",", "\n").split("\n") if k.strip()]
        with open("keys.txt", "a") as f:
            for k in keys:
                f.write(f"{k}\n")
        db.load_keys()
        await msg.answer(f"✅ Добавлено {len(keys)} ключей")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

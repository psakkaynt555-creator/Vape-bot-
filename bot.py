import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Вставь сюда свой токен от BotFather (в кавычках)
TOKEN = "9048872953:AAHmGmrGxfU989whNV5J3zmPf_PRfcp_a0U"

admin_router = Router()
logging.basicConfig(level=logging.INFO)


# Состояния для корзины и заказа
class OrderState(StatesGroup):
  waiting_for_payment = State()


# База товаров (можешь менять названия, цены и вкусы прямо здесь)
CATALOG = {
    "vape": {
        "title": "💨 Курилки",
        "items": {
            "waka_8k": {
                "name": "WAKA 8k",
                "price": "11.750₸",
                "flavors": ["Арбузный лед", "Мята", "Ягодный микс"],
            },
            "waka_10k": {
                "name": "WAKA 10k",
                "price": "13.750₸",
                "flavors": ["Клубника Киви", "Черника", "Энергетик"],
            },
            "elfbar_16k": {
                "name": "ElfBar BC Pro 16000",
                "price": "12.500₸",
                "flavors": ["Виноград", "Персик Манго", "Кола"],
            },
        },
    },
    "liquid": {
        "title": "🍸 Жидкости",
        "items": {
            "chrome_liquid": {
                "name": "Жидкость CHROME",
                "price": "4.750₸",
                "flavors": ["Черника Лимон", "Ежевичный Мохито"],
            }
        },
    },
}

# Корзина пользователей (в памяти)
carts = {}


# Главное меню
def get_main_menu():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="💨 Курилки", callback_data="cat_vape"
              ),
              InlineKeyboardButton(
                  text="🍸 Жидкости", callback_data="cat_liquid"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="ℹ️ Информация", callback_data="info"
              ),
              InlineKeyboardButton(text="🆘 Помощь", callback_data="help"),
          ],
      ]
  )


@admin_router.message(Command("start"))
async def cmd_start(message: Message):
  text = (
      "✨ **Главное меню**\n\nВыберите категорию из списка ниже:"
      " 👇"
  )
  await message.answer(text, reply_markup=get_main_menu(), parse_mode="Markdown")


@admin_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
  text = "✨ **Главное меню**\n\nВыберите категорию из списка ниже: 👇"
  await callback.message.edit_text(
      text, reply_markup=get_main_menu(), parse_mode="Markdown"
  )
  await callback.answer()


@admin_router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
  cat_key = callback.data.split("_")[1]
  category = CATALOG.get(cat_key)

  buttons = []
  for item_id, item_info in category["items"].items():
    buttons.append([
        InlineKeyboardButton(
            text=f"{item_info['name']} — {item_info['price']}",
            callback_data=f"item_{cat_key}_{item_id}",
        )
    ])

  buttons.append(
      [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
  )
  keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

  await callback.message.edit_text(
      f"📂 **{category['title']}**\n\nВыберите товар:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data.startswith("item_"))
async def show_item(callback: CallbackQuery):
  _, cat_key, item_id = callback.data.split("_")
  item = CATALOG[cat_key]["items"][item_id]

  buttons = []
  for flavor in item["flavors"]:
    buttons.append([
        InlineKeyboardButton(
            text=f"🟢 {flavor} (ост: 1шт)",
            callback_data=f"buy_{item_id}_{flavor}",
        )
    ])

  buttons.append(
      [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat_{cat_key}")]
  )
  keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

  await callback.message.edit_text(
      f"📦 **{item['name']} — {item['price']}**\nВыберите вкус:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data.startswith("buy_"))
async def add_to_cart(callback: CallbackQuery):
  parts = callback.data.split("_")
  item_id = parts[1]
  flavor = "_".join(parts[2:])

  user_id = callback.from_user.id
  if user_id not in carts:
    carts[user_id] = []

  # Ищем название товара
  item_name = ""
  item_price = ""
  for cat in CATALOG.values():
    if item_id in cat["items"]:
      item_name = cat["items"][item_id]["name"]
      item_price = cat["items"][item_id]["price"]

  carts[user_id].append(
      {"name": item_name, "price": item_price, "flavor": flavor}
  )

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🛒 Корзина", callback_data="show_cart"
              ),
              InlineKeyboardButton(
                  text="✅ Оформить заказ", callback_data="checkout"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="⬅️ Назад в меню", callback_data="back_to_main"
              )
          ],
      ]
  )

  await callback.message.edit_text(
      f"✅ **{item_name} — {item_price}** — {flavor} добавлен в"
      " корзину!\n\nМожете открыть корзину или перейти к оформлению.",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery):
  user_id = callback.from_user.id
  user_cart = carts.get(user_id, [])

  if not user_cart:
    await callback.answer("Ваша корзина пуста!", show_alert=True)
    return

  cart_text = "🛒 **Ваша корзина:**\n\n"
  for idx, prod in enumerate(user_cart, 1):
    cart_text += f"{idx}. {prod['name']} ({prod['flavor']}) — {prod['price']}\n"

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
          [InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")],
          [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")],
      ]
  )

  await callback.message.edit_text(
      cart_text, reply_markup=keyboard, parse_mode="Markdown"
  )
  await callback.answer()


@admin_router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
  user_id = callback.from_user.id
  carts[user_id] = []
  await callback.message.edit_text(
      "🗑 Корзина очищена!",
      reply_markup=InlineKeyboardMarkup(
          inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_main")]]
      ),
  )
  await callback.answer()


@admin_router.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery):
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="💳 Банковский перевод", callback_data="pay_card")],
          [InlineKeyboardButton(text="🪙 USDT TRC20 (-10%)", callback_data="pay_usdt")],
          [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="back_to_main")],
      ]
  )
  await callback.message.edit_text(
      "💳 **Выберите способ оплаты:**\n\nВаш заказ сформирован. Нажмите кнопку ниже:",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
  pay_type = "Банковский перевод" if callback.data == "pay_card" else "USDT TRC20 (со скидкой 10%)"
  user_id = callback.from_user.id
  carts[user_id] = []  д очищаем корзину после заказа

  await callback.message.edit_text(
      f"🎉 **Заказ успешно оформлен!**\n\nСпособ оплаты: {pay_type}\n\nС вами свяжется менеджер для подтверждения.",
      reply_markup=InlineKeyboardMarkup(
          inline_keyboard=[[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")]]
      ),
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data == "info")
async def info_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      "ℹ️ **Информация**\n\nДобро пожаловать в наш магазин! Быстрая доставка и лучшие цены.",
      reply_markup=InlineKeyboardMarkup(
          inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
      ),
      parse_mode="Markdown",
  )
  await callback.answer()


@admin_router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
  await callback.message.edit_text(
      "🆘 **Помощь / Поддержка**\n\nПо всем вопросам пишите администратору.",
      reply_markup=InlineKeyboardMarkup(
          inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
      ),
      parse_mode="Markdown",
  )
  await callback.answer()


async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(admin_router)
  await bot.delete_webhook(drop_pending_updates=True)
  print("Бот успешно запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())

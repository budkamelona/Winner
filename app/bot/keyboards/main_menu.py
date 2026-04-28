from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Создать розыгрыш", callback_data="menu:create_giveaway")],
            [InlineKeyboardButton(text="🗒 Мои розыгрыши", callback_data="menu:my_giveaways")],
            [InlineKeyboardButton(text="📢 Мои каналы", callback_data="menu:my_channels")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu:cancel")],
        ]
    )

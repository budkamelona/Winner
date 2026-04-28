from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.models import Channel


def channels_list_keyboard(channels: list[Channel], add_button: bool = True) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        label = f"📢 {ch.title}"
        if ch.username:
            label += f" (@{ch.username})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"channel:select:{ch.id}")])
    if add_button:
        rows.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="channel:add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_select_for_giveaway_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        label = f"📢 {ch.title}"
        if ch.username:
            label += f" (@{ch.username})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"giveaway:channel:{ch.id}")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="menu:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_detail_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить канал", callback_data=f"channel:delete:{channel_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu:my_channels")],
        ]
    )

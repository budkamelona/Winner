from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.infrastructure.models import FinishMode, Giveaway, GiveawayStatus


def finish_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖐 Вручную", callback_data="giveaway:finish_mode:manual")],
            [InlineKeyboardButton(text="⏰ По времени", callback_data="giveaway:finish_mode:by_time")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu:cancel")],
        ]
    )


def winner_selection_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Случайным образом", callback_data="giveaway:winner_mode:random")],
            [InlineKeyboardButton(text="✍️ Вручную", callback_data="giveaway:winner_mode:manual")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu:cancel")],
        ]
    )


def make_participate_keyboard(giveaway_id: int, count: int, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎁 Участвовать ({count})",
                    url=f"https://t.me/{bot_username}?start=join_{giveaway_id}",
                )
            ]
        ]
    )


def giveaway_manage_keyboard(giveaway: Giveaway) -> InlineKeyboardMarkup:
    rows = []
    if giveaway.status == GiveawayStatus.active and giveaway.finish_mode == FinishMode.manual:
        rows.append(
            [InlineKeyboardButton(text="🏁 Завершить розыгрыш", callback_data=f"giveaway:finish:{giveaway.id}")]
        )
    rows.append(
        [InlineKeyboardButton(text="🗑 Удалить розыгрыш", callback_data=f"giveaway:delete:{giveaway.id}")]
    )
    rows.append([InlineKeyboardButton(text="🔙 К списку", callback_data="menu:my_giveaways")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_delete_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"giveaway:delete_confirm:{giveaway_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"giveaway:view:{giveaway_id}")],
        ]
    )


def giveaways_list_keyboard(giveaways: list[Giveaway]) -> InlineKeyboardMarkup:
    rows = []
    status_emoji = {
        "active": "🟢",
        "finished": "✅",
        "draft": "📝",
        "scheduled": "⏰",
        "cancelled": "❌",
    }
    for g in giveaways:
        emoji = status_emoji.get(g.status, "")
        label = f"{emoji} #{g.id} — {g.text[:30]}{'...' if len(g.text) > 30 else ''}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"giveaway:view:{g.id}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_finish_keyboard(giveaway_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, завершить", callback_data=f"giveaway:finish_confirm:{giveaway_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"giveaway:view:{giveaway_id}")],
        ]
    )

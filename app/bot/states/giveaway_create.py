from aiogram.fsm.state import State, StatesGroup


class GiveawayCreateStates(StatesGroup):
    choosing_channel = State()
    entering_text = State()
    entering_winners_count = State()
    choosing_finish_mode = State()
    entering_finish_time = State()
    choosing_winner_selection_mode = State()

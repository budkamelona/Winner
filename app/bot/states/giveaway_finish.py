from aiogram.fsm.state import State, StatesGroup


class GiveawayFinishStates(StatesGroup):
    entering_winners = State()

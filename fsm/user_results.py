from aiogram.fsm.state import State, StatesGroup

class StateUser(StatesGroup):
    USER_CONFIRMATION = State()      # Подтверждение личности
    BRANCH_SELECTION = State()       # Выбор отделения (только для новых)
    LEGAL_EXAMINATION = State()      # Правовая экспертиза
    SUBSCRIPTION = State()           # Подписка
    NON_MORTGAGE_SECONDARY = State() # Неипотека-Вторичка
    NON_MORTGAGE_PRIMARY = State()   # Неипотека-Первичка
    NON_MORTGAGE_COUNTRY = State()   # Неипотека-Загородка
    CONFIRMATION = State()           # Подтверждение перед сохранением
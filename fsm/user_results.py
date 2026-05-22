from aiogram.fsm.state import State, StatesGroup

class StateUser(StatesGroup):
    USER_CONFIRMATION = State()      # Подтверждение личности
    BRANCH_SELECTION = State()       # Выбор отделения (только для новых)
    LEADS_COUNT = State()            # Сколько передали лидов по ЗП
    LEADS_LOOP = State()             # Состояние цикла: текущий индекс лида
    # Для каждого лида:
    LEADS_LOOP_LEAD_NAME = State()   # Имя Отчество клиента
    LEADS_LOOP_LEAD_CHANNEL = State()# Канал (ВСП/Премьер/Первый)
    CONFIRMATION = State()           # Подтверждение перед сохранением

from aiogram.filters import BaseFilter
from aiogram.types import Message
from database.admins.admin_query import admins_list


class IsAdmin(BaseFilter):
    key = 'is_admin'

    def __init__(self) -> None:
        self.admins = admins_list()

    async def __call__(self, msg: Message) -> bool:
        admins = [x[0] for x in self.admins]
        return msg.from_user.id in admins

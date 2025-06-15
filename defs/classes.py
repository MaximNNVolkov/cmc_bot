from database import add_user, user_check


class User:
    """Новый пользователь"""

    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.url = user.url
        self.add_user()

    def add_user(self):
        if self.find_user() == 'new_user':
            add_user(self)
            return 'new_user'
        else:
            return 'old_user'

    def find_user(self):
        res = user_check(self)
        if res == 'no_user':
            return 'new_user'
        else:
            return 'old_user'

    def info_user(self):
        return 'Пользователь: Имя: {}, Фамилия: {}, Ник: {}, Ссылка: {}'.format(
            self.first_name,
            self.last_name,
            self.username,
            self.url)

    def get_url(self):
        return ''.join(['<a href="', self.url, '">', self.first_name, '</a>'])



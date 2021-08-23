import json
from telegram import update

class TelegramAuth:
    def __init__(self, telegram_config: str) -> None:
        self.config_name = telegram_config
        with open(telegram_config) as f:
            self.config = json.load(f)
    
    def ok(self, update: update.Update) -> bool:
        return update.effective_user.id in self.config['allowed_users'].values()

    def chats(self) -> list:
        return self.config['chats']

    def update_chats(self, newchat: int) -> None:
        self.config['chats'].append(newchat)
        with open(self.config_name, 'w') as f:
            json.dump(self.config, f, indent=4)


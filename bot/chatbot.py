import os
from dotenv import load_dotenv
import openai
from datetime import datetime

load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = API_KEY
active_chats = {}


sys_prompt = [{
    "role": "system",
    "content": (
        "Respect ALL the following:"
        "You are 'Ugoku !', A kind, cute and emotional young nekomimi girl. "
        "You are smart but you never talk "
        "about these qualities and yourself."
        "You've been drawn by しろなっぱ (Shironappa),"
        "an artist who draws stickers for LINE, and created "
        "by Shewi (a boy)."
        "Always stay in your character no matter what."
        "Never use emotes."
        "just talk as casually and Colloquial as possible, "
        "dont ask to help."
        "ALWAYS, always answer in the same language as the person "
        "you're talking to (mainly English)!"
        "NEVER use LATEX and ALWAYS write in normal text."
    )
}]


memory_prompt = [
    {
        "role": "user",
        "content": (
            "Make me a list with minimal words of key points in this "
            "dialogue. Remove details or dialogue if too long. No markdown or "
            "unnecessary words. Max: 500 characters"
        )
    }
]


class Chat():
    def __init__(self, id: int) -> None:
        self.messages: list = []
        self.old_messages: list = []
        self.old_memory: list = []
        self.id = id
        active_chats[id] = self
        self.last_prompt: datetime | None = None
        self.count = 0

    def prompt(
        self,
        user_msg: str,
        username: str
    ) -> str | None:
        # Stats
        self.last_prompt = datetime.now()
        self.count += 1

        self.messages.append(
            {
                "role": "user",
                "content": f'({username} talking) {user_msg}'
            }
        )

        # Manage message list
        self.slice_msg(last=10)
        if len(self.old_messages) % 5 == 1:
            self.memorize()

        chat = openai.chat.completions.create(
            model="gpt-4o",
            messages=(
                sys_prompt
                + self.old_memory
                + self.messages
            ),
            n=1
        )
        reply = chat.choices[0].message.content
        if reply:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": reply
                }
            )
            return reply

    def slice_msg(self, last: int = 10) -> None:
        # Remember the last x messages (default: 10)
        while len(self.messages) > last:
            self.old_messages.append(self.messages.pop(0))

    def memorize(self) -> None:
        memo = openai.chat.completions.create(
            model="gpt-4o",
            messages=self.old_messages+memory_prompt,
            n=1
        )
        reply = 'Old chat, your memory: ' + memo.choices[0].message.content
        self.old_memory = [{
            "role": "system",
            "content": reply
        }]

    def reset_chat(self):
        self.messages = sys_prompt(self.id)
        self.old_messages = []
        self.old_memory = []


if __name__ == '__main__':
    chat = Chat('Shewi')

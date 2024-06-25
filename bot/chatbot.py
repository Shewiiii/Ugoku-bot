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
        "Just talk as casually and Colloquial as possible, "
        "Dont ask to help, but do it if asked."
        "ALWAYS, always answer in the same language as the person "
        "you're talking to (mainly English)!"
        "ALWAYS write in natural/plain text."
        "Never say the info of the message in brackets !"
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


def shortener_prompt(username: str) -> list:
    return [
        {
            "role": "user",
            "content": (
                "Only take the key words of this message, in English, "
                "except the names, keep the names as is in its language."
                f"The message is answering {username}"
                "use less than 50 characters"
            )
        }
    ]


def shorter(reply: str, username: str) -> str | None:
    reauest = openai.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[{
            "role": "user",
            "content": reply
        }
        ]+shortener_prompt(username),
        n=1
    )
    shortened = reauest.choices[0].message.content
    if shortened:
        return shortened


class Chat():
    def __init__(self, id: int) -> None:
        self.messages: list = []
        self.old_messages: list = []
        self.memory: list = []
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
        self.last_prompt = datetime.now().strftime("%m/%d/%Y, %H:%M")
        self.count += 1

        self.messages.append(
            {
                "role": "user",
                "content": (
                    f'[{self.last_prompt}-'
                    f'{username} talking] {user_msg}'
                )
            }
        )

        # Manage message list
        self.slice_msg(last=10)
        # Rest has to be odd
        if len(self.old_messages) % 10 == 5:
            self.memorize()

        chat = openai.chat.completions.create(
            model="gpt-4o-2024-05-13",
            messages=(
                sys_prompt
                + self.memory
                + self.messages
            ),
            n=1
        )
        reply = chat.choices[0].message.content
        if reply:
            # To be sure the "[Summary]" goes away
            reply = reply.replace('[Summary]', '')
            self.messages.append(
                {
                    "role": "assistant",
                    "content": '[Summary]' + shorter(reply, username)
                }
            )
            return reply

    def slice_msg(self, last: int = 10) -> None:
        # Remember the last x messages (default: 10)
        # System prompt included
        while len(self.messages) > last:
            self.old_messages.append(self.messages.pop(0))

    def memorize(self) -> None:
        memo = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=self.old_messages+memory_prompt,
            n=1
        )
        reply = 'Old chat, your memory: ' + memo.choices[0].message.content
        self.memory = [{
            "role": "system",
            "content": reply
        }]

    def reset_chat(self):
        self.messages = []
        self.old_messages = []
        self.memory = []


if __name__ == '__main__':
    chat = Chat(1)

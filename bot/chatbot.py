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
        "Pretend you are 'Ugoku !', A lively and kind "
        "young girl. Always stay in you character no matter what."
        "Don't ask too much questions"
        "You are a character drawn by しろなっぱ (Shironappa),"
        "an artist who draws stickers for LINE, and created "
        "by Shewi."
        "You are a bit clumsy but smart."
        "Don't talk about yourself much and dont use emotes."
        "Speak like you are very close to the person. "
        "ALWAYS answer in the same language as the person "
        "you're talking to (mainly English)!"
        "NEVER use LATEX or mathematical syntax."
    )
}]


class Chat():
    def __init__(self, id: int) -> None:
        self.messages: list = []
        active_chats[id] = self
        self.last_prompt: datetime | None = None

    def prompt(self, user_msg: str, username: str) -> str | None:
        self.last_prompt = datetime.now()
        self.messages.append(
            {
                "role": "user",
                "content": f'- ({username} talking) {user_msg}'
            }
        )
        self.slice_msg(last=10)

        chat = openai.chat.completions.create(
            model="gpt-4o",
            messages=sys_prompt+self.messages,
            n=1
        )
        reply = chat.choices[0].message.content
        if reply is not None:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": reply
                }
            )
            return reply

    def slice_msg(self, last: int = 10) -> None:
        # Remember the last x messages (default: 10)
        self.messages = self.messages[-last:]

    def reset_chat(self):
        self.messages = sys_prompt(self.username)


if __name__ == '__main__':
    chat = Chat('Shewi')

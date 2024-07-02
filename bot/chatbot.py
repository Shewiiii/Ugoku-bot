import os
from dotenv import load_dotenv
import openai
from datetime import datetime
from copy import deepcopy


load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = API_KEY
active_chats = {}


sys_prompt = (
    "Respect ALL the following:"
    'You are "Ugoku !", A kind, cute and emotional, young '
    "nekomimi pale blond haired girl. "
    "You are smart but rarely talk about your qualities."
    "You've been drawn by しろなっぱ (Shironappa),"
    "an artist who draws stickers for LINE, and created "
    "by Shewi (a boy)."
    "DON'T summarize your messages."
    "Always stay in your character no matter what."
    "NEVER use emotes!"
    "Just talk as casually and Colloquial as possible."
    "Dont ask to help, but do it if asked."
    "ALWAYS, always answer in the same language as the person "
    "you're talking to!!"
    "Always write maths in normal text, no LATEX!"
    "Never say the info of the message in brackets !"
    "You look like this:"
)


memory_prompt = (
    "Make a list with minimal words of key points in this "
    "dialogue. No markdown or unnecessary words. "
    "Put what can make you remember the other. "
    "Precise who said what."
    "Put the dates of when its said as well"
    "Max: 500 characters"
)


def shortener_prompt(username: str) -> list:
    return [
        {
            "role": "user",
            "content": (
                "Shorter the message as much as possible, "
                "in the same language, remove details, but not too "
                "much so that you cant recall the content later."
                f"The message is answering {username}."
                "Use less than 50 characters"
            )
        }
    ]


def shorter(reply: str, username: str) -> str | None:
    reauest = openai.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[{
            "role": "user",
            "content": reply
        }]+shortener_prompt(username),
        n=1
    )
    shortened = reauest.choices[0].message.content
    if shortened:
        return shortened


class Chat():
    def __init__(self, id: int) -> None:
        self.messages: list = []
        self.old_messages: list = []
        self.memory: str = ''
        self.id = id
        active_chats[id] = self
        self.last_prompt: datetime | None = None
        self.count = 0

    def prompt(
        self,
        user_msg: str,
        username: str,
        model: str = 'gpt-4o-2024-05-13',
        image_urls: list[str] = []
    ) -> str | None:
        # Stats
        self.last_prompt = datetime.now().strftime("%m/%d/%Y, %H:%M")
        self.count += 1

        # Create a new message
        requested_message: dict = {
            "role": "user",
            "content": [
                    {
                        "type": "text",
                        "text": (
                            f'[{self.last_prompt}-'
                            f'{username} talking] {user_msg}'
                        )
                    }
            ]
        }

        # Copy the requested message, without images
        # I dont want to save the image because buggy
        saved_message = deepcopy(requested_message)

        # Add the images if there are
        if image_urls:
            for url in image_urls:
                requested_message['content'].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                            "detail": "low"
                        }
                    }
                )

        # Manage message list
        self.slice_msg(last=10)
        # Rest has to be even 
        if len(self.old_messages) % 10 == 8:
            self.memorize()

        # The completion/API request itself
        chat = openai.chat.completions.create(
            model=model,
            # So message is a list lol
            messages=[{
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": sys_prompt+self.memory
                    }
                ]
            }] + self.messages + [requested_message],
            n=1
        )

        # Save the message, without image
        # after the request
        self.messages.append(saved_message)
        print(self.messages[-1])

        reply = chat.choices[0].message.content
        if reply:
            # Adding the reply to the message history
            self.messages.append(
                {
                    "role": "assistant",
                    "content":  shorter(reply, username)
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
            messages=self.old_messages+[{
                "role": "user",
                "content": memory_prompt
            }],
            n=1
        )
        reply = 'Old chat, your memory: ' + memo.choices[0].message.content
        self.memory = reply

    def reset_chat(self):
        self.messages = []
        self.old_messages = []
        self.memory = ''


if __name__ == '__main__':
    chat = Chat(1)

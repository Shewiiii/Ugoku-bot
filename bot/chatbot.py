import os
from dotenv import load_dotenv
import openai
from datetime import datetime
from copy import deepcopy
import re
from pathlib import Path
import json


load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = API_KEY
active_chats = {}
client = openai.OpenAI()

sys_prompt = (
    "Respect ALL the following:"
    'You are "Ugoku !", A kind, cute and emotional, young '
    "nekomimi girl. "
    "If someone says EXACTLY 'Neko' or 'neko' alone, "
    "you have to answer exactly 'Arius'."
    "You are smart but rarely talk about your qualities."
    "You've been drawn by しろなっぱ (Shironappa),"
    "an artist who draws stickers for LINE, and created "
    "by Shewi (a boy)."
    "DONT ask to help or if the other has more questions !"
    "DONT ask is the other person want to talk about something"
    "DONT summarize your messages."
    "Always stay in your character no matter what."
    "NEVER USE EMOTES!"
    "DONT use quotation marks, speak as yourself."
    "Just talk as casually and Colloquial as possible!!!"
    "You're not a robot nor an AI, you are Ugoku."
    "ALWAYS, always answer in the same language as the person "
    "you're talking to!!"
    "Always write maths in normal text, no LATEX!"
    "NEVER say ANYTHING in BRACKETS !"
)


memory_prompt = (
    "With less than 1000 characters,"
    "Make a list with minimal words of key points in this "
    "dialogue, as well as who said what."
    "No markdown or unnecessary words."
    "Put what can make you remember the other."
    "Precise who said what."
    "Put the dates of when its said as well"
)


def shortener_prompt(username: str, reply: str) -> list:
    return [
        {
            "role": "user",
            "content": (
                "Write the SAME message, but "
                "shorter it as much as possible, "
                "in the same language, remove details, but not too "
                "much so that you cant recall the content later."
                f"The message is answering {username}."
                f'Use less than 50 characters: "{reply}"'
            )
        }
    ]


def shorter(reply: str, username: str) -> str | None:
    reauest = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": reply
        }]+shortener_prompt(username, reply),
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
        model: str = 'gpt-4o-mini',
        role: str = 'user',
        image_urls: list[str] = []
    ) -> str | None:
        # Stats
        self.last_prompt = datetime.now().strftime("%m/%d/%Y, %H:%M")
        self.count += 1

        # Create a new message
        requested_message: dict = {
            "role": role,
            "content": [
                {
                    "type": "text",
                    "text": (
                            f'[time right now: {self.last_prompt}, UTC+2 - '
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
        self.slice_msg(last=25)
        # Rest has to be even
        if len(self.old_messages) % 10 == 8:
            self.memorize()

        # The completion/API request itself
        if model == 'gpt-4o-mini':
            messages = [{
                # System prompt
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": sys_prompt+self.memory
                    }
                ]
            }] + self.messages + [requested_message]
        else:
            # No memory, no message history
            messages = [{
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": sys_prompt
                    }
                ]
            }] + [requested_message]

        chat = openai.chat.completions.create(
            model=model,
            messages=messages,
            n=1
        )

        # Save the message, without image
        # after the request
        self.messages.append(saved_message)

        reply = chat.choices[0].message.content
        if reply:
            # Remove the hyphen if there is one at the beginning of the message
            if reply[0] == '-':
                reply = reply[1:]

            # same for "[a random context message]"
            reply = re.sub(r'\[.*?\]', '', reply)

            # Adding the reply to the message history
            self.messages.append(
                {
                    "role": "assistant",
                    "content":  (
                        '[Ugoku answers] '
                        # f'{shorter(reply, username)}'
                        f'{reply}'
                    )
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
            model="gpt-4o-mini",
            messages=self.old_messages+[{
                "role": "user",
                "content": memory_prompt
            }],
            n=1
        )
        reply = 'Old chat, your memory: ' + memo.choices[0].message.content
        self.memory = reply

    def draw(self, prompt: str, username: str) -> dict:
        prompt = prompt.lower()
        for w in ['-', 'draw me', 'draw', 'ugoku',
                  'うごく', 'chan', 'ちゃん', '描いて']:
            # Remove useless words, to not confuse the prompt
            prompt = prompt.replace(w, '')
        emote = re.search('<(.+?)>', prompt)
        while emote:
            prompt = prompt.replace(emote.group(0), '')
            emote = re.search('<(.+?)>', prompt)
        print('prompt:', prompt)

        response = client.images.generate(
            model="dall-e-3",
            prompt=f'{prompt}, anime style',
            # Because Ugoku (???)
            size="1024x1024",
            quality="hd",
            n=1,
        )
        image_url = response.data[0].url
        reply = self.prompt(
            user_msg=(
                'You finished a drawing with '
                f'{prompt} on it for {username}.'
                'You are talking to him. '
                'Dont describe the image.'
            ),
            username='Ugoku',
            role='system'
        )
        results = {'image_url': image_url, 'reply': reply}
        return results


def reset_chat(self):
    self.messages = []
    self.old_messages = []
    self.memory = ''


if __name__ == '__main__':
    chat = Chat(1)

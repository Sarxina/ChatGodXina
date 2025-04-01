from twitchio.ext import commands
from twitchio import *
from datetime import datetime, timedelta
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import asyncio
import threading
import pytz
import random
import os
from voices_manager import TTSManager

load_dotenv()

TWITCH_CHANNEL_NAME = os.getenv('TWITCH_CHANNEL_NAME')
VOICE_OPTIONS = [
    "en-US-DavisNeural",
    "en-US-TonyNeural",
    "en-US-JasonNeural",
    "en-US-GuyNeural",
    "en-US-JaneNeural",
    "en-US-NancyNeural",
    "en-US-JennyNeural",
    "en-US-AriaNeural",
]

socketio = SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")
print(socketio.async_mode)

@app.route("/")
def home():
    return render_template('index.html') #redirects to index.html in templates folder

@socketio.event
def connect(): #when socket connects, send data confirming connection
    socketio.emit('message_send', {'message': "Connected successfully!", 'current_user': "Temp User", 'user_number': "1"})

@socketio.on("tts")
def toggletts(value):
    print("TTS: Received the value " + str(value['checked']))
    twitchbot.gods[int(value['user_number']) - 1].tts_enabled = value['checked']

@socketio.on("pickrandom")
def pickrandom(value):
    twitchbot.randomUser(int(value['user_number']))
    print("Getting new random user for user " + value['user_number'])




@socketio.on("choose")
def chooseuser(value):
    """Choose a user for the given god"""

    # Check to see if we have enough gods
    if len(twitchbot.gods) < int(value['user_number']):
        return

    twitchbot.gods[int(value['user_number']) - 1].name = value['chosen_user'].lower()
    socketio.emit('message_send', {
        'message': f"{value['chosen_user']} was picked!",
        'current_user': f"{value['chosen_user']}",
        'user_number': value['user_number']
    })


@socketio.on("voicename")
def choose_voice_name(value):
    if (value['voice_name']) != None:
        twitchbot.update_voice_name(value['user_number'], value['voice_name'])
        print("Updating voice name to: " + value['voice_name'])

@socketio.on("voicestyle")
def choose_voice_style(value):
    if (value['voice_style']) != None:
        twitchbot.update_voice_style(value['user_number'], value['voice_style'])
        print("Updating voice style to: " + value['voice_style'])


class GodUser:
    # Current username of the god
    name = None
    # Whether TTS is enabled for this user
    tts_enabled = True
    # Passphrase to become this user
    key_passphrase = ""
    # dict of usernames and time last chatted
    user_pool = {}

    voice_name = None
    voice_style = "random"
    tts_manager = None

    number = 0

    def __init__(self, number, tts_manager=None, voice_name=None, voice_style=None):
        """Constructor for the GodUser class"""
        self.number = number
        self.key_passphrase = f'!player{number}'
        self.tts_manager = tts_manager
        self.voice_name = voice_name if voice_name else random.choice(VOICE_OPTIONS)
        self.voice_style = voice_style if voice_style else "random"

    def choose_god(self):
        self.name = random.choice(list(self.user_pool.keys()))
        socketio.emit('message_send', {
            'message': f"{self.name} was picked!",
            'current_user': f"{self.name}",
            'user_number': self.number
        })
        print("Random User is: " + self.name)

    def update_voice_name(self, voice_name):
        """Setter for the god's voice name"""
        self.voice_name = voice_name

    def update_voice_style(self, voice_style):
        """Setter for the god's voice style"""
        self.voice_style = voice_style

    def enable_move(self):
        """Enable the OBS move filter for the god"""
        self.tts_manager.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - DnD Player {self.number}", True)
    def disable_move(self):
        """Disable the OBS move filter for the god"""
        self.tts_manager.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - DnD Player {self.number}", False)

    def speak(self, text):
        """Speak the given text using the god's TTS settings"""
        if self.tts_enabled and self.tts_manager:
            self.enable_move()
            tts_file = self.tts_manager.azuretts_manager.text_to_audio(text, self.voice_name, self.voice_style)
            self.disable_move()
            self.tts_manager.audio_manager.play_audio(tts_file, True, True, True)
        else:
            print("TTS is not enabled for this user.")

class Bot(commands.Bot):
    gods = []
    seconds_active = 450 # of seconds until a chatter is booted from the list
    max_users = 2000 # of users who can be in user pool
    tts_manager = None

    @property
    def name_to_user(self):
        """Maps the 3 god's current usernames to user object"""
        return {self.gods[i].name: self.gods[i] for i in range(len(self.gods))}

    @property
    def keyphrase_to_user_pool(self):
        """Maps the 3 god's keyphrases to their user pool"""
        return {self.gods[i].key_passphrase: self.gods[i].user_pool for i in range(len(self.gods))}

    def __init__(self, num_gods = 3):
        load_dotenv()
        self.tts_manager = TTSManager()
        self.gods = [
            GodUser(number=i,
                    tts_manager=self.tts_manager,
                    voice_name=VOICE_OPTIONS[i - 1],
                    voice_style="random",)
            for i in range(1, num_gods + 1)]

        #connects to twitch channel
        print("THe access token is: " + os.getenv('TWITCH_ACCESS_TOKEN'))
        print("The channel name is: " + os.getenv('TWITCH_CHANNEL_NAME'))
        print(os.getenv('TWITCH_ACCESS_TOKEN'))
        super().__init__(token=os.getenv('TWITCH_ACCESS_TOKEN'),
                         prefix='?',
                         initial_channels=[TWITCH_CHANNEL_NAME])

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def event_message(self, message):
        await self.process_message(message)

    async def process_message(self, message: Message):
        # print("We got a message from this person: " + message.author.name)
        # print("Their message was " + message.content)

        # If this is our current_user, read out their message

        if message.author.name in self.name_to_user:
            user = self.name_to_user[message.author.name]

            socketio.emit('message_send', {
                'message': f'{message.content}',
                'current_user': f'{user.name}',
                'user_number': user.number
            })
            if user.tts_enabled:
                user.speak(message.content)

        if message.content in self.keyphrase_to_user_pool:
            user_pool = self.keyphrase_to_user_pool[message.content]

            if message.author.name.lower() in user_pool:
                # Remove this chatter from pool if they're already there
                user_pool.pop(message.author.name.lower())
            # Add user to end of pool with new msg time
            user_pool[message.author.name.lower()] = message.timestamp
            # Now we remove the oldest viewer if they're past the activity threshold, or if we're past the max # of users
            activity_threshold = datetime.now(pytz.utc) - timedelta(seconds=self.seconds_active)  # calculate the cutoff time
            oldest_user = list(user_pool.keys())[0]  # The first user in the dict is the user who chatted longest ago
            if user_pool[oldest_user].replace(tzinfo=pytz.utc) < activity_threshold or len(user_pool) > self.max_users:
                user_pool.pop(oldest_user)
                if len(user_pool) == self.max_users:
                    print(f"{oldest_user} was popped due to hitting max users")
                else:
                    print(f"{oldest_user} was popped due to not talking for {self.seconds_active} seconds")

    def randomUser(self, user_number):
        """Choose the user for the given god"""
        try:
            self.gods[user_number - 1].choose_god()
        except Exception as e:
            print(f"Error in randomUser: {e}")

    def update_voice_name(self, user_number, voice_name):
        self.gods[user_number - 1].update_voice_name(voice_name)

    def update_voice_style(self, user_number, voice_style):
        """Update the voice style for the given god"""
        self.gods[user_number - 1].update_voice_style(voice_style)


def startTwitchBot():
    global twitchbot
    asyncio.set_event_loop(asyncio.new_event_loop())
    twitchbot = Bot()
    twitchbot.run()

if __name__=='__main__':

    # Creates and runs the twitchio bot on a separate thread
    bot_thread = threading.Thread(target=startTwitchBot)
    bot_thread.start()

    socketio.run(app)

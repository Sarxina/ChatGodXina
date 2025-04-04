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
from src.main.voices_manager import TTSManager

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

    chat_god_route = None

    socketio = None

    number = 0

    @property
    def source_group_name(self):
        """The OBS source gorup name for this god"""
        return f"CG{self.number} Group"

    def __init__(self,
                 number,
                 socketio=None,
                 tts_manager=None,
                 voice_name=None,
                 voice_style=None):
        """Constructor for the GodUser class"""

        self.socketio = socketio
        self.number = number
        self.key_passphrase = f'!player{number}'
        self.tts_manager = tts_manager
        self.voice_name = voice_name if voice_name else random.choice(VOICE_OPTIONS)
        self.voice_style = voice_style if voice_style else "random"

    def choose_god(self):
        """Choose a random user from the user pool"""
        self.name = random.choice(list(self.user_pool.keys()))
        self.socketio.emit('message_send', {
            'message': f"{self.name} was picked!",
            'current_user': f"{self.name}",
            'user_number': self.number
        }, namespace='/chatgod')
        print("Random User is: " + self.name)

    def update_voice_name(self, voice_name):
        """Setter for the god's voice name"""
        self.voice_name = voice_name

    def update_voice_style(self, voice_style):
        """Setter for the god's voice style"""
        self.voice_style = voice_style

    def _toggle_animation_visibility(self, visible=True):
        """Toggle the visibility of the god's animation in OBS"""
        self.tts_manager.obswebsockets_manager.set_filter_visibility(self.source_group_name, "Chat God Talk", visible)
    def enable_move(self):
        """Enable the OBS move filter for the god"""
        self._toggle_animation_visibility(True)
    def disable_move(self):
        """Disable the OBS move filter for the god"""
        self._toggle_animation_visibility(False)

    def speak(self, text):
        """Speak the given text using the god's TTS settings"""
        if self.tts_enabled and self.tts_manager:
            self.enable_move()
            tts_file = self.tts_manager.azuretts_manager.text_to_audio(text, self.voice_name, self.voice_style)
            self.tts_manager.audio_manager.play_audio(tts_file, True, True, True)
            self.disable_move()
        else:
            print("TTS is not enabled for this user.")


class Bot(commands.Bot):
    gods = []
    seconds_active = 450 # of seconds until a chatter is booted from the list
    max_users = 2000 # of users who can be in user pool
    tts_manager = None

    obs_scene_name = "Chat Gods"

    chat_god_route = None


    @property
    def name_to_user(self):
        """Maps the 3 god's current usernames to user object"""
        return {self.gods[i].name: self.gods[i] for i in range(len(self.gods))}

    @property
    def keyphrase_to_user_pool(self):
        """Maps the 3 god's keyphrases to their user pool"""
        return {self.gods[i].key_passphrase: self.gods[i].user_pool for i in range(len(self.gods))}

    def __init__(self, num_gods = 3, socketio=None):
        load_dotenv()
        self.socketio = socketio
        self.tts_manager = TTSManager()
        self.gods = [
            GodUser(number=i,
                    socketio=self.socketio,
                    tts_manager=self.tts_manager,
                    voice_name=VOICE_OPTIONS[i - 1],
                    voice_style="random")
            for i in range(1, num_gods + 1)]

        #connects to twitch channel
        print("THe access token is: " + os.getenv('TWITCH_ACCESS_TOKEN'))
        print("The channel name is: " + os.getenv('TWITCH_CHANNEL_NAME'))
        print(os.getenv('TWITCH_ACCESS_TOKEN'))
        super().__init__(token=os.getenv('TWITCH_ACCESS_TOKEN'),
                         prefix='?',
                         initial_channels=[TWITCH_CHANNEL_NAME])

    async def god_message(self, message: Message):
        """Send a message to the Twitch channel as the god"""
        user = self.name_to_user[message.author.name]
        self.socketio.emit('message_send', {
            'message': f'{message.content}',
            'current_user': f'{user.name}',
            'user_number': user.number
        }, namespace='/chatgod')
        if user.tts_enabled:
            user.speak(message.content)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def event_message(self, message):
        await self.process_message(message)

    async def process_message(self, message: Message):
        # print("We got a message from this person: " + message.author.name)
        # print("Their message was " + message.content)

       # If the the user is a god. send their message
        if message.author.name in self.name_to_user:
            await self.god_message(message)

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
        self.gods[int(user_number) - 1].update_voice_name(voice_name)

    def update_voice_style(self, user_number, voice_style):
        """Update the voice style for the given god"""
        self.gods[int(user_number) - 1].update_voice_style(voice_style)

class ChatGodApp:
    def __init__(self):
        self.flask_app = Flask(__name__)
        self.socketio = SocketIO(self.flask_app, async_mode='threading')
        self.twitchbot = self._create_bot()
        self._register_routes()
        self._register_events()

    async def handle_god_messages(self, message: Message):
        """Can be overriden in child classes for custom message behavior"""
        pass

    def _create_bot(self):
        """Creates a new chatbot with a custom on message hook"""
        twitchbot = Bot(num_gods=3, socketio=self.socketio)

        base_god_message = twitchbot.god_message

        async def god_message(message: Message):
            await base_god_message(message)
            await self.handle_god_messages(message)

        twitchbot.god_message = god_message
        return twitchbot

    def _register_routes(self):
        @self.flask_app.route('/')
        def home():
            return render_template('index.html')

    def _register_events(self):
        @self.socketio.on('connect', namespace='/chatgod')
        def connect():
            self.socketio.emit('message_send', {
                'message': "Connected successfully!",
                'current_user': "Temp User",
                'user_number': "1"
            }, namespace='/chatgod')

        @self.socketio.on("tts", namespace='/chatgod')
        def toggletts(value):
            print("TTS: Received the value " + str(value['checked']))
            self.twitchbot.gods[int(value['user_number']) - 1].tts_enabled = value['checked']

        @self.socketio.on("pickrandom", namespace='/chatgod')
        def pickrandom(value):
            self.twitchbot.randomUser(int(value['user_number']))
            print("Getting new random user for user " + value['user_number'])

        @self.socketio.on("choose", namespace='/chatgod')
        def chooseuser(value):
            if len(self.twitchbot.gods) < int(value['user_number']):
                return
            self.twitchbot.gods[int(value['user_number']) - 1].name = value['chosen_user'].lower()
            self.socketio.emit('message_send', {
                'message': f"{value['chosen_user']} was picked!",
                'current_user': f"{value['chosen_user']}",
                'user_number': value['user_number']
            }, namespace='/chatgod')

        @self.socketio.on("voicename", namespace='/chatgod')
        def choose_voice_name(value):
            if value['voice_name'] is not None:
                self.twitchbot.update_voice_name(value['user_number'], value['voice_name'])
                print("Updating voice name to: " + value['voice_name'])

        @self.socketio.on("voicestyle", namespace='/chatgod')
        def choose_voice_style(value):
            if value['voice_style'] is not None:
                self.twitchbot.update_voice_style(value['user_number'], value['voice_style'])
                print("Updating voice style to: " + value['voice_style'])

    def start_bot_async(self):
        """Start the Twitch bot"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.twitchbot.run()

    def start_bot_on_thread(self):
        """Start the Twitch bot on a separate thread"""
        bot_thread = threading.Thread(target=self.start_bot_async)
        bot_thread.start()

    def run(self):
        """Run the Flask app and the Twitch bot"""
        self.start_bot_on_thread()
        self.socketio.run(self.flask_app)


if __name__=='__main__':
    ChatGodApp().run()

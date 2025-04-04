from flask import send_file
from pathlib import Path

import requests
import re
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

from src.main.chat_god_app import ChatGodApp
CLIENT_SECRETS_FILE = 'src/chat_remote/youtube_secret.json'
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

class ChatRemote(ChatGodApp):

    def __init__(self):
        super().__init__()
        self.service = self.get_authenticated_service()
    def _register_routes(self):
        super()._register_routes()
        @self.flask_app.route('/chatremote')
        def chatremote_home():
            return send_file(Path(__file__).parent / 'frontend.html')

    def _register_events(self):
        super()._register_events()

        @self.socketio.on('connect', namespace='/chatremote')
        def on_chatremote_connect():
            print('Client connected to /chatremote')

    def _search_youtube_scrape(self, query):
        """You can use this option if you do not have a YouTUbe API key"""
        url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
        resp = requests.get(url)
        if resp.ok:
            match = re.search(r'\"videoId\":\"(.*?)\"', resp.text)
            if match:
                return match.group(1)
        return None

    def get_authenticated_service(self):
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0, open_browser=True)
        return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    async def get_first_video_id(self, query: str) -> str:
        request = self.service.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=1
        )
        response = request.execute()
        print("Response:", response)
        return response['items'][0]['id']['videoId']

    def _get_youtube_query(self, msg):
        """Extracts the YouTube query from the message."""
        commands = ['i wanna watch', 'i want to watch']

        # get the first command that matches the messag
        matched = next((cmd for cmd in commands if msg.content.lower().startswith(cmd + ' ')), None)
        return msg.content.replace(matched + ' ', '', 1).strip() if matched else None

    async def _handle_god_messages(self, message):
        """Attempts to change the channel"""
        query = self._get_youtube_query(message)
        if query:
            print("Query found:", query)
            video_id = await self.get_first_video_id(query)
            if video_id:
                print("Video ID found:", video_id)
                self.socketio.emit('load_video', {'videoId': video_id}, namespace='/chatremote')
                self.socketio.emit('message_send', {'message': 'Sent load_video'}, namespace='/chatgod')


    async def handle_god_messages(self, message):
        await self._handle_god_messages(message)

    # def run(self, **kwargs):
    #     self.socketio.run(self.app, **kwargs)

if __name__ == '__main__':
    start_chatgod()
    ChatRemote()
    socketio.run(chatgod_app)

from flask import send_file
import requests
import re

import sys
from pathlib import Path

from src.main.chat_god_app import ChatGodApp

class ChatRemote(ChatGodApp):
    def _register_routes(self):
        super()._register_routes()
        @self.flask_app.route('/chatremote')
        def home():
            return send_file("frontend.html")

    def _register_events(self):
        super()._register_events()
        @self.socketio.on('new_message', namespace='/chatremote')
        def handle_chat_message(data):
            msg = data.get('message', '').lower()
            if msg.startswith('i wanna watch '):
                query = msg.replace('i wanna watch ', '', 1).strip()
                video_id = self._search_youtube(query)
                if video_id:
                    self.socketio.emit('load_video', {'videoId': video_id}, namespace='/chatremote')

    # def _search_youtube(self, query):
    #     url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
    #     resp = requests.get(url)
    #     if resp.ok:
    #         match = re.search(r'\"videoId\":\"(.*?)\"', resp.text)
    #         if match:
    #             return match.group(1)
    #     return None

    # def run(self, **kwargs):
    #     self.socketio.run(self.app, **kwargs)

if __name__ == '__main__':
    start_chatgod()
    ChatRemote()
    socketio.run(chatgod_app)

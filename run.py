import argparse
from src.main.chat_god_app import ChatGodApp
from src.chat_remote.chat_remote import ChatRemote

app_map = {
    'main': ChatGodApp,
    'chatremote': ChatRemote
}

parser = argparse.ArgumentParser(description="Chat God Application")
parser.add_argument('--port', type=int, default=5000)
parser.add_argument('--app',
                    type=str,
                    choices=app_map.keys(),
                    default='main',
                    help="Choose the application to run")

args = parser.parse_args()

app = app_map[args.app]()
app.run()

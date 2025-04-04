from src.main.audio_player import AudioManager
from src.main.obs_websockets import OBSWebsocketsManager
from src.main.azure_text_to_speech import AzureTTSManager

class TTSManager:
    azuretts_manager = AzureTTSManager()
    audio_manager = AudioManager()
    obswebsockets_manager = OBSWebsocketsManager()

    user1_voice_name = "en-US-DavisNeural"
    user1_voice_style = "random"
    user2_voice_name = "en-US-TonyNeural"
    user2_voice_style = "random"
    user3_voice_name = "en-US-JaneNeural"
    user3_voice_style = "random"

    def __init__(self):
        file_path = self.azuretts_manager.text_to_audio("Chat God App is now running!") # Say some shit when the app starts
        self.audio_manager.play_audio(file_path, True, True, True)

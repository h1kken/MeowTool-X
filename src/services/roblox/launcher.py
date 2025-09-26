from src.utils import current_time_in_ms, generate_browser_tracker_id, encode_string_to_url
from .account import RobloxAccount


class RobloxLauncher:
    def __init__(self):
        self._launchers = {}
        
    def launch(self, auth_ticket: str, place_id: str, server_id: str):
        launch_time = current_time_in_ms()
        browser_tracker_id = generate_browser_tracker_id()
        
        launch_url =  f'https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGame&placeId={place_id}&gameId={server_id}&isPlayTogetherGame=false&isTeleport=true'
        encoded_launch_url = encode_string_to_url(launch_url)
        
        arguments = f'roblox-player:1+launchmode:play+gameinfo:{auth_ticket}+launchtime:{launch_time}+placelauncherurl:{encoded_launch_url}+browsertrackerid:{browser_tracker_id}+robloxLocale:en_us+gameLocale:en_us+channel:+LaunchExp:InApp'
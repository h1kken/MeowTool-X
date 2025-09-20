from typing import Literal
from src.http.manager import RequestManager

class RobloxApis:
    @staticmethod
    def get_simple_account_data(cookies: dict[str, str]) -> dict:
        with RequestManager(cookies=cookies) as client:
            response = client.get('https://users.roblox.com/v1/users/authenticated').json()
        return response

    @staticmethod
    def get_complex_account_data(cookies: dict[str, str]) -> dict:
        with RequestManager(cookies=cookies) as client:
            response = client.get('https://www.roblox.com/my/settings/json').json()
        return response
    
    @staticmethod
    def get_user_is_achieved_badge(cookies: dict[str, str], user_id: int | str, badge_id: int | str) -> bool:
        with RequestManager(cookies=cookies) as client:
            response = client.get(f'https://badges.roblox.com/v1/users/{user_id}/badges/{badge_id}/awarded-date')
        return True if response else False

    @staticmethod
    def get_place_id_user_in(cookies: dict, user_id: int | str) -> int:
        data = {
            'userIds': [user_id]
        }
        with RequestManager(cookies=cookies) as client:
            response = client.post('https://presence.roblox.com/v1/presence/users', data=data).json()
        return response['userPresences'][0]['placeId']

    @staticmethod
    def get_x_csrf_token(cookies: dict[str, str]) -> str:
        with RequestManager(cookies=cookies) as client:
            response = client.post('https://auth.roblox.com/v2/logout').headers
        return response['X-CSRF-Token']

    @staticmethod
    def get_auth_ticket(cookies: dict[str, str], x_csrf_token: str) -> str:
        headers = {
            'X-CSRF-Token': x_csrf_token,
            'referer': 'https://www.roblox.com/hewhewhew'
        }
        with RequestManager(headers=headers, cookies=cookies) as client:
            response = client.post('https://auth.roblox.com/v1/authentication-ticket').headers
        return response['rbx-authentication-ticket']

    @staticmethod
    def get_server_ids(place_id: int | str, *, less_players=True, exclude_full_places=True, amount: Literal['5', '10', '25', '50', '100'] = '25') -> dict:
        with RequestManager() as client:
            response = client.get(f'https://games.roblox.com/v1/games/{place_id}/servers/0?{'sortOrder=1&' if less_players else ''}{'excludeFullGames=true&' if exclude_full_places else ''}limit={amount}').json()
        return response
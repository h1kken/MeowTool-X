import re
import asyncio
from typing import Optional
from typing import Literal
from src.exceptions.roblox import InvalidCookie
from src.utils.regex_utils import ROBLOX_COOKIE_PATTERN
from src.utils.date_utils import convert_date
from services.roblox.http.client import RobloxHttpClient
from src.config.manager import config
from src.utils.string_utils import convert_age_group
from src.utils.file_utils import get_nested

from src.utils.consts import (
    DATE_ROBLOX_REG_DATE_FORMAT,
    TIME_FRAME_TRANSACTIONS,
    ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME,
    ITEMS_PER_PAGE_RAP,
    ITEMS_PER_PAGE_GAMEPASSES,
    ITEMS_PER_PAGE_BADGES,
    ITEMS_PER_PAGE_FAVORITE_PLACES,
    ITEMS_PER_PAGE_BUNDLES,
    ITEMS_PER_PAGE_PLACE_SERVER_IDS
)

class RobloxAccount:
    def __init__(
        self,
        session: RobloxHttpClient,
        cookies: Optional[dict[str, str]] = None,
        account_information: Optional[dict] = None
    ):
        self._session = session
        self._cookies = cookies
        self._account_information = account_information or {}
        self._player_id = self._account_information.get('UserId')
        self._player_name = self._account_information.get('Name')
        self.data = {}

    @property
    def cookie(self) -> str:
        return (self._cookies or {}).get('.ROBLOSECURITY')

    async def get_simple_account_information(self) -> dict:
        return await (await self._session.get('https://users.roblox.com/v1/users/authenticated', cookies=self._cookies)).json()

    async def get_complex_account_information(self) -> dict:
        return await (await self._session.get('https://www.roblox.com/my/settings/json')).json()

    async def get_profile_information(
        self,
        *components: Literal[
            'UserProfileHeader',
            'Actions',
            'About',
            'CurrentlyWearing',
            'ContentPosts',
            'Friends',
            'Collections',
            'Communities',
            'FavoriteExperiences',
            'RobloxBadges',
            'PlayerBadges',
            'Statistics',
            'Experiences',
            'CreationsModels',
            'Clothing',
            'Store'
        ]
    ) -> dict:
        json = {
            'components': [{'component': component} for component in components],
            'includeComponentOrdering': True,
            'profileId': str(self._player_id),
            'profileType': 'User'
        }
        return await (await self._session.post('https://apis.roblox.com/profile-platform-api/v1/profiles/get', json=json)).json()
    
    def get_link(self) -> str:
        return f'https://www.roblox.com/users/{self._player_id}'
    
    def get_id(self) -> int:
        return self._account_information.get('UserId')
    
    def get_name(self) -> str:
        return self._account_information.get('Name')
    
    def get_display_name(self) -> str:
        return self._account_information.get('DisplayName')
    
    async def get_country_registration(self) -> str:
        response: dict = await (await self._session.get('https://users.roblox.com/v1/users/authenticated/country-code')).json()
        return response.get('countryCode')
    
    async def get_registration_date_dmy(self) -> str:
        response: dict = await (await self._session.get(f'https://users.roblox.com/v1/users/{self._player_id}')).json()
        return convert_date(response.get('created'), DATE_ROBLOX_REG_DATE_FORMAT)
    
    def get_registration_date_in_days(self) -> int:
        return self._account_information.get('AccountAgeInDays')
    
    async def get_robux(self) -> int:
        response: dict = await (await self._session.get(f'https://economy.roblox.com/v1/users/{self._player_id}/currency')).json()
        return response.get('robux')
    
    async def get_billing(self) -> int:
        response: dict = await (await self._session.get('https://billing.roblox.com/v1/credit')).json()
        return response.get('robuxAmount')
    
    async def get_transactions_time_frame(self, *, time_frame: Literal['Day', 'Week', 'Month', 'Year'] = TIME_FRAME_TRANSACTIONS) -> dict:
        params = {
            'timeFrame': time_frame,
            'transactionType': 'Summary'
        }
        response: dict = await (await self._session.get(f'https://economy.roblox.com/v2/users/{self._player_id}/transaction-totals', params=params)).json()
        return {
            'pending': response.get('pendingRobuxTotal'),
            'donate': abs(response.get('outgoingRobuxTotal'))
        }
        
    async def get_transaction_all_time(self, *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME) -> dict:
        donate_all_time = 0
        check_list_custom_gamepasses = ...
        cur_page = 0
        donate_all_time_max_page = config.get('Roblox.Cookie_Checker.Main.Donate_All_Time_Max_Check_Pages', default=-1)
        custom_gamepasses_max_page = config.get('Roblox.Cookie_Checker.Main.Custom_Gamepasses_Max_Check_Pages', default=-1)
        max_page = max(donate_all_time_max_page, custom_gamepasses_max_page)
        params = {
            'transactionType': 2,
            'limit': items_per_page,
            'cursor': ''
        }
        while params.get('cursor') is not None and cur_page != max_page:
            # response: dict = (await self._client.get(f'https://economy.roblox.com/v2/users/{self._player_id}/transactions', params=params, cookies=self._cookies)).json()
            # for transaction in response.get('data', []):
            #     if config.get('Roblox.Cookie_Checker.Main.Donate_All_Time') and (donate_all_time_max_page == -1 or cur_page < donate_all_time_max_page):
            #         donate_all_time += transaction['currency']['amount']
            #     if config.get('Roblox.Cookie_Checker.Main.Custom_Gamepasses') and 'name' in transaction['details'] and transaction['details']['name'] in ... and (custom_gamepasses_max_page == -1 or cur_page < custom_gamepasses_max_page):
            #         check_list_custom_gamepasses[transaction['details']['name']] += 1
            # params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
            
        return {
            'donate_all_time': abs(donate_all_time),
            'custom_gamepasses': check_list_custom_gamepasses
        }
    
    async def get_rap(self, *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_RAP) -> int:
        rap = 0
        cur_page = 0
        max_page = config.get('Roblox.Cookie_Checker.Main.Rap_Max_Check_Pages', default=-1)
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while params.get('cursor') is not None and cur_page != max_page:
            response: dict[str, list[dict]] = (await self._session.get(f'https://inventory.roblox.com/v1/users/{self._player_id}/assets/collectibles', params=params, cookies=self._cookies)).json()
            rap = sum(item for item in response.get('data', []) if type(item.get('recentAveragePrice')) is int)
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return rap
    
    async def get_cards(self) -> int:
        response: dict = await (await self._session.get(f'https://apis.roblox.com/payments-gateway/v1/payment-profiles', cookies=self._cookies)).json()
        return len(response)
    
    async def get_premium(self) -> bool:
        return self._account_information.get('IsPremium')
    
    async def get_gamepasses(self, *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_GAMEPASSES) -> list:
        check_list_gamepasses = {gamepass['PlaceName']: [] for gamepass in ....values()}
        check_list_gamepasses_amount = len(...)
        found_gamepasses_amount = 0
        cur_page, max_page = 0, config.get('Roblox.Cookie_Checker.Main.Gamepasses_Max_Check_Pages', default=-1)
        params = {
            'count': items_per_page,
            'exclusiveStartId': ''
        }
        while params.get('exclusiveStartId') is not None and cur_page != max_page and found_gamepasses_amount != check_list_gamepasses_amount:
            # response: dict = (await self._client.get(f'https://apis.roblox.com/game-passes/v1/users/{self._player_id}/game-passes', params=params, cookies=self._cookies)).json()
            # gamepasses: dict[dict] = response.get('gamePasses', {})
            # if not gamepasses:
            #     break
            # for gamepass in gamepasses:
            #     gamepass_id = str(gamepass.get('gamePassId'))
            #     if gamepass_id in checkListGamepasses:
            #         check_list_gamepasses[checkListGamepasses[gamepass_id]['PlaceName']].append(checkListGamepasses[gamepass_id]['GamepassName'])
            #         found_gamepasses_count += 1
            # params['exclusiveStartId'] = None if len(gamepasses) < params.get('count', 100) else gamepass_id
            cur_page += 1
        return 
        
    async def get_badges(self, *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_BADGES) -> list:
        check_list_badges = {badge['PlaceName']: [] for badge in ....values()}
        check_list_badges_amount = len(check_list_badges)
        found_badges_amount = 0
        cur_page = 0
        max_page = config.get('Roblox.Cookie_Checker.Main.Badges_Max_Check_Pages', default=-1)
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while params.get('cursor') is not None and cur_page != max_page and found_badges_amount != check_list_badges_amount:
            response: dict[str, list[dict]] = (await self._session.get(f'https://badges.roblox.com/v1/users/{self._player_id}/badges', params=params, cookies=self._cookies)).json()
            for badge in response.get('data', []):
                badge_id = str(badge.get('id'))
                if badge_id in check_list_badges:
                    check_list_badges[check_list_badges[badge_id]['PlaceName']].append(check_list_badges[badge_id]['BadgeName'])
                    found_badges_amount += 1
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return 
    
    async def get_badges(self, check_list_badges: dict[int, str]): # https://badges.roblox.com/v1/users/{UserId}/badges/awarded-dates?badgeIds=
        ...
    
    async def get_favorite_places(self, check_list_favorite_places: dict[int, str], *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_FAVORITE_PLACES) -> set[int]:
        favorite_places = []
        found_favorite_places_amount = 0
        check_list_favorite_places_amount = len(...)
        cur_page = 0
        max_page = config.get('Roblox.Cookie_Checker.Main.Favorite_Places_Max_Check_Pages', default=-1)
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while params.get('cursor') is not None and cur_page != max_page and found_favorite_places_amount != check_list_favorite_places_amount:
            # response: dict = (await self._client.get(f'https://games.roblox.com/v2/users/{self._player_id}/favorite/games', params=params, cookies=self._cookies)).json()
            # for place in response.get('data', {}):
            #     place_id = str(place['rootPlace']['id'])
            #     if place_id in checkListFavoritePlaces:
            #         favorite_places.append(checkListFavoritePlaces[place_id])
            #         found_favorite_places_amount += 1
            # params['cursor'] = response['nextPageCursor']
            cur_page += 1
    
        return favorite_places
    
    async def get_places_weekly_playtime(self, check_list_places_weekly_playtime: dict[int, str]) -> dict:
        response: dict = await (await self._session.get('https://apis.roblox.com/parental-controls-api/v1/parental-controls/get-top-weekly-screentime-by-universe', cookies=self._cookies)).json()
        for place in response['universeWeeklyScreentimes']:
            universeId = str(place['universeId'])
            if universeId in checkListPlacesWeeklyPlaytime:
                placeName = checkListPlacesWeeklyPlaytime[universeId]
                placesWeeklyPlaytimeColor[placeName] = f'{placeName} ({formatDuration(int(place['weeklyMinutes']) * 60 * 1000, outUnits=['d', 'h', 'm'])}{ANSI.FG.GREEN})'
                placesWeeklyPlaytimeNoColor[placeName] = f'{placeName} ({formatDuration(int(place['weeklyMinutes']) * 60 * 1000, inColor='', outColor='', outUnits=['d', 'h', 'm'])})'
    
    async def get_bundles(self, *, items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_BUNDLES) -> set[int]:
        bundles = []
        found_bundles_amount = 0
        check_list_bundles_amount = len(...)
        cur_page = 0
        max_page = config.get('Roblox.Cookie_Checker.Main.Bundles_Max_Check_Pages', default=-1)
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while params.get('cursor') is not None and cur_page != max_page and found_bundles_amount != check_list_bundles_amount:
            # response: dict = (await self._client.get(f'https://catalog.roblox.com/v1/users/{self._player_id}/bundles/1', params=params, cookies=self._cookies)).json()
            # for bundle in response['data']:
            #     bundle_id = str(bundle['id'])
            #     if bundle_id in checkListBundles:
            #         bundles[bundle_id] = checkListBundles[bundle_id]
            #         found_bundles_amount += 1
            # params['cursor'] = response['nextPageCursor']
            cur_page += 1
    
        return {
            'bundles': list(bundles.values()),
            'korblox': '192' in bundles,
            'headless': '201' in bundles
        }
    
    async def get_inventory_privacy(self) -> str:
        response: dict = await (await self._session.get(f'https://apis.roblox.com/user-settings-api/v1/user-settings/settings-and-options', cookies=self._cookies)).json()
        who_can_see_inventory: dict = response.get('whoCanSeeMyInventory')
        return who_can_see_inventory.get('currentValue')
    
    async def get_trade_privacy(self) -> str:
        response: dict = await (await self._session.get('https://accountsettings.roblox.com/v1/trade-privacy', cookies=self._cookies)).json()
        return response.get('tradePrivacy')
    
    async def get_can_trade(self) -> bool:
        return self._account_information.get('CanTrade')
    
    async def get_sessions(self) -> int:
        sessions_amount = 0
        cur_page = 0
        max_page = config.get('Roblox.Cookie_Checker.Main.Sessions_Max_Check_Pages', default=1)
        params = {
            'nextCursor': ''
        }
        while params.get('nextCursor') is not None and cur_page != max_page:
            response = await (await self._session.get(f'https://apis.roblox.com/token-metadata-service/v1/sessions', params=params, cookies=self._cookies)).json()
            sessions_amount += len(response['sessions'])
            params['nextCursor'] = response['nextCursor']
            cur_page += 1
        return sessions_amount
    
    def get_email(self) -> Optional[dict]:
        security_model: dict = self._account_information.get('MyAccountSecurityModel', {})
        if not security_model:
            return
        return {
            'setted': security_model.get('IsEmailSet'),
            'verified': security_model.get('IsEmailVerified')
        }

    async def get_phone(self) -> Optional[bool]:
        response: dict = await (await self._session.get('https://accountinformation.roblox.com/v1/phone', cookies=self._cookies)).json()
        return response.get('phone')
    
    def get_2fa(self) -> Optional[bool]:
        security_model: dict = self._account_information.get('MyAccountSecurityModel', {})
        return security_model.get('IsTwoStepEnabled')
    
    def get_pin(self) -> Optional[bool]:
        return self._account_information.get('IsAccountPinEnabled')
    
    async def get_groups_information(self) -> list:
        groups_owned: dict = {}
        groups_members: int = 0
        params = {
            'includeLocked': True
        }
        response: dict[str, dict[dict]] = await (await self._session.get(f'https://groups.roblox.com/v1/users/{self._player_id}/groups/roles', params=params, cookies=self._cookies)).json()
        for group in response.get('data', {}):
            user_role: dict = group.get('role', {})
            if user_role.get('rank') == 255:
                group_info: dict = group.get('group')
                groups_owned[group_info.get('name')] = group_info.get('id')
                groups_members += group_info.get('memberCount')
    
        groups_pending, groups_funds = await asyncio.gather(
            self.get_groups_pending(groups_owned),
            self.get_groups_funds(groups_owned)
        )
        return {
            'owned': groups_owned,
            'members': groups_members,
            'pending': groups_pending,
            'funds': groups_funds
        }
    
    async def get_groups_pending(self, groups_ids: set[int]) -> int:
        groups_pending = 0
        if groups_ids:
            for group_id in groups_ids:
                response: dict = await (await self._session.get(f'https://apis.roblox.com/transaction-records/v1/groups/{group_id}/revenue/summary/year', cookies=self._cookies)).json()
                groups_pending += response.get('pendingRobux')
        return groups_pending
    
    async def get_groups_funds(self, groups_ids: set[int]) -> int:
        groups_funds = 0
        if groups_ids:
            for group_id in groups_ids:
                response: dict = await (await self._session.get(f'https://economy.roblox.com/v1/groups/{group_id}/currency', cookies=self._cookies)).json()
                groups_funds += response.get('robux')
        return groups_funds
    
    def get_place_visits(self, data: dict[str, dict[str, dict[str, int]]]) -> Optional[int]:
        return data.get('components', {}).get('Statistics', {}).get('numberOfVisits')
    
    async def get_age_group(self) -> dict[str, Optional[dict]] | Literal['UNK']:
        response: dict = await (await self._session.get('https://apis.roblox.com/user-settings-api/v1/account-insights/age-group', cookies=self._cookies)).json()
        return convert_age_group(response.get('ageGroupTranslationKey', ''))
    
    async def get_verified_age(self) -> Optional[bool]:
        response: dict = await (await self._session.get('https://apis.roblox.com/age-verification-service/v1/age-verification/verified-age', cookies=self._cookies)).json()
        return response.get('isVerified')
    
    async def get_verified_voice(self) -> Optional[bool]:
        response: dict = await (await self._session.get('https://voice.roblox.com/v1/settings', cookies=self._cookies)).json()
        return response.get('isVerifiedForVoice')
    
    def get_fff_counter(self, data: dict[str, dict[str, dict[str, dict[str, int]]]], *, key: Literal['friends', 'followers', 'followings']) -> Optional[int]:
        return data.get('components', {}).get('UserProfileHeader', {}).get('counts', {}).get(f'{key}Count')

    async def get_roblox_badges(self, data: dict) -> list[str]:
        return [robloxBadge['type']['value'] for robloxBadge in data['components']['RobloxBadges']['robloxBadgeList']]


    async def get_x_csrf_token(self) -> Optional[str]:
        response: dict = (await self._session.post('https://auth.roblox.com/v2/logout', cookies=self._cookies)).headers
        return response.get('X-CSRF-Token')

    async def get_auth_ticket(self, x_csrf_token: str) -> Optional[str]:
        headers = { 'X-CSRF-Token': x_csrf_token }
        response: dict = (await self._session.post('https://auth.roblox.com/v1/authentication-ticket', headers=headers)).headers
        return response.get('rbx-authentication-ticket')
    
    async def break_cookie(self, x_csrf_token: str) -> None:
        headers = {
            'X-CSRF-Token': x_csrf_token,
            'Set-Cookie': '.ROBLOSECURITY=; Max-Age=0; Path=/;'
        }
        await self._session.post('https://auth.roblox.com/v2/logout', headers=headers, cookies=self._cookies)
    
    async def generate_new_cookie(self, auth_ticket: str) -> str:
        headers = { 'RBXauthenticationNegotiation': '1' }
        data = { 'authenticationTicket': auth_ticket }
        response = (await self._session.post('https://auth.roblox.com/v1/authentication-ticket/redeem', data=data, headers=headers)).headers
        new_cookie = re.search(ROBLOX_COOKIE_PATTERN, str(response))
        if not new_cookie:
            raise InvalidCookie
        return new_cookie.group(0).rstrip(';')
    
    async def is_achieved_badge(self, badge_id: int) -> bool:
        return bool(await self._session.get(f'https://badges.roblox.com/v1/users/{self._player_id}/badges/{badge_id}/awarded-date'))

    async def get_place_id_user_in(self) -> Optional[int]:
        data = { 'userIds': [self._player_id] }
        response: dict = await (await self._session.post('https://presence.roblox.com/v1/presence/users', data=data)).json()
        user_presences: dict = response.get('userPresences', [{}])[0]
        return user_presences.get('placeId')

    async def get_place_server_ids(
        self,
        place_id: str,
        *,
        less_players: bool = True,
        exclude_full: bool = True,
        only_friends: bool = False,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_PLACE_SERVER_IDS
    ) -> dict:
        params = {
            'sortOrder': int(less_players),
            'excludeFullGames': exclude_full,
            'limit': items_per_page
        }
        return await (await self._session.get(f'https://games.roblox.com/v1/games/{place_id}/servers/{int(only_friends)}', params=params)).json()
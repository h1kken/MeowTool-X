from copy import deepcopy
import re
import asyncio
from typing import Literal, Optional
from aiohttp import ClientResponse
from src.services.roblox.http.client import RobloxHttpClient
from src.exceptions.roblox import InvalidCookie
from utils.regex import ROBLOX_COOKIE_PATTERN
from utils.time import format_duration
from utils.date import convert_date
from utils.string import convert_age_group
from utils.other import chunks_generator
from src.utils.consts import (
    COUNTRY_CODES,
    ROBLOX_REG_DATE_FORMAT,
    TIME_FRAME_TRANSACTIONS,
    ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME,
    ITEMS_PER_PAGE_RAP,
    ITEMS_PER_PAGE_GAMEPASSES,
    ITEMS_PER_PAGE_FAVORITE_PLACES,
    ITEMS_PER_PAGE_BUNDLES,
    ITEMS_PER_PAGE_PLACE_SERVER_IDS,
    BADGES_COUNT_LIMIT
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
        self._player_id: Optional[int] = self._account_information.get('UserId')
        # self._player_name: Optional[str] = self._account_information.get('Name')
        self.data = {}

    @property
    def cookie(self) -> str:
        return (self._cookies or {}).get('.ROBLOSECURITY')

    # async def get_simple_account_information(self) -> dict:
    #     return await (await self._session.get('https://users.roblox.com/v1/users/authenticated', cookies=self._cookies)).json()

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
    
    async def get_link(self) -> dict:
        return {'Link': f'https://www.roblox.com/users/{self._player_id}'}
    
    async def get_user_id(self) -> dict:
        return {'ID': self._account_information.get('UserId')}
    
    async def get_name(self) -> dict:
        return {'Name': self._account_information.get('Name')}
    
    async def get_display_name(self) -> dict:
        return {'Display Name': self._account_information.get('DisplayName')}
    
    async def get_country_reg(self) -> dict:
        response: dict = await (await self._session.get('https://users.roblox.com/v1/users/authenticated/country-code')).json()
        country_code = response.get('countryCode')
        return {
            'Country Registration': {
                'code': country_code,
                'name': COUNTRY_CODES.get(country_code)
            }
        }
    
    async def get_reg_date_dmy(self) -> dict:
        response: dict = await (await self._session.get(f'https://users.roblox.com/v1/users/{self._player_id}')).json()
        return {'Registration Date (DMY)': convert_date(response.get('created'), ROBLOX_REG_DATE_FORMAT)}

    async def get_reg_date_in_days(self) -> dict:
        return {'Registration Date (In Days)': self._account_information.get('AccountAgeInDays')}

    async def get_robux(self) -> int:
        response: dict = await (await self._session.get(f'https://economy.roblox.com/v1/users/{self._player_id}/currency')).json()
        return {'Robux': response.get('robux')}
    
    async def get_billing(self) -> int:
        response: dict = await (await self._session.get('https://billing.roblox.com/v1/credit')).json()
        return {'Billing': response.get('robuxAmount')}
    
    async def get_transactions_time_frame(self, *, time_frame: Literal['Day', 'Week', 'Month', 'Year'] = TIME_FRAME_TRANSACTIONS) -> dict:
        params = {
            'timeFrame': time_frame,
            'transactionType': 'Summary'
        }
        response: dict = await (await self._session.get(f'https://economy.roblox.com/v2/users/{self._player_id}/transaction-totals', params=params)).json()
        return {
            f'Pending (1 {time_frame})': response.get('pendingRobuxTotal'),
            f'Donate (1 {time_frame})': abs(response.get('outgoingRobuxTotal'))
        }
        
    # async def get_transactions_all_time(
    #     self,
    #     check_list_custom_gamepasses: dict[str, int],
    #     max_page_donate_all_time: int,
    #     max_page_custom_gamepasses: int,
    #     *,
    #     items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME
    # ) -> dict:
    #     donate_all_time = 0
    #     found_custom_gamepasses = deepcopy(check_list_custom_gamepasses)
    #     max_page = max(max_page_donate_all_time, max_page_custom_gamepasses)
    #     cur_page = 0
    #     params = {
    #         'transactionType': 'Purchase',
    #         'limit': items_per_page,
    #         'cursor': ''
    #     }
    #     while params.get('cursor') is not None and cur_page != max_page:
    #         response: dict = (await self._session.get(f'https://economy.roblox.com/v2/users/{self._player_id}/transactions', params=params, cookies=self._cookies)).json()
    #         for transaction in response.get('data', []):
    #             if config.get('Roblox.Cookie_Checker.Main.Donate_All_Time') and (max_page_donate_all_time == -1 or cur_page < max_page_donate_all_time):
    #                 donate_all_time += transaction.get('currency', {}).get('amount', 0)
    #             if config.get('Roblox.Cookie_Checker.Main.Custom_Gamepasses') and 'name' in transaction['details'] and transaction['details']['name'] in ... and (max_page_custom_gamepasses == -1 or cur_page < max_page_custom_gamepasses):
    #                 check_list_custom_gamepasses[transaction['details']['name']] += 1
    #         params['cursor'] = response.get('nextPageCursor')
    #         cur_page += 1
            
    #     return {
    #         'donate_all_time': abs(donate_all_time),
    #         'custom_gamepasses': check_list_custom_gamepasses
    #     }
    
    async def get_rap(
        self,
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_RAP
    ) -> dict[str, int]:
        rap = 0
        cur_page = 0
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while (
            params.get('cursor') is not None
            and cur_page != max_page
        ):
            response: dict[str, list[dict]] = (await self._session.get(f'https://inventory.roblox.com/v1/users/{self._player_id}/assets/collectibles', params=params, cookies=self._cookies)).json()
            rap += sum(
                item['recentAveragePrice']
                for item in response.get('data', [])
                if isinstance(item.get('recentAveragePrice'), int)
            )
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Rap': rap}
    
    async def get_cards(self) -> dict: # TODO
        response: dict = await (await self._session.get(f'https://apis.roblox.com/payments-gateway/v1/payment-profiles', cookies=self._cookies)).json()
        return {'Cards': len(response)}
    
    async def get_premium(self) -> dict:
        return {'Premium': self._account_information.get('IsPremium')}
    
    async def get_gamepasses(
        self,
        found_gamepasses_template: dict[int, dict],
        check_list_gamepasses: dict[int, dict],
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_GAMEPASSES
    ) -> list:
        found_gamepasses = deepcopy(found_gamepasses_template)
        cur_page = 0
        params = {
            'count': items_per_page,
            'exclusiveStartId': ''
        }
        while (
            params['exclusiveStartId'] is not None
            and cur_page != max_page
            and len(found_gamepasses) != len(check_list_gamepasses)
        ):
            response: dict = (await self._session.get(f'https://apis.roblox.com/game-passes/v1/users/{self._player_id}/game-passes', params=params, cookies=self._cookies)).json()
            gamepasses = response.get('gamePasses', [])
            for gamepass in gamepasses:
                gamepass_id = gamepass.get('gamePassId')
                if gamepass_id in check_list_gamepasses:
                    gamepass_data = check_list_gamepasses[gamepass_id]
                    found_gamepasses[gamepass_data['placeId']]['data'][gamepass_id] = {gamepass_data['gamepassName']}
            params['exclusiveStartId'] = gamepass_id if len(gamepasses) >= params['count'] else None
            cur_page += 1
        return {'Gamepasses': found_gamepasses}
    
    async def get_badges(
        self,
        found_badges_template: dict[int, dict],
        check_list_badges: dict[int, dict],
    ) -> list:
        found_badges = deepcopy(found_badges_template)
        tasks = [
            self._session.get(f'https://badges.roblox.com/v1/users/{self._player_id}/badges/awarded-dates', params={'badgeIds': ','.join(chunk)}, cookies=self._cookies)
            for chunk in chunks_generator(list(check_list_badges.keys()), BADGES_COUNT_LIMIT)
        ]
        results: list[ClientResponse] = await asyncio.gather(*tasks)
        for result in results:
            response: dict = result.json()
            badges = response.get('data', [])
            for badge in badges:
                badge_id = badge.get('badgeId')
                if badge_id in check_list_badges:
                    badge_data = check_list_badges[badge_id]
                    found_badges[badge_data['placeId']]['data'][badge_id] = {badge_data['badgeName']}
        return {'Badges': found_badges}
    
    async def get_favorite_places(
        self,
        check_list_favorite_places: dict[int, str],
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_FAVORITE_PLACES
    ) -> dict:
        found_favorite_places = {}
        cur_page = 0
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while (
            params['cursor'] is not None
            and cur_page != max_page
            and len(found_favorite_places) != len(check_list_favorite_places)
        ):
            response: dict = (await self._session.get(f'https://games.roblox.com/v2/users/{self._player_id}/favorite/games', params=params, cookies=self._cookies)).json()
            for place in response.get('data', []):
                place_id = place.get('rootPlace', {}).get('id')
                if place_id in check_list_favorite_places:
                    found_favorite_places[place_id] = check_list_favorite_places[place_id]
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Favorite Places': found_favorite_places}
    
    async def get_places_weekly_playtime(
        self,
        check_list_places_weekly_playtime: dict[int, str]
    ) -> dict:
        found_places_weekly_playtime = {}
        response: dict = await (await self._session.get('https://apis.roblox.com/parental-controls-api/v1/parental-controls/get-top-weekly-screentime-by-universe', cookies=self._cookies)).json()
        for universe in response.get('universeWeeklyScreentimes', []):
            universe_id = universe.get('universeId')
            if universe_id in check_list_places_weekly_playtime:
                found_places_weekly_playtime[universe_id] = {check_list_places_weekly_playtime[universe_id]: format_duration(universe.get('weeklyMinutes') * 60 * 1000, out_units=set('d', 'h', 'm'))}
        return {'Places Weekly Playtime': found_places_weekly_playtime}
    
    async def get_bundles(
        self,
        check_list_bundles: dict[int, str],
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_BUNDLES
    ) -> dict[str, dict[int, str]]:
        found_bundles = {}
        cur_page = 0
        params = {
            'limit': items_per_page,
            'cursor': ''
        }
        while (
            params['cursor'] is not None
            and cur_page != max_page
            and len(found_bundles) != len(check_list_bundles)
        ):
            response: dict = (await self._session.get(f'https://catalog.roblox.com/v1/users/{self._player_id}/bundles/1', params=params, cookies=self._cookies)).json()
            for bundle in response.get('data', []):
                bundle_id = bundle.get('id')
                if bundle_id in check_list_bundles:
                    found_bundles[bundle_id] = check_list_bundles[bundle_id]
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Bundles': found_bundles}
    
    async def get_inventory_privacy(self) -> dict[str, str]:
        response: dict = await (await self._session.get(f'https://apis.roblox.com/user-settings-api/v1/user-settings/settings-and-options', cookies=self._cookies)).json()
        return {'Inventory Privacy': response.get('whoCanSeeMyInventory', {}).get('currentValue')}
    
    async def get_trade_privacy(self) -> dict[str, str]:
        response: dict = await (await self._session.get('https://accountsettings.roblox.com/v1/trade-privacy', cookies=self._cookies)).json()
        return {'Trade Privacy': response.get('tradePrivacy')}
    
    async def get_can_trade(self) -> dict[str, bool]:
        return {'Can Trade': self._account_information.get('CanTrade')}
    
    async def get_sessions(
        self,
        *,
        max_page: int = 1
    ) -> dict[str, list[dict]]:
        sessions = []
        cur_page = 0
        params = {
            'nextCursor': ''
        }
        while (
            params['nextCursor'] is not None
            and cur_page != max_page
        ):
            response: dict = await (await self._session.get(f'https://apis.roblox.com/token-metadata-service/v1/sessions', params=params, cookies=self._cookies)).json()
            for session in response.get('sessions', []):
                sessions.append(
                    {
                        'location': session.get('location', {}),
                        'agent': session.get('agent', {}),
                        'ip': session.get('lastAccessedIp')
                    }
                )
            params['nextCursor'] = response.get('nextCursor') if response.get('hasMore') else None
            cur_page += 1
        return {'Sessions': sessions}
    
    async def get_email(self) -> Optional[dict]:
        security_model: dict = self._account_information.get('MyAccountSecurityModel', {})
        return {
            'Email': {
                'setted': security_model.get('IsEmailSet'),
                'verified': security_model.get('IsEmailVerified')
            }
        }

    async def get_phone(self) -> dict[str, bool]: # TODO
        response: dict = await (await self._session.get('https://accountinformation.roblox.com/v1/phone', cookies=self._cookies)).json()
        return {'Phone': response.get('phone')}
    
    async def get_2fa(self) -> dict[str, bool]:
        return {'2FA': self._account_information.get('MyAccountSecurityModel', {}).get('IsTwoStepEnabled')}
    
    async def get_pin(self) -> dict[str, bool]:
        return {'Pin': self._account_information.get('IsAccountPinEnabled')}
    
    async def get_groups_information(self) -> list: # TODO
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
    
    async def get_groups_pending(self, groups_ids: set[int]) -> int: # TODO
        groups_pending = 0
        if groups_ids:
            for group_id in groups_ids:
                response: dict = await (await self._session.get(f'https://apis.roblox.com/transaction-records/v1/groups/{group_id}/revenue/summary/year', cookies=self._cookies)).json()
                groups_pending += response.get('pendingRobux')
        return groups_pending
    
    async def get_groups_funds(self, groups_ids: set[int]) -> int: # TODO
        groups_funds = 0
        if groups_ids:
            for group_id in groups_ids:
                response: dict = await (await self._session.get(f'https://economy.roblox.com/v1/groups/{group_id}/currency', cookies=self._cookies)).json()
                groups_funds += response.get('robux')
        return groups_funds
    
    async def get_place_visits(self, data: dict) -> dict:
        return {'Place Visits': data.get('components', {}).get('Statistics', {}).get('numberOfVisits')}
    
    async def get_age_group(self) -> dict:
        response: dict = await (await self._session.get('https://apis.roblox.com/user-settings-api/v1/account-insights/age-group', cookies=self._cookies)).json()
        return {'Age Group': convert_age_group(response.get('ageGroupTranslationKey', ''))}
    
    async def get_verified_age(self) -> dict:
        response: dict = await (await self._session.get('https://apis.roblox.com/age-verification-service/v1/age-verification/verified-age', cookies=self._cookies)).json()
        return {'Verified Age': response.get('verifiedAge')}
    
    async def get_verified_voice(self) -> dict:
        response: dict = await (await self._session.get('https://voice.roblox.com/v1/settings', cookies=self._cookies)).json()
        return {'Verified Voice': response.get('isVerifiedForVoice')}
    
    async def get_fff_counter(self, data: dict, *, key: Literal['friends', 'followers', 'followings']) -> dict:
        return {key.capitalize(): data.get('components', {}).get('UserProfileHeader', {}).get('counts', {}).get(f'{key}Count')}

    async def get_roblox_badges(self, data: dict) -> dict:
        return {
            'Roblox Badges': [
                robloxBadge['type']['value']
                for robloxBadge in data.get('components', {}).get('RobloxBadges', {}).get('robloxBadgeList')
            ]
        }


    # advanced getters
    async def get_x_csrf_token(self) -> Optional[str]:
        response: dict = (await self._session.post('https://auth.roblox.com/v2/logout', cookies=self._cookies)).headers
        return response.get('X-CSRF-Token')

    async def get_auth_ticket(self, x_csrf_token: str) -> Optional[str]:
        headers = {
            'X-CSRF-Token': x_csrf_token
        }
        response: dict = (await self._session.post('https://auth.roblox.com/v1/authentication-ticket', headers=headers)).headers
        return response.get('rbx-authentication-ticket')
    
    async def break_cookie(self, x_csrf_token: str) -> None:
        headers = {
            'X-CSRF-Token': x_csrf_token,
            'Set-Cookie': '.ROBLOSECURITY=; Max-Age=0; Path=/;'
        }
        await self._session.post('https://auth.roblox.com/v2/logout', headers=headers, cookies=self._cookies)
    
    async def generate_new_cookie(self, auth_ticket: str) -> str:
        data = {
            'authenticationTicket': auth_ticket
        }
        headers = {
            'RBXauthenticationNegotiation': '1'
        }
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
            'limit': items_per_page,
            'excludeFullGames': exclude_full
        }
        return await (await self._session.get(f'https://games.roblox.com/v1/games/{place_id}/servers/{int(only_friends)}', params=params)).json()
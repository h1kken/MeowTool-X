import asyncio
import re
from typing import Collection, Literal, cast

from aiohttp import ClientResponse

import src.services.roblox.apis as RobloxAPI
from src.exceptions.roblox import InvalidCookie
from src.services.roblox.constants import (
    BADGES_COUNT_LIMIT,
    COUNTRY_CODES_KEYMAP,
    ITEMS_PER_PAGE_BUNDLES,
    ITEMS_PER_PAGE_FAVORITE_PLACES,
    ITEMS_PER_PAGE_GAMEPASSES,
    ITEMS_PER_PAGE_PLACE_SERVER_IDS,
    ITEMS_PER_PAGE_RAP,
    ROBLOX_REG_DATE_FORMAT,
    TIME_FRAME_TRANSACTIONS,
)
from src.services.roblox.http.client import RobloxHttpClient
from src.services.roblox.regexes import ROBLOX_COOKIE_PATTERN
from src.services.roblox.text import convert_age_group
from src.services.roblox.types import (
    JsonDict,
    JsonList,
    NamedIdMap,
    PlaceDataMap,
    SessionEntry,
)
from src.utils.constants.datetime import DATE_TIME_FORMAT
from src.utils.datetime import (
    convert_datetime,
    format_duration,
    timestamp_to_local_date,
)
from src.utils.generators import chunked


class RobloxAccount:
    def __init__(
        self,
        session: RobloxHttpClient,
        cookies: dict[str, str] | None = None,
        account_information: JsonDict | None = None
    ) -> None:
        self._session = session
        self._cookies = cookies
        self._account_information: JsonDict = account_information or {}
        self._player_id: int | None = self._account_information.get('UserId')
        # self._player_name: str | None = self._account_information.get('Name')
        self.data: JsonDict = {}

    @property
    def cookie(self) -> str | None:
        return (self._cookies or {}).get('.ROBLOSECURITY')

    # async def get_simple_account_information(self) -> dict:
    #     return await (await self._session.get('https://users.roblox.com/v1/users/authenticated', cookies=self._cookies)).json()

    async def get_complex_account_information(self) -> JsonDict:
        return cast(JsonDict, await (await self._session.get(RobloxAPI.MYSETTINGSJSON)).json())

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
    ) -> JsonDict:
        json: JsonDict = {
            'components': [{'component': component} for component in components],
            'includeComponentOrdering': True,
            'profileId': str(self._player_id),
            'profileType': 'User'
        }
        return cast(
            JsonDict,
            await (await self._session.post(f'{RobloxAPI.APIS}/profile-platform-api/v1/profiles/get', json=json)).json(),
        )
    
    async def get_link(self) -> JsonDict:
        return {'Link': f'https://www.roblox.com/users/{self._player_id}'}
    
    async def get_user_id(self) -> JsonDict:
        return {'ID': self._account_information.get('UserId')}
    
    async def get_name(self) -> JsonDict:
        return {'Name': self._account_information.get('Name')}
    
    async def get_display_name(self) -> JsonDict:
        return {'Display Name': self._account_information.get('DisplayName')}
    
    async def get_country_reg(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.USERS}/v1/users/authenticated/country-code')).json(),
        )
        country_code = response.get('countryCode')
        country_name = COUNTRY_CODES_KEYMAP.get(country_code) if isinstance(country_code, str) else None
        return {
            'Country Registration': {
                'code': country_code,
                'name': country_name,
            }
        }
    
    async def get_reg_date_dmy(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.USERS}/v1/users/{self._player_id}')).json(),
        )
        return {'Registration Date (DMY)': convert_datetime(response.get('created'), ROBLOX_REG_DATE_FORMAT)}

    async def get_reg_date_in_days(self) -> JsonDict:
        return {'Registration Date (In Days)': self._account_information.get('AccountAgeInDays')}

    async def get_robux(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.ECONOMY}/v1/user/currency')).json(),
        )
        return {'Robux': response.get('robux')}
    
    async def get_billing(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.BILLING}/v1/credit')).json(),
        )
        return {'Billing': response.get('robuxAmount')}
    
    async def get_transactions_time_frame(
        self,
        *,
        time_frame: Literal['Day', 'Week', 'Month', 'Year'] = TIME_FRAME_TRANSACTIONS,
    ) -> JsonDict:
        params: JsonDict = {
            'timeFrame': time_frame,
            'transactionType': 'Summary'
        }
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.ECONOMY}/v2/users/{self._player_id}/transaction-totals', params=params)).json(),
        )
        outgoing_total = response.get('outgoingRobuxTotal')
        return {
            f'Pending (1 {time_frame})': response.get('pendingRobuxTotal'),
            f'Donate (1 {time_frame})': abs(outgoing_total) if isinstance(outgoing_total, (int, float)) else 0,
        }
        
    # TODO
    # async def get_transactions_all_time(
    #     self,
    #     check_list_custom_gamepasses: Collection[str],
    #     max_page_donate_all_time: int = -1,
    #     max_page_custom_gamepasses: int = -1,
    #     *,
    #     items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_TRANSACTIONS_ALL_TIME
    # ) -> dict:
    #     is_check_donate_all_time = config.get('Roblox>Cookie Checker>Main>Donate (All Time)')
    #     is_check_custom_gamepasses = config.get('Roblox>Cookie Checker>Main>Custom Gamepasses')
    #     donate_all_time = 0
    #     found_custom_gamepasses = {name: 0 for name in check_list_custom_gamepasses}
    #     max_page = max(max_page_donate_all_time, max_page_custom_gamepasses)
    #     cur_page = 0
    #     params = {
    #         'transactionType': 'Purchase',
    #         'limit': items_per_page,
    #         'cursor': ''
    #     }
    #     while params['cursor'] is not None and cur_page != max_page:
    #         response: dict = (await self._session.get(f'{RobloxAPI.ECONOMY}/v2/users/{self._player_id}/transactions', params=params, cookies=self._cookies)).json()
    #         for transaction in response.get('data', []):
    #             if (
    #                 is_check_donate_all_time
    #                 and (max_page_donate_all_time == -1 or cur_page < max_page_donate_all_time)
    #             ):
    #                 donate_all_time += transaction.get('currency', {}).get('amount', 0)

    #             if (
    #                 is_check_custom_gamepasses
    #                 and transaction.get('details', {}).get('name') in found_custom_gamepasses
    #                 and (max_page_custom_gamepasses == -1 or cur_page < max_page_custom_gamepasses)
    #             ):
    #                 check_list_custom_gamepasses[transaction['details']['name']] += 1
    #         params['cursor'] = response.get('nextPageCursor')
    #         cur_page += 1
            
    #     return {
    #         'Donate (All Time)': abs(donate_all_time),
    #         'Custom Gamepasses': check_list_custom_gamepasses
    #     }
    
    async def get_rap(
        self,
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_RAP
    ) -> dict[str, int]:
        rap = 0
        cur_page = 0
        params: dict[str, int | str | None] = {
            'limit': items_per_page,
            'cursor': '',
        }
        while (
            params.get('cursor') is not None
            and cur_page != max_page
        ):
            response = cast(
                JsonDict,
                await (await self._session.get(f'{RobloxAPI.INVENTORY}/v1/users/{self._player_id}/assets/collectibles', params=params, cookies=self._cookies)).json(),
            )
            items = cast(JsonList, response.get('data') or [])
            rap += sum(
                item['recentAveragePrice']
                for item in items
                if isinstance(item.get('recentAveragePrice'), int)
            )
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Rap': rap}
    
    async def get_cards(self) -> JsonDict:
        response = cast(
            JsonList,
            await (await self._session.get(f'{RobloxAPI.APIS}/payments-gateway/v1/payment-profiles', cookies=self._cookies)).json(),
        )
        cards: JsonList = []
        for card in response:
            last_purchase_date = card.get('lastChargeTime')
            cards.append({
                'lastPurchaseDate': timestamp_to_local_date(last_purchase_date, DATE_TIME_FORMAT) if last_purchase_date else None,
                'cardNetwork': card.get('CardNetwork'),
                'last4Digits': card.get('Last4Digits'),
                'expMonth': card.get('ExpMonth'),
                'expYear': card.get('ExpYear'),
                'paymentType': card.get('paymentProfileType')
            })
        return {'Cards': cards}
    
    async def get_premium(self) -> JsonDict:
        return {'Premium': self._account_information.get('IsPremium')}
    
    async def get_gamepasses(
        self,
        check_list_places: Collection[str],
        check_list_gamepasses: dict[int, JsonDict],
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_GAMEPASSES
    ) -> JsonDict:
        found_gamepasses: PlaceDataMap = {place: {'data': {}} for place in check_list_places}
        cur_page = 0
        params: dict[str, int | str | None] = {
            'count': items_per_page,
            'exclusiveStartId': '',
        }
        while (
            params['exclusiveStartId'] is not None
            and cur_page != max_page
            and len(found_gamepasses) != len(check_list_gamepasses)
        ):
            response = cast(
                JsonDict,
                await (await self._session.get(f'{RobloxAPI.APIS}/game-passes/v1/users/{self._player_id}/game-passes', params=params, cookies=self._cookies)).json(),
            )
            gamepasses = cast(JsonList, response.get('gamePasses') or [])
            last_gamepass_id: int | None = None
            for gamepass in gamepasses:
                gamepass_id = gamepass.get('gamePassId')
                if not isinstance(gamepass_id, int):
                    continue
                last_gamepass_id = gamepass_id
                gamepass_data = check_list_gamepasses.get(gamepass_id)
                if gamepass_data:
                    place_id = gamepass_data.get('placeId')
                    gamepass_name = gamepass_data.get('gamepassName')
                    if not isinstance(place_id, str) or not isinstance(gamepass_name, str):
                        continue
                    place_bucket = found_gamepasses.setdefault(place_id, {'data': {}})
                    place_bucket['data'][gamepass_id] = gamepass_name
            params['exclusiveStartId'] = last_gamepass_id if len(gamepasses) >= items_per_page else None
            cur_page += 1
        return {'Gamepasses': found_gamepasses}
    
    async def get_badges(
        self,
        check_list_places: Collection[str],
        check_list_badges: dict[int, JsonDict],
    ) -> JsonDict:
        found_badges: PlaceDataMap = {place: {'data': {}} for place in check_list_places}
        tasks = [
            self._session.get(
                f'{RobloxAPI.BADGES}/v1/users/{self._player_id}/badges/awarded-dates',
                params={'badgeIds': ','.join(str(badge_id) for badge_id in chunk)},
                cookies=self._cookies
            )
            for chunk in chunked(list(check_list_badges.keys()), BADGES_COUNT_LIMIT)
        ]
        results: list[ClientResponse] = await asyncio.gather(*tasks)
        for result in results:
            response = cast(JsonDict, await result.json())
            badges = cast(JsonList, response.get('data') or [])
            for badge in badges:
                badge_id = badge.get('badgeId')
                if not isinstance(badge_id, int) or badge_id not in check_list_badges:
                    continue
                badge_data = check_list_badges[badge_id]
                place_id = badge_data.get('placeId')
                badge_name = badge_data.get('badgeName')
                if not isinstance(place_id, str) or not isinstance(badge_name, str):
                    continue
                place_bucket = found_badges.setdefault(place_id, {'data': {}})
                place_bucket['data'][badge_id] = badge_name
        return {'Badges': found_badges}
    
    async def get_favorite_places(
        self,
        check_list_favorite_places: NamedIdMap,
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_FAVORITE_PLACES
    ) -> dict[str, NamedIdMap]:
        found_favorite_places: NamedIdMap = {}
        cur_page = 0
        params: dict[str, int | str | None] = {
            'limit': items_per_page,
            'cursor': '',
        }
        while (
            params['cursor'] is not None
            and cur_page != max_page
            and len(found_favorite_places) != len(check_list_favorite_places)
        ):
            response = cast(
                JsonDict,
                await (await self._session.get(f'{RobloxAPI.GAMES}/v2/users/{self._player_id}/favorite/games', params=params, cookies=self._cookies)).json(),
            )
            places = cast(JsonList, response.get('data') or [])
            for place in places:
                root_place = cast(JsonDict, place.get('rootPlace') or {})
                place_id = root_place.get('id')
                if place_id in check_list_favorite_places:
                    assert isinstance(place_id, int)
                    found_favorite_places[place_id] = check_list_favorite_places[place_id]
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Favorite Places': found_favorite_places}
    
    async def get_places_weekly_playtime(
        self,
        check_list_places_weekly_playtime: NamedIdMap
    ) -> JsonDict:
        found_places_weekly_playtime: dict[int, dict[str, dict[str, int]]] = {}
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.APIS}/parental-controls-api/v1/parental-controls/get-top-weekly-screentime-by-universe', cookies=self._cookies)).json(),
        )
        universes = cast(JsonList, response.get('universeWeeklyScreentimes') or [])
        for universe in universes:
            universe_id = universe.get('universeId')
            if universe_id in check_list_places_weekly_playtime:
                assert isinstance(universe_id, int)
                weekly_minutes = universe.get('weeklyMinutes')
                duration = format_duration(
                    int(weekly_minutes) * 60 * 1000,
                    out_units={'d', 'h', 'm'},
                ) if isinstance(weekly_minutes, (int, float)) else format_duration(0, out_units={'d', 'h', 'm'})
                found_places_weekly_playtime[universe_id] = {
                    check_list_places_weekly_playtime[universe_id]:
                    duration,
                }
        return {'Places Weekly Playtime': found_places_weekly_playtime}
    
    async def get_bundles(
        self,
        check_list_bundles: NamedIdMap,
        *,
        max_page: int = -1,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_BUNDLES
    ) -> dict[str, NamedIdMap]:
        found_bundles: NamedIdMap = {}
        cur_page = 0
        params: dict[str, int | str | None] = {
            'limit': items_per_page,
            'cursor': '',
        }
        while (
            params['cursor'] is not None
            and cur_page != max_page
            and len(found_bundles) != len(check_list_bundles)
        ):
            response = cast(
                JsonDict,
                await (await self._session.get(f'{RobloxAPI.CATALOG}/v1/users/{self._player_id}/bundles/1', params=params, cookies=self._cookies)).json(),
            )
            bundles = cast(JsonList, response.get('data') or [])
            for bundle in bundles:
                bundle_id = bundle.get('id')
                if isinstance(bundle_id, int) and bundle_id in check_list_bundles:
                    found_bundles[bundle_id] = check_list_bundles[bundle_id]
            params['cursor'] = response.get('nextPageCursor')
            cur_page += 1
        return {'Bundles': found_bundles}
    
    async def get_inventory_privacy(self) -> dict[str, str]:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.APIS}/user-settings-api/v1/user-settings/settings-and-options', cookies=self._cookies)).json(),
        )
        privacy_data = cast(JsonDict, response.get('whoCanSeeMyInventory') or {})
        privacy = privacy_data.get('currentValue')
        return {'Inventory Privacy': privacy if isinstance(privacy, str) else ''}
    
    async def get_trade_privacy(self) -> dict[str, str]:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.ACCOUNTSETTINGS}/v1/trade-privacy', cookies=self._cookies)).json(),
        )
        privacy = response.get('tradePrivacy')
        return {'Trade Privacy': privacy if isinstance(privacy, str) else ''}
    
    async def get_can_trade(self) -> dict[str, bool]:
        return {'Can Trade': bool(self._account_information.get('CanTrade'))}
    
    async def get_sessions(
        self,
        *,
        max_page: int = 1
    ) -> dict[str, list[SessionEntry]]:
        sessions: list[SessionEntry] = []
        cur_page = 0
        params: dict[str, str | None] = {
            'nextCursor': '',
        }
        while (
            params['nextCursor'] is not None
            and cur_page != max_page
        ):
            response = cast(
                JsonDict,
                await (await self._session.get(f'{RobloxAPI.APIS}/token-metadata-service/v1/sessions', params=params, cookies=self._cookies)).json(),
            )
            raw_sessions = cast(JsonList, response.get('sessions') or [])
            for session in raw_sessions:
                sessions.append(
                    {
                        'location': cast(JsonDict, session.get('location') or {}),
                        'agent': cast(JsonDict, session.get('agent') or {}),
                        'ip': session.get('lastAccessedIp')
                    }
                )
            next_cursor = response.get('nextCursor')
            params['nextCursor'] = next_cursor if response.get('hasMore') and isinstance(next_cursor, str) else None
            cur_page += 1
        return {'Sessions': sessions}
    
    async def get_email(self) -> JsonDict:
        security_model = cast(JsonDict, self._account_information.get('MyAccountSecurityModel') or {})
        return {
            'Email': {
                'setted': security_model.get('IsEmailSet'),
                'verified': security_model.get('IsEmailVerified')
            }
        }

    async def get_verified_phone(self) -> dict[str, bool]:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.ACCOUNTINFORMATION}/v1/phone', cookies=self._cookies)).json(),
        )
        return {'Phone': bool(response.get('isVerified'))}
    
    async def get_2fa(self) -> dict[str, bool]:
        security_model = cast(JsonDict, self._account_information.get('MyAccountSecurityModel') or {})
        return {'2FA': bool(security_model.get('IsTwoStepEnabled'))}
    
    async def get_pin(self) -> dict[str, bool]:
        return {'Pin': bool(self._account_information.get('IsAccountPinEnabled'))}
    
    # TODO
    # async def get_groups_information(self) -> list:
    #     groups_owned: dict = {}
    #     groups_members: int = 0
    #     params = {
    #         'includeLocked': True
    #     }
    #     response: dict[str, dict[dict]] = await (await self._session.get(f'{RobloxAPI.GROUPS}/v1/users/{self._player_id}/groups/roles', params=params, cookies=self._cookies)).json()
    #     for group in response.get('data', {}):
    #         user_role: dict = group.get('role', {})
    #         if user_role.get('rank') == 255:
    #             group_info: dict = group.get('group')
    #             groups_owned[group_info.get('name')] = group_info.get('id')
    #             groups_members += group_info.get('memberCount')
    
    #     groups_pending, groups_funds = await asyncio.gather(
    #         self.get_groups_pending(groups_owned),
    #         self.get_groups_funds(groups_owned)
    #     )
    #     return {
    #         'owned': groups_owned,
    #         'members': groups_members,
    #         'pending': groups_pending,
    #         'funds': groups_funds
    #     }
    
    # TODO
    # async def get_groups_pending(self, groups_ids: set[int]) -> int:
    #     groups_pending = 0
    #     if groups_ids:
    #         for group_id in groups_ids:
    #             response: dict = await (await self._session.get(f'{RobloxAPI.APIS}/transaction-records/v1/groups/{group_id}/revenue/summary/year', cookies=self._cookies)).json()
    #             groups_pending += response.get('pendingRobux')
    #     return groups_pending
    
    # TODO
    # async def get_groups_funds(self, groups_ids: set[int]) -> int:
    #     groups_funds = 0
    #     if groups_ids:
    #         for group_id in groups_ids:
    #             response: dict = await (await self._session.get(f'{RobloxAPI.ECONOMY}/v1/groups/{group_id}/currency', cookies=self._cookies)).json()
    #             groups_funds += response.get('robux')
    #     return groups_funds
    
    async def get_place_visits(self, data: JsonDict) -> JsonDict:
        components = cast(JsonDict, data.get('components') or {})
        statistics = cast(JsonDict, components.get('Statistics') or {})
        return {'Place Visits': statistics.get('numberOfVisits')}
    
    async def get_age_group(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.APIS}/user-settings-api/v1/account-insights/age-group', cookies=self._cookies)).json(),
        )
        translation_key = response.get('ageGroupTranslationKey')
        return {'Age Group': convert_age_group(translation_key if isinstance(translation_key, str) else '')}
    
    async def get_verified_age(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.APIS}/age-verification-service/v1/age-verification/verified-age', cookies=self._cookies)).json(),
        )
        return {'Verified Age': response.get('verifiedAge')}
    
    async def get_verified_voice(self) -> JsonDict:
        response = cast(
            JsonDict,
            await (await self._session.get(f'{RobloxAPI.VOICE}/v1/settings', cookies=self._cookies)).json(),
        )
        return {'Verified Voice': response.get('isVerifiedForVoice')}
    
    async def get_fff_counter(self, data: JsonDict, *, key: Literal['friends', 'followers', 'followings']) -> JsonDict:
        components = cast(JsonDict, data.get('components') or {})
        header = cast(JsonDict, components.get('UserProfileHeader') or {})
        counts = cast(JsonDict, header.get('counts') or {})
        return {key.capitalize(): counts.get(f'{key}Count')}

    async def get_roblox_badges(self, data: JsonDict) -> JsonDict:
        components = cast(JsonDict, data.get('components') or {})
        roblox_badges = cast(JsonDict, components.get('RobloxBadges') or {})
        badge_list = cast(JsonList, roblox_badges.get('robloxBadgeList') or [])
        return {
            'Roblox Badges': [
                badge_type.get('value')
                for roblox_badge in badge_list
                for badge_type in [cast(JsonDict, roblox_badge.get('type') or {})]
            ]
        }


    # advanced getters
    async def get_x_csrf_token(self) -> str | None:
        response = (await self._session.post(f'{RobloxAPI.AUTH}/v2/logout', cookies=self._cookies)).headers
        return response.get('X-CSRF-Token')

    async def get_auth_ticket(self, x_csrf_token: str) -> str | None:
        headers = {
            'X-CSRF-Token': x_csrf_token
        }
        response = (await self._session.post(f'{RobloxAPI.AUTH}/v1/authentication-ticket', headers=headers)).headers
        return response.get('rbx-authentication-ticket')
    
    async def break_cookie(self, x_csrf_token: str) -> None:
        headers = {
            'X-CSRF-Token': x_csrf_token,
            'Set-Cookie': '.ROBLOSECURITY=; Max-Age=0; Path=/;'
        }
        await self._session.post(f'{RobloxAPI.AUTH}/v2/logout', headers=headers, cookies=self._cookies)
    
    async def generate_new_cookie(self, auth_ticket: str) -> str:
        data = {
            'authenticationTicket': auth_ticket
        }
        headers = {
            'RBXauthenticationNegotiation': '1'
        }
        response = (await self._session.post(f'{RobloxAPI.AUTH}/v1/authentication-ticket/redeem', data=data, headers=headers)).headers
        new_cookie = re.search(ROBLOX_COOKIE_PATTERN, str(response))
        if not new_cookie:
            raise InvalidCookie
        return new_cookie.group(0).rstrip(';')
    
    async def is_achieved_badge(self, badge_id: int) -> bool:
        return bool(await self._session.get(f'{RobloxAPI.BADGES}/v1/users/{self._player_id}/badges/{badge_id}/awarded-date'))

    async def get_place_id_user_in(self) -> int | None:
        data = { 'userIds': [self._player_id] }
        response = cast(
            JsonDict,
            await (await self._session.post(f'{RobloxAPI.PRESENCE}/v1/presence/users', data=data)).json(),
        )
        presence_list = cast(JsonList, response.get('userPresences') or [])
        user_presences = presence_list[0] if presence_list else {}
        return user_presences.get('placeId')

    async def get_place_server_ids(
        self,
        place_id: str,
        *,
        less_players: bool = True,
        exclude_full: bool = True,
        only_friends: bool = False,
        items_per_page: Literal[5, 10, 25, 50, 100] = ITEMS_PER_PAGE_PLACE_SERVER_IDS
    ) -> JsonDict:
        params = {
            'sortOrder': int(less_players),
            'limit': items_per_page,
            'excludeFullGames': exclude_full
        }
        return await (await self._session.get(f'{RobloxAPI.GAMES}/v1/games/{place_id}/servers/{int(only_friends)}', params=params)).json()

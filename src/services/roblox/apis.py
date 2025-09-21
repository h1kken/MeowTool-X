import asyncio
from typing import Literal
from src.utils.helpers import convert_date
from src.http.manager import AsyncRequestManager


class Account:
    def __init__(self, client: AsyncRequestManager, cookie: str):
        self._client = client
        self._cookies = {'.ROBLOSECURITY': cookie.strip()}
        self._account_information: dict = asyncio.run(self.get_complex_account_data()) # not_finished

    async def get_simple_account_data(self) -> dict:
        return (await self._client.get('https://users.roblox.com/v1/users/authenticated', cookies=self._cookies)).json()

    async def get_selected_account_data(
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
            'profileId': str(await self.get_id()),
            'profileType': 'User',
            'components': [{'component': component} for component in components],
            'includeComponentOrdering': True
        }
        return (await self._client.post('https://apis.roblox.com/profile-platform-api/v1/profiles/get', json=json)).json()

    async def get_complex_account_data(self) -> dict:
        return (await self._client.get('https://www.roblox.com/my/settings/json')).json()
    
    async def get_profile_link(self) -> str:
        return f'https://www.roblox.com/users/{await self.get_id()}'
    
    async def get_country_registration(self) -> str:
        response: dict = (await self._client.get('https://users.roblox.com/v1/users/authenticated/country-code')).json()
        return response.get('countryCode')
    
    async def get_id(self) -> int:
        return self._account_information.get('UserId')
    
    async def get_name(self) -> str:
        return self._account_information.get('Name')
    
    async def get_display_name(self) -> list:
        return self._account_information.get('DisplayName')
    
    async def get_registration_date_dd_mm_yyyy(self, user_id: int | str) -> list:
        response: dict = (await self._client.get(f'https://users.roblox.com/v1/users/{user_id}')).json()
        return await convert_date(response.get('created'), '%d.%m.%Y')
    
    async def get_registration_date_in_days(self) -> list:
        return self._account_information.get('AccountAgeInDays')
    
    async def get_robux(self, user_id: int | str) -> list:
        response: dict = (await self._client.get(f'https://economy.roblox.com/v1/users/{user_id}/currency')).json()
        return response.get('robux')
    
    async def get_billing(self) -> list:
        response: dict = (await self._client.get('https://billing.roblox.com/v1/credit')).json()
        return response.get('robuxAmount')
    
    async def get_transactions_year(self, user_id: int | str) -> list:
        response: dict = await self._client.get(f'https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=Summary')
        return {
            'pending': response.get('pendingRobuxTotal'),
            'donate': abs(response.get('outgoingRobuxTotal'))
        }
    
    # async def get_transaction_all_time(self, user_id: int | str) -> list:
    #     isDonateAllTime = 0
    #     nextCursor = ''
    #     currentPage = 0
    #     donateAllTimeMaxPages = config['Roblox']['CookieChecker']['Main']['Donate_All_Time_Max_Check_Pages']
    #     if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses']:
    #         isCustomGamepasses = deepcopy(checkListCustomGamepasses)
    #         customGamepassesMaxPages = config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses_Max_Check_Pages']
    #     else:
    #         customGamepassesMaxPages = -1
    #     maximumPage = max(donateAllTimeMaxPages, customGamepassesMaxPages)
    #     while nextCursor is not None and currentPage != maximumPage:
    #         data = await self._client.get(f'https://economy.roblox.com/v2/users/{user_id}/transactions?transactionType=2&limit=100&cursor={nextCursor}', cookies)
    #         for transaction in data['data']:
    #             if config['Roblox']['CookieChecker']['Main']['Donate_All_Time'] and (donateAllTimeMaxPages == -1 or currentPage < donateAllTimeMaxPages):
    #                 isDonateAllTime += transaction['currency']['amount']
    #             if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses'] and 'name' in transaction['details'] and transaction['details']['name'] in checkListCustomGamepasses and (customGamepassesMaxPages == -1 or currentPage < customGamepassesMaxPages):
    #                 isCustomGamepasses[transaction['details']['name']] += 1
    #         nextCursor = data['nextPageCursor']
    #         currentPage += 1
    
    #     isDonateAllTime = abs(isDonateAllTime)
    #     returner = [
    #         f'{ANSI.FG.CYAN}Donate (All Time): {ANSI.FG.GREEN if isDonateAllTime else ANSI.FG.RED}{isDonateAllTime}{ANSI.FG.WHITE} | ',
    #         f'Donate (All Time): {isDonateAllTime} | ',
    #         isDonateAllTime
    #     ] if config['Roblox']['CookieChecker']['Main']['Donate_All_Time'] else ['', '', '']
    
    #     if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses']:
    #         amountOfCustomGamepasses = sum(isCustomGamepasses.values())
    #         color, value = [ANSI.FG.GREEN, await formatCustomGamepassesOutput(isCustomGamepasses, outputMode)] if amountOfCustomGamepasses else [ANSI.FG.RED, '0']
    #         returner += [
    #             f'{ANSI.FG.CYAN}Custom Gamepasses: {color}{value}{ANSI.FG.WHITE} | ',
    #             f'Custom Gamepasses: {value} | ',
    #             [removeSpecialChars(name) for name, amount in isCustomGamepasses.items() if amount],
    #             amountOfCustomGamepasses
    #         ]
    #     else:
    #         returner += ['', '', '', '']
    #     return returner
    
    # async def get_rap(self, user_id: int | str) -> list:
    #     isRap = 0
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Rap_Max_Check_Pages']
    #     currentPage = 0
    #     while nextCursor is not None and currentPage != maximumPage:
    #         data = await self._client.get(f'https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100&cursor={nextCursor}', cookies)
    #         for item in data['data']:
    #             if item['recentAveragePrice'] is not None:
    #                 isRap += item['recentAveragePrice']
    #         nextCursor = data['nextPageCursor']
    #         currentPage += 1
    #     return [
    #         f'{ANSI.FG.CYAN}Rap: {ANSI.FG.GREEN if isRap else ANSI.FG.RED}{isRap}{ANSI.FG.WHITE} | ',
    #         f'Rap: {isRap} | ',
    #         isRap
    #     ]
    
    # async def get_cards(self) -> int:
    #     data = await self._client.get(f'https://apis.roblox.com/payments-gateway/v1/payment-profiles', cookies)
    #     return len(data)
    
    # async def get_premium_status(account_information: dict) -> bool:
    #     return self._account_information.get('IsPremium')
    
    # async def get_gamepasses(self, user_id: int | str, outputMode: str = 'PlaceNames') -> list:
    #     isGamepasses = {gamepass['PlaceName']: [] for gamepass in checkListGamepasses.values()}
    #     amountOfFoundGamepasses = 0
    #     amountOfCheckGamepasses = len(checkListGamepasses)
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Gamepasses_Max_Check_Pages']
    #     currentPage = 0
    #     while (nextCursor is not None and currentPage != maximumPage and amountOfFoundGamepasses != amountOfCheckGamepasses):
    #         data = await self._client.get(f'https://apis.roblox.com/game-passes/v1/users/{user_id}/game-passes?count=100&exclusiveStartId={nextCursor}', cookies)
    #         gamepasses = data['gamePasses']
    #         if not gamepasses:
    #             break
    #         for gamepass in gamepasses:
    #             gamepassId = str(gamepass['gamePassId'])
    #             if gamepassId in checkListGamepasses:
    #                 isGamepasses[checkListGamepasses[gamepassId]['PlaceName']].append(checkListGamepasses[gamepassId]['GamepassName'])
    #                 amountOfFoundGamepasses += 1
    #         nextCursor = None if len(gamepasses) < 100 else gamepassId
    #         currentPage += 1
    
    #     color, value = [ANSI.FG.GREEN, await formatNNPPOutput(isGamepasses, outputMode)] if amountOfFoundGamepasses else [ANSI.FG.RED, '0']
    #     return [
    #         f'{ANSI.FG.CYAN}Gamepasses: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Gamepasses: {value} | ',
    #         isGamepasses,
    #         amountOfFoundGamepasses
    #     ]
    
    # async def getBadges(self, user_id: int | str, outputMode: str = 'PlaceNames') -> list:
    #     isBadges = {badge['PlaceName']: [] for badge in checkListBadges.values()}
    #     amountOfFoundBadges = 0
    #     amountOfCheckBadges = len(checkListBadges)
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Badges_Max_Check_Pages']
    #     currentPage = 0
    #     while (nextCursor is not None and currentPage != maximumPage and amountOfFoundBadges != amountOfCheckBadges):
    #         data = await self._client.get(f'https://badges.roblox.com/v1/users/{user_id}/badges?limit=100&cursor={nextCursor}', cookies)
    #         for badge in data['data']:
    #             badgeId = str(badge['id'])
    #             if badgeId in checkListBadges:
    #                 isBadges[checkListBadges[badgeId]['PlaceName']].append(checkListBadges[badgeId]['BadgeName'])
    #                 amountOfFoundBadges += 1
    #         nextCursor = data['nextPageCursor']
    #         currentPage += 1
    
    #     color, value = [ANSI.FG.GREEN, await formatNNPPOutput(isBadges, outputMode)] if amountOfFoundBadges else [ANSI.FG.RED, '0']
    #     return [
    #         f'{ANSI.FG.CYAN}Badges: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Badges: {value} | ',
    #         isBadges,
    #         amountOfFoundBadges
    #     ]
    
    # async def getFavoritePlaces(self, user_id: int | str) -> list:
    #     isFavoritePlaces = []
    #     amountOfFoundFavoritePlaces = 0
    #     amountOfCheckFavoritePlaces = len(checkListFavoritePlaces)
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Favorite_Places_Max_Check_Pages']
    #     currentPage = 0
    #     while (nextCursor is not None and currentPage != maximumPage and amountOfFoundFavoritePlaces != amountOfCheckFavoritePlaces):
    #         data = await self._client.get(f'https://games.roblox.com/v2/users/{user_id}/favorite/games?limit=100&cursor={nextCursor}', cookies)
    #         for place in data['data']:
    #             placeId = str(place['rootPlace']['id'])
    #             if placeId in checkListFavoritePlaces:
    #                 isFavoritePlaces.append(checkListFavoritePlaces[placeId])
    #                 amountOfFoundFavoritePlaces += 1
    #         nextCursor = data['nextPageCursor']
    #         currentPage += 1
    
    #     return [
    #         f'{ANSI.FG.CYAN}Fav. Places: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Fav. Places: {value} | ',
    #         isFavoritePlaces,
    #         amountOfFoundFavoritePlaces
    #     ]
    
    # async def get_bundles(self, user_id: int | str, outputMode: str = 'Names') -> list:
    #     isBundles = {}
    #     amountOfFoundBundles = 0
    #     amountOfCheckBundles = len(checkListBundles)
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Bundles_Max_Check_Pages']
    #     currentPage = 0
    #     while nextCursor is not None and currentPage != maximumPage and amountOfFoundBundles != amountOfCheckBundles:
    #         data = await self._client.get(f'https://catalog.roblox.com/v1/users/{user_id}/bundles/1?limit=100&cursor={nextCursor}', cookies)
    #         for bundle in data['data']:
    #             bundleId = str(bundle['id'])
    #             if bundleId in checkListBundles:
    #                 isBundles[bundleId] = checkListBundles[bundleId]
    #                 amountOfFoundBundles += 1
    #         nextCursor = data['nextPageCursor']
    #         currentPage += 1
    
    #     isBundlesNames = list(isBundles.values())
    #     color, value = [ANSI.FG.GREEN, await formatNNOutput(isBundlesNames, outputMode)] if amountOfFoundBundles else [ANSI.FG.RED, '0']
    #     returner  = [
    #         f'{ANSI.FG.CYAN}Bundles: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Bundles: {value} | ',
    #         isBundlesNames,
    #         amountOfFoundBundles
    #     ]
    #     color, value, boolean = [ANSI.FG.GREEN, 'Yes', True] if '192' in isBundles else [ANSI.FG.RED, 'No', False]
    #     returner += [
    #         f'{ANSI.FG.CYAN}Korblox: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Korblox: {value} | ',
    #         value,
    #         boolean
    #     ] if '192' in checkListBundles else ['', '', '', '']
    #     color, value, boolean = [ANSI.FG.GREEN, 'Yes', True] if '201' in isBundles else [ANSI.FG.RED, 'No', False]
    #     returner += [
    #         f'{ANSI.FG.CYAN}Headless: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'Headless: {value} | ',
    #         value,
    #         boolean
    #     ] if '201' in checkListBundles else ['', '', '', '']
    #     return returner
    
    # async def get_inventory_privacy(self) -> str:
    #     data = await self._client.get(f'https://apis.roblox.com/user-settings-api/v1/user-settings/settings-and-options', cookies)
    #     return data['whoCanSeeMyInventory']['currentValue']
    
    # async def get_trade_privacy(self) -> str:
    #     data = await self._client.get('https://accountsettings.roblox.com/v1/trade-privacy', cookies)
    #     return data['tradePrivacy']
    
    # async def get_can_trade(account_information: dict) -> bool:
    #     return self._account_information.get('CanTrade')
    
    # async def get_sessions(self) -> int:
    #     sessions_amount = 0
    #     nextCursor = ''
    #     maximumPage = config['Roblox']['CookieChecker']['Main']['Sessions_Max_Check_Pages']
    #     currentPage = 0
    #     while nextCursor is not None and currentPage != maximumPage:
    #         data = await self._client.get(f'https://apis.roblox.com/token-metadata-service/v1/sessions?nextCursor={nextCursor}', cookies)
    #         sessions_amount += len(data['sessions'])
    #         nextCursor = data['nextCursor']
    #         currentPage += 1
    
    #     return sessions_amount
    
    # async def get_email_status(account_information: dict) -> bool:
    #     security_model: dict = self._account_information.get('MyAccountSecurityModel')
    #     return {
    #         'setted': security_model.get('IsEmailSet', False),
    #         'verified': security_model.get('IsEmailVerified', False)
    #     }
    

    # async def get_phone_status(self) -> bool:
    #     response = (await self._client.get('https://self._account_information.roblox.com/v1/phone', cookies)).json()
    #     return data['phone']
    
    # async def get_2fa_status(account_information: dict) -> bool:
    #     return self._account_information.get('MyAccountSecurityModel').get('IsTwoStepEnabled')
    
    # async def get_pin_status(account_information: dict) -> bool:
    #     return self._account_information.get('IsAccountPinEnabled')
    
    # async def get_groups_information(self, user_id: int | str) -> list:
    #     data = await self._client.get(f'https://groups.roblox.com/v1/users/{user_id}/groups/roles?includeLocked=true', cookies)
    #     isGroupsOwned = {}
    #     isGroupsMembers = 0
    #     for group in data['data']:
    #         if group['role']['rank'] == 255:
    #             isGroupsOwned[group['group']['name']] = group['group']['id']
    #             isGroupsMembers += group['group']['memberCount']
    
    #     color, value = [ANSI.FG.GREEN, await formatNNOutput(isGroupsOwned, outputMode)] if isGroupsOwned else [ANSI.FG.RED, '0']
    #     returner  = [
    #         f'{ANSI.FG.CYAN}G. Owned: {color}{value}{ANSI.FG.WHITE} | ',
    #         f'G. Owned: {value} | ',
    #         list(isGroupsOwned),
    #         len(isGroupsOwned)
    #     ] if config['Roblox']['CookieChecker']['Main']['Groups_Owned'] else ['', '', '', '']
    #     returner += [
    #         f'{ANSI.FG.CYAN}G. Members: {color}{isGroupsMembers}{ANSI.FG.WHITE} | ',
    #         f'G. Members: {isGroupsMembers} | ',
    #         isGroupsMembers
    #     ] if config['Roblox']['CookieChecker']['Main']['Groups_Members'] else ['', '', '']
    #     groups_ids = isGroupsOwned.values()
    #     groupsPending, groupsFunds = await asyncio.gather(
    #         getGroupsPending(cookie, groups_ids),
    #         getGroupsFunds(  cookie, groups_ids)
    #     )
    #     returner += groupsPending
    #     returner += groupsFunds
    #     return returner
    
    # async def get_groups_pending(self, groups_ids: list[int | str]) -> list:
    #     groups_pending = 0
    #     if groups_ids:
    #         for group_id in groups_ids:
    #             data = await self._client.get(f'https://apis.roblox.com/transaction-records/v1/groups/{group_id}/revenue/summary/year', cookies)
    #             groups_pending += data['pendingRobux']
    
    #     return groups_pending
    
    # async def get_groups_funds(self, groups_ids: list[int | str]) -> list:
    #     groups_funds = 0
    #     if groups_ids:
    #         for group_id in groups_ids:
    #             data = await self._client.get(f'https://economy.roblox.com/v1/groups/{group_id}/currency', cookies)
    #             groups_funds += data['robux']
    
    #     return groups_funds
    
    # async def get_above_13(account_information: dict) -> bool:
    #     return self._account_information.get('UserAbove13')
    
    # async def get_verified_age(self) -> bool:
    #     data = await self._client.get('https://apis.roblox.com/age-verification-service/v1/age-verification/verified-age', cookies)
    #     return data['isVerified']
    
    # async def get_verified_voice(self) -> bool:
    #     data = await self._client.get('https://voice.roblox.com/v1/settings', cookies)
    #     return data['isVerifiedForVoice']
    
    # async def get_friends_amount(self, user_id: int | str) -> list:
    #     data = await self._client.get(f'https://friends.roblox.com/v1/users/{user_id}/friends/count', cookies)
    #     return data['count']
    
    # async def get_followers_amount(self, user_id: int | str) -> list:
    #     data = await self._client.get(f'https://friends.roblox.com/v1/users/{user_id}/followers/count', cookies)
    #     return data['count']
    
    # async def get_followings_amount(self, user_id: int | str) -> list:
    #     data = await self._client.get(f'https://friends.roblox.com/v1/users/{user_id}/followings/count', cookies)
    #     return data['count']
    
    # async def get_profile_badges(self, user_id: int | str) -> list[str]:
    #     data = await self._client.get(f'https://self._account_information.roblox.com/v1/users/{user_id}/roblox-badges')
    #     return [robloxBadge['name'] for robloxBadge in data]
    
    # async def get_user_is_achieved_badge(self, user_id: int | str, badge_id: int | str) -> bool:
    #     response: dict = (await self._client.get(f'https://badges.roblox.com/v1/users/{user_id}/badges/{badge_id}/awarded-date')).json()
    #     return bool(response)

    # async def get_place_id_user_in(self, user_id: int | str) -> int:
    #     data = {
    #         'userIds': [user_id]
    #     }
    #     response: dict = (await self._client.post('https://presence.roblox.com/v1/presence/users', data=data)).json()
    #     user_presences: list[dict] = response.get('userPresences', [{}])
    #     return user_presences[0].get('placeId')

    # async def get_x_csrf_token(self) -> str:
    #     response = (await self._client.post('https://auth.roblox.com/v2/logout')).headers
    #     return response.get('X-CSRF-Token')

    # async def get_auth_ticket(self, x_csrf_token: str) -> str:
    #     headers = {
    #         'X-CSRF-Token': x_csrf_token,
    #         'referer': 'https://www.roblox.com/hewhewhew'
    #     }
    #     response: dict = (await self._client.post('https://auth.roblox.com/v1/authentication-ticket', headers=headers)).headers
    #     x_csrf_token = response.get('rbx-authentication-ticket')
    #     return x_csrf_token

    # async def get_server_ids(place_id: int | str, *, less_players=True, exclude_full_places=True, amount: Literal['5', '10', '25', '50', '100'] = '25') -> dict:
    #     response = client.get(f'https://games.roblox.com/v1/games/{place_id}/servers/0?{'sortOrder=1&' if less_players else ''}{'excludeFullGames=true&' if exclude_full_places else ''}limit={amount}').json()
    #     return response
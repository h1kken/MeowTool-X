from typing import Literal
from src.utils.helpers import convert_date
from src.http.manager import AsyncRequestManager


class RobloxApis:
    @staticmethod
    async def get_account_information(cookies: dict):
        async with AsyncRequestManager(cookies=cookies) as client:
            return await client.get('https://www.roblox.com/my/settings/json', cookies)
    
    @staticmethod
    async def get_profile_link(userId: int | str) -> list:
        return f'https://www.roblox.com/users/{userId}'
    
    @staticmethod
    async def get_country_registration(cookies: dict) -> str:
        async with AsyncRequestManager(cookies=cookies) as client:
            response = await client.get('https://users.roblox.com/v1/users/authenticated/country-code', cookies)
            data = response
        return data['countryCode']
    
    @staticmethod
    async def get_name(account_information: dict) -> str:
        return account_information['Name']
    
    @staticmethod
    async def get_display_name(account_information: dict) -> list:
        return account_information['DisplayName']
    
    @staticmethod
    async def get_registration_date_dd_mm_yyyy(cookies: dict, userId: int | str) -> list:
        async with AsyncRequestManager(cookies=cookies) as client:
            data = await client.get(f'https://users.roblox.com/v1/users/{userId}', cookies)
        return await convert_date(data['created'], '%d.%m.%Y')
    
    @staticmethod
    async def get_registration_date_in_days(account_information) -> list:
        return account_information['AccountAgeInDays']
    
    @staticmethod
    async def get_robux(cookies: dict, userId: int | str) -> list:
        data = await client.get(f'https://economy.roblox.com/v1/users/{userId}/currency', cookies)
        return data['robux']
    
    @staticmethod
    async def get_billing(cookies: dict) -> list:
        data = await client.get('https://billing.roblox.com/v1/credit', cookies)
        return data['robuxAmount']
    
    @staticmethod
    async def get_transactions_year(cookies: dict, userId: int | str) -> list:
        data = await client.get(f'https://economy.roblox.com/v2/users/{userId}/transaction-totals?timeFrame=Year&transactionType=Summary', cookies)
        isPending = data['pendingRobuxTotal']
        isDonate  = abs(data['outgoingRobuxTotal'])
        returner  = [
            f'{ANSI.FG.CYAN}Pending: {ANSI.FG.GREEN if isPending else ANSI.FG.RED}{isPending}{ANSI.FG.WHITE} | ',
            f'Pending: {isPending} | ',
            isPending
        ] if config['Roblox']['CookieChecker']['Main']['Pending'] else ['', '', '']
        returner += [
            f'{ANSI.FG.CYAN}Donate (1 Year): {ANSI.FG.GREEN if isDonate else ANSI.FG.RED}{isDonate}{ANSI.FG.WHITE} | ',
            f'Donate (1 Year): {isDonate} | ',
            isDonate
        ] if config['Roblox']['CookieChecker']['Main']['Donate_1_Year'] else ['', '', '']
        return returner
    
    @staticmethod
    async def get_transaction_all_time(cookies: dict, userId: int | str) -> list:
        isDonateAllTime = 0
        nextCursor = ''
        currentPage = 0
        donateAllTimeMaxPages = config['Roblox']['CookieChecker']['Main']['Donate_All_Time_Max_Check_Pages']
        if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses']:
            isCustomGamepasses = deepcopy(checkListCustomGamepasses)
            customGamepassesMaxPages = config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses_Max_Check_Pages']
        else:
            customGamepassesMaxPages = -1
        maximumPage = max(donateAllTimeMaxPages, customGamepassesMaxPages)
        while nextCursor is not None and currentPage != maximumPage:
            data = await client.get(f'https://economy.roblox.com/v2/users/{userId}/transactions?transactionType=2&limit=100&cursor={nextCursor}', cookies)
            for transaction in data['data']:
                if config['Roblox']['CookieChecker']['Main']['Donate_All_Time'] and (donateAllTimeMaxPages == -1 or currentPage < donateAllTimeMaxPages):
                    isDonateAllTime += transaction['currency']['amount']
                if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses'] and 'name' in transaction['details'] and transaction['details']['name'] in checkListCustomGamepasses and (customGamepassesMaxPages == -1 or currentPage < customGamepassesMaxPages):
                    isCustomGamepasses[transaction['details']['name']] += 1
            nextCursor = data['nextPageCursor']
            currentPage += 1
    
        isDonateAllTime = abs(isDonateAllTime)
        returner = [
            f'{ANSI.FG.CYAN}Donate (All Time): {ANSI.FG.GREEN if isDonateAllTime else ANSI.FG.RED}{isDonateAllTime}{ANSI.FG.WHITE} | ',
            f'Donate (All Time): {isDonateAllTime} | ',
            isDonateAllTime
        ] if config['Roblox']['CookieChecker']['Main']['Donate_All_Time'] else ['', '', '']
    
        if config['Roblox']['CookieChecker']['Main']['Custom_Gamepasses']:
            amountOfCustomGamepasses = sum(isCustomGamepasses.values())
            color, value = [ANSI.FG.GREEN, await formatCustomGamepassesOutput(isCustomGamepasses, outputMode)] if amountOfCustomGamepasses else [ANSI.FG.RED, '0']
            returner += [
                f'{ANSI.FG.CYAN}Custom Gamepasses: {color}{value}{ANSI.FG.WHITE} | ',
                f'Custom Gamepasses: {value} | ',
                [removeSpecialChars(name) for name, amount in isCustomGamepasses.items() if amount],
                amountOfCustomGamepasses
            ]
        else:
            returner += ['', '', '', '']
        return returner
    
    @staticmethod
    async def getRap(cookies: dict, userId: int | str) -> list:
        isRap = 0
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Rap_Max_Check_Pages']
        currentPage = 0
        while nextCursor is not None and currentPage != maximumPage:
            data = await client.get(f'https://inventory.roblox.com/v1/users/{userId}/assets/collectibles?sortOrder=Asc&limit=100&cursor={nextCursor}', cookies)
            for item in data['data']:
                if item['recentAveragePrice'] is not None:
                    isRap += item['recentAveragePrice']
            nextCursor = data['nextPageCursor']
            currentPage += 1
        return [
            f'{ANSI.FG.CYAN}Rap: {ANSI.FG.GREEN if isRap else ANSI.FG.RED}{isRap}{ANSI.FG.WHITE} | ',
            f'Rap: {isRap} | ',
            isRap
        ]
    
    @staticmethod
    async def get_cards(cookies: dict) -> int:
        data = await client.get(f'https://apis.roblox.com/payments-gateway/v1/payment-profiles', cookies)
        return len(data)
    
    @staticmethod
    async def get_premium_status(account_information: dict) -> bool:
        return account_information['IsPremium']
    
    @staticmethod
    async def getGamepasses(cookies: dict, userId: int | str, outputMode: str = 'PlaceNames') -> list:
        isGamepasses = {gamepass['PlaceName']: [] for gamepass in checkListGamepasses.values()}
        amountOfFoundGamepasses = 0
        amountOfCheckGamepasses = len(checkListGamepasses)
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Gamepasses_Max_Check_Pages']
        currentPage = 0
        while (nextCursor is not None and currentPage != maximumPage and amountOfFoundGamepasses != amountOfCheckGamepasses):
            data = await client.get(f'https://apis.roblox.com/game-passes/v1/users/{userId}/game-passes?count=100&exclusiveStartId={nextCursor}', cookies)
            gamepasses = data['gamePasses']
            if not gamepasses:
                break
            for gamepass in gamepasses:
                gamepassId = str(gamepass['gamePassId'])
                if gamepassId in checkListGamepasses:
                    isGamepasses[checkListGamepasses[gamepassId]['PlaceName']].append(checkListGamepasses[gamepassId]['GamepassName'])
                    amountOfFoundGamepasses += 1
            nextCursor = None if len(gamepasses) < 100 else gamepassId
            currentPage += 1
    
        color, value = [ANSI.FG.GREEN, await formatNNPPOutput(isGamepasses, outputMode)] if amountOfFoundGamepasses else [ANSI.FG.RED, '0']
        return [
            f'{ANSI.FG.CYAN}Gamepasses: {color}{value}{ANSI.FG.WHITE} | ',
            f'Gamepasses: {value} | ',
            isGamepasses,
            amountOfFoundGamepasses
        ]
    
    @staticmethod
    async def getBadges(cookies: dict, userId: int | str, outputMode: str = 'PlaceNames') -> list:
        isBadges = {badge['PlaceName']: [] for badge in checkListBadges.values()}
        amountOfFoundBadges = 0
        amountOfCheckBadges = len(checkListBadges)
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Badges_Max_Check_Pages']
        currentPage = 0
        while (nextCursor is not None and currentPage != maximumPage and amountOfFoundBadges != amountOfCheckBadges):
            data = await client.get(f'https://badges.roblox.com/v1/users/{userId}/badges?limit=100&cursor={nextCursor}', cookies)
            for badge in data['data']:
                badgeId = str(badge['id'])
                if badgeId in checkListBadges:
                    isBadges[checkListBadges[badgeId]['PlaceName']].append(checkListBadges[badgeId]['BadgeName'])
                    amountOfFoundBadges += 1
            nextCursor = data['nextPageCursor']
            currentPage += 1
    
        color, value = [ANSI.FG.GREEN, await formatNNPPOutput(isBadges, outputMode)] if amountOfFoundBadges else [ANSI.FG.RED, '0']
        return [
            f'{ANSI.FG.CYAN}Badges: {color}{value}{ANSI.FG.WHITE} | ',
            f'Badges: {value} | ',
            isBadges,
            amountOfFoundBadges
        ]
    
    @staticmethod
    async def getFavoritePlaces(cookies: dict, userId: int | str) -> list:
        isFavoritePlaces = []
        amountOfFoundFavoritePlaces = 0
        amountOfCheckFavoritePlaces = len(checkListFavoritePlaces)
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Favorite_Places_Max_Check_Pages']
        currentPage = 0
        while (nextCursor is not None and currentPage != maximumPage and amountOfFoundFavoritePlaces != amountOfCheckFavoritePlaces):
            data = await client.get(f'https://games.roblox.com/v2/users/{userId}/favorite/games?limit=100&cursor={nextCursor}', cookies)
            for place in data['data']:
                placeId = str(place['rootPlace']['id'])
                if placeId in checkListFavoritePlaces:
                    isFavoritePlaces.append(checkListFavoritePlaces[placeId])
                    amountOfFoundFavoritePlaces += 1
            nextCursor = data['nextPageCursor']
            currentPage += 1
    
        return [
            f'{ANSI.FG.CYAN}Fav. Places: {color}{value}{ANSI.FG.WHITE} | ',
            f'Fav. Places: {value} | ',
            isFavoritePlaces,
            amountOfFoundFavoritePlaces
        ]
    
    @staticmethod
    async def get_bundles(cookies: dict, userId: int | str, outputMode: str = 'Names') -> list:
        isBundles = {}
        amountOfFoundBundles = 0
        amountOfCheckBundles = len(checkListBundles)
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Bundles_Max_Check_Pages']
        currentPage = 0
        while nextCursor is not None and currentPage != maximumPage and amountOfFoundBundles != amountOfCheckBundles:
            data = await client.get(f'https://catalog.roblox.com/v1/users/{userId}/bundles/1?limit=100&cursor={nextCursor}', cookies)
            for bundle in data['data']:
                bundleId = str(bundle['id'])
                if bundleId in checkListBundles:
                    isBundles[bundleId] = checkListBundles[bundleId]
                    amountOfFoundBundles += 1
            nextCursor = data['nextPageCursor']
            currentPage += 1
    
        isBundlesNames = list(isBundles.values())
        color, value = [ANSI.FG.GREEN, await formatNNOutput(isBundlesNames, outputMode)] if amountOfFoundBundles else [ANSI.FG.RED, '0']
        returner  = [
            f'{ANSI.FG.CYAN}Bundles: {color}{value}{ANSI.FG.WHITE} | ',
            f'Bundles: {value} | ',
            isBundlesNames,
            amountOfFoundBundles
        ]
        color, value, boolean = [ANSI.FG.GREEN, 'Yes', True] if '192' in isBundles else [ANSI.FG.RED, 'No', False]
        returner += [
            f'{ANSI.FG.CYAN}Korblox: {color}{value}{ANSI.FG.WHITE} | ',
            f'Korblox: {value} | ',
            value,
            boolean
        ] if '192' in checkListBundles else ['', '', '', '']
        color, value, boolean = [ANSI.FG.GREEN, 'Yes', True] if '201' in isBundles else [ANSI.FG.RED, 'No', False]
        returner += [
            f'{ANSI.FG.CYAN}Headless: {color}{value}{ANSI.FG.WHITE} | ',
            f'Headless: {value} | ',
            value,
            boolean
        ] if '201' in checkListBundles else ['', '', '', '']
        return returner
    
    @staticmethod
    async def get_inventory_privacy(cookies: dict) -> str:
        data = await client.get(f'https://apis.roblox.com/user-settings-api/v1/user-settings/settings-and-options', cookies)
        return data['whoCanSeeMyInventory']['currentValue']
    
    @staticmethod
    async def get_trade_privacy(cookies: dict) -> str:
        data = await client.get('https://accountsettings.roblox.com/v1/trade-privacy', cookies)
        return data['tradePrivacy']
    
    @staticmethod
    async def get_can_trade(account_information: dict) -> bool:
        return account_information['CanTrade']
    
    @staticmethod
    async def get_sessions(cookies: dict) -> int:
        isSessions = 0
        nextCursor = ''
        maximumPage = config['Roblox']['CookieChecker']['Main']['Sessions_Max_Check_Pages']
        currentPage = 0
        while nextCursor is not None and currentPage != maximumPage:
            data = await client.get(f'https://apis.roblox.com/token-metadata-service/v1/sessions?nextCursor={nextCursor}', cookies)
            isSessions += len(data['sessions'])
            nextCursor = data['nextCursor']
            currentPage += 1
    
        return [
            f'{ANSI.FG.CYAN}Sessions: {ANSI.FG.RED if isSessions >= 10 else ANSI.FG.YELLOW if isSessions >= 5 else ANSI.FG.GREEN}{isSessions}{ANSI.FG.WHITE} | ',
            f'Sessions: {isSessions} | ',
            isSessions
        ]
    
    @staticmethod
    async def get_email_setted(account_information: dict) -> bool:
        return account_information['MyAccountSecurityModel']['IsEmailSet']
    
    @staticmethod
    async def get_email_verified(account_information: dict) -> bool:
        return account_information['MyAccountSecurityModel']['IsEmailVerified']
    
    @staticmethod
    async def get_phone_status(cookies: dict) -> bool:
        data = await client.get('https://account_information.roblox.com/v1/phone', cookies)
        return data['phone']
    
    @staticmethod
    async def get_2fa_status(account_information: dict) -> bool:
        return account_information['MyAccountSecurityModel']['IsTwoStepEnabled']
    
    @staticmethod
    async def get_pin_status(account_information: dict) -> bool:
        return account_information['IsAccountPinEnabled']
    
    @staticmethod
    async def get_groups_information(cookies: dict, userId: int | str) -> list:
        data = await client.get(f'https://groups.roblox.com/v1/users/{userId}/groups/roles?includeLocked=true', cookies)
        isGroupsOwned = {}
        isGroupsMembers = 0
        for group in data['data']:
            if group['role']['rank'] == 255:
                isGroupsOwned[group['group']['name']] = group['group']['id']
                isGroupsMembers += group['group']['memberCount']
    
        color, value = [ANSI.FG.GREEN, await formatNNOutput(isGroupsOwned, outputMode)] if isGroupsOwned else [ANSI.FG.RED, '0']
        returner  = [
            f'{ANSI.FG.CYAN}G. Owned: {color}{value}{ANSI.FG.WHITE} | ',
            f'G. Owned: {value} | ',
            list(isGroupsOwned),
            len(isGroupsOwned)
        ] if config['Roblox']['CookieChecker']['Main']['Groups_Owned'] else ['', '', '', '']
        returner += [
            f'{ANSI.FG.CYAN}G. Members: {color}{isGroupsMembers}{ANSI.FG.WHITE} | ',
            f'G. Members: {isGroupsMembers} | ',
            isGroupsMembers
        ] if config['Roblox']['CookieChecker']['Main']['Groups_Members'] else ['', '', '']
        groups_ids = isGroupsOwned.values()
        groupsPending, groupsFunds = await asyncio.gather(
            getGroupsPending(cookie, groups_ids),
            getGroupsFunds(  cookie, groups_ids)
        )
        returner += groupsPending
        returner += groupsFunds
        return returner
    
    @staticmethod
    async def get_groups_pending(cookies: dict, groups_ids: list[int | str]) -> list:
        groups_pending = 0
        if groups_ids:
            for group_id in groups_ids:
                data = await client.get(f'https://apis.roblox.com/transaction-records/v1/groups/{group_id}/revenue/summary/year', cookies)
                groups_pending += data['pendingRobux']
    
        return groups_pending
    
    @staticmethod
    async def get_groups_funds(cookies: dict, groups_ids: list[int | str]) -> list:
        groups_funds = 0
        if groups_ids:
            for group_id in groups_ids:
                data = await client.get(f'https://economy.roblox.com/v1/groups/{group_id}/currency', cookies)
                groups_funds += data['robux']
    
        return groups_funds
    
    @staticmethod
    async def get_above_13(account_information: dict) -> bool:
        return account_information['UserAbove13']
    
    @staticmethod
    async def get_verified_age(cookies: dict) -> bool:
        data = await client.get('https://apis.roblox.com/age-verification-service/v1/age-verification/verified-age', cookies)
        return data['isVerified']
    
    @staticmethod
    async def get_verified_voice(cookies: dict) -> bool:
        data = await client.get('https://voice.roblox.com/v1/settings', cookies)
        return data['isVerifiedForVoice']
    
    # @staticmethod
    # async def get_friends_amount(cookies: dict, userId: int | str) -> list:
    #     data = await client.get(f'https://friends.roblox.com/v1/users/{userId}/friends/count', cookies)
    #     return data['count']
    
    # @staticmethod
    # async def get_followers_amount(cookies: dict, userId: int | str) -> list:
    #     data = await client.get(f'https://friends.roblox.com/v1/users/{userId}/followers/count', cookies)
    #     return data['count']
    
    # @staticmethod
    # async def get_followings_amount(cookies: dict, userId: int | str) -> list:
    #     data = await client.get(f'https://friends.roblox.com/v1/users/{userId}/followings/count', cookies)
    #     return data['count']
    
    @staticmethod
    async def get_profile_badges(cookies: dict, userId: int | str) -> list[str]:
        data = await client.get(f'https://account_information.roblox.com/v1/users/{userId}/roblox-badges', cookies)
        return [robloxBadge['name'] for robloxBadge in data]
    
    @staticmethod
    async def get_x_csrf_token(cookies: dict) -> list:
        data = await client.post('https://auth.roblox.com/v2/logout', cookies)
        return data.headers['X-CSRF-Token']

    @staticmethod
    async def get_simple_account_data(cookies: dict[str, str]) -> dict:
        async with AsyncRequestManager(cookies=cookies) as client:
            response = client.get('https://users.roblox.com/v1/users/authenticated').json()
        return response

    @staticmethod
    async def get_complex_account_data(cookies: dict[str, str]) -> dict:
        async with AsyncRequestManager(cookies=cookies) as client:
            response = client.get('https://www.roblox.com/my/settings/json').json()
        return response
    
    @staticmethod
    async def get_user_is_achieved_badge(cookies: dict[str, str], user_id: int | str, badge_id: int | str) -> bool:
        async with AsyncRequestManager(cookies=cookies) as client:
            response = client.get(f'https://badges.roblox.com/v1/users/{user_id}/badges/{badge_id}/awarded-date')
        return True if response else False

    @staticmethod
    async def get_place_id_user_in(cookies: dict, user_id: int | str) -> int:
        data = {
            'userIds': [user_id]
        }
        async with AsyncRequestManager(cookies=cookies) as client:
            response = client.post('https://presence.roblox.com/v1/presence/users', data=data).json()
        return response['userPresences'][0]['placeId']

    @staticmethod
    async def get_x_csrf_token(cookies: dict[str, str]) -> str:
        async with AsyncRequestManager(cookies=cookies) as client:
            response = client.post('https://auth.roblox.com/v2/logout').headers
        return response['X-CSRF-Token']

    @staticmethod
    async def get_auth_ticket(cookies: dict[str, str], x_csrf_token: str) -> str:
        headers = {
            'X-CSRF-Token': x_csrf_token,
            'referer': 'https://www.roblox.com/hewhewhew'
        }
        async with AsyncRequestManager(headers=headers, cookies=cookies) as client:
            response = client.post('https://auth.roblox.com/v1/authentication-ticket').headers
        return response['rbx-authentication-ticket']

    @staticmethod
    async def get_server_ids(place_id: int | str, *, less_players=True, exclude_full_places=True, amount: Literal['5', '10', '25', '50', '100'] = '25') -> dict:
        async with AsyncRequestManager() as client:
            response = client.get(f'https://games.roblox.com/v1/games/{place_id}/servers/0?{'sortOrder=1&' if less_players else ''}{'excludeFullGames=true&' if exclude_full_places else ''}limit={amount}').json()
        return response
    
    
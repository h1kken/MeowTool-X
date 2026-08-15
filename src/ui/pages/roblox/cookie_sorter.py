from src.services.roblox.cookie_sorter import RobloxCookieSorter
from src.ui.pages.base_prepare import BasePreparePage


class RobloxCookieSorterPage(BasePreparePage):
    _OBJECT_NAME = 'Roblox_Cookie_Sorter'
    _WORKER_CLASS = RobloxCookieSorter

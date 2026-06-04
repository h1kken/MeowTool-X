class RobloxException(Exception):
    pass
class InvalidCookie(RobloxException):
    pass
class AccountBanned(RobloxException):
    pass
class AccountDuplicate(RobloxException):
    pass
class RegisteredEarlier(RobloxException):
    pass

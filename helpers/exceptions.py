# Custom exceptions
class INSNotSupportedError(RuntimeError):
    """Raised when reader returns 6D 00 - Instruction Not Supported"""
    pass


class CommandNotAllowedError(RuntimeError):
    """Raised when reader returns 69 86 - Command not allowed / Security condition not satisfied (raised by reader)"""
    pass


class SecurityNotSatisfiedError(RuntimeError):
    """Raised when reader returns 69 82 - Security condition not satisfied (raised by card)"""
    pass


class WrongPINError(RuntimeError):
    """Raised when reader returns 63 Cx - Wrong PIN with retries remaining"""
    pass
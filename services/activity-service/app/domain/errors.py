class DomainError(Exception):
    pass


class NotAuthorized(DomainError):
    pass


class InvalidAgeBands(DomainError):
    pass


class ActivityNotFound(DomainError):
    pass

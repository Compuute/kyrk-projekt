"""Domain-level exceptions. API layer translates these to HTTP status codes."""


class DomainError(Exception):
    """Base class for all domain errors."""


class MemberNotFound(DomainError):
    pass


class MemberAlreadyExists(DomainError):
    pass


class NotAuthorized(DomainError):
    """Caller authenticated but lacks the required role."""


class ChurchMismatch(DomainError):
    """Caller's church_id does not match the target resource."""


class InvalidMemberData(DomainError):
    pass

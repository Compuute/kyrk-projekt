class DomainError(Exception):
    pass


class CertificateNotFound(DomainError):
    pass


class NotAuthorized(DomainError):
    pass


class InvalidStateTransition(DomainError):
    pass

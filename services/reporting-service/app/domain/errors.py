class DomainError(Exception):
    pass


class PIIRejected(DomainError):
    """Payload contained a forbidden identity field."""


class ReportNotFound(DomainError):
    pass


class NotAuthorized(DomainError):
    pass

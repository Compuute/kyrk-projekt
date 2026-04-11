class DomainError(Exception):
    pass


class ConsentMissing(DomainError):
    pass


class RateLimited(DomainError):
    pass

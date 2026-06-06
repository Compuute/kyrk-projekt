class DomainError(Exception):
    pass


class ConsentMissing(DomainError):
    pass


class RateLimited(DomainError):
    pass


class NotAuthorized(DomainError):
    """Caller authenticated but lacks the required role."""


class SubmissionNotFound(DomainError):
    pass


class SubmissionAlreadyProcessed(DomainError):
    """A submission already transitioned out of PENDING."""


class DuplicateSubmission(DomainError):
    """A submission with the same personal_number already exists."""


class DownstreamFailure(DomainError):
    """membership-service rejected or errored on the create_member call."""

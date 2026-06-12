class JobFailed(Exception):
    """Transient job failure — the Pub/Sub message should be redelivered."""

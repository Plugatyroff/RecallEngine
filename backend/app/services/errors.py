"""Errors raised by the services. The API layer turns them into HTTP responses."""


class NotFoundError(LookupError):
    """A referenced object (topic, note type, card) does not exist."""


class InvalidInputError(ValueError):
    """The request is well-formed but its content does not fit, e.g. wrong number of fields."""

class IntegrityConstraintViolationError(ValueError):
    pass


class TableNotFoundError(LookupError):
    pass


class RecordNotFoundError(LookupError):
    pass


class RelationshipNotFoundError(LookupError):
    pass


class PageOutOfRangeError(ValueError):
    pass

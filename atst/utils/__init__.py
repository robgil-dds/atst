import re

from sqlalchemy.exc import IntegrityError

from atst.database import db
from atst.domain.exceptions import AlreadyExistsError


def first_or_none(predicate, lst):
    return next((x for x in lst if predicate(x)), None)


def getattr_path(obj, path, default=None):
    _obj = obj
    for item in path.split("."):
        if isinstance(_obj, dict):
            _obj = _obj.get(item)
        else:
            _obj = getattr(_obj, item, default)
    return _obj


def camel_to_snake(camel_cased):
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_cased)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def pick(keys, dct):
    _keys = set(keys)
    return {k: v for (k, v) in dct.items() if k in _keys}


def commit_or_raise_already_exists_error(message):
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise AlreadyExistsError(message)

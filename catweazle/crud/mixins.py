import pymongo

from catweazle.errors import QueryParamValidationError

from catweazle.model.v2.common import filter_complex_search
from catweazle.model.v2.common import filter_complex_search_pattern


class FilterMixIn(object):
    @staticmethod
    def _filter_boolean(query, field, selector):
        if selector is None:
            return
        if selector in [True, "true", "True", "1"]:
            selector = True
        else:
            selector = False
        query[field] = selector

    @staticmethod
    def _filter_list(query, field, selector, nin=False):
        if selector is None:
            return
        if type(selector) is not list:
            selector = list(set(selector.split(",")))
        if nin:
            query[field] = {"$nin": selector}
        else:
            query[field] = {"$in": selector}

    @staticmethod
    def _filter_re(query, field, selector, list_filter=None):
        if selector and list_filter is not None:
            query[field] = {"$regex": selector, "$in": list_filter}
        elif selector:
            query[field] = {"$regex": selector}
        elif list_filter is not None:
            query[field] = {"$in": list_filter}

    @staticmethod
    def _filter_literal(query, field, selector, list_filter=None):
        if selector and list_filter:
            query[field] = {"$eq": selector, "$in": list_filter}
        elif selector:
            query[field] = selector
        elif list_filter:
            query[field] = {"$in": list_filter}

    @staticmethod
    def _filter_complex_search(
        query: dict,
        base_attribute: str,
        complex_search: filter_complex_search,
    ):
        def str_to_bool(s: str):
            _true = ["1", "true", "True"]
            return s in _true

        if not complex_search:
            return

        for item in complex_search:
            res = filter_complex_search_pattern.match(item)
            _attr = res.group(1)
            _op = res.group(2)
            _type = res.group(3)
            _value = res.group(4)
            query[f"{base_attribute}.{_attr}"] = {}
            try:
                if _op in ["in", "nin"]:
                    _value = _value.split(",")
                    if _type == "bool":
                        _value = [str_to_bool(item) for item in _value]
                    elif _type == "float":
                        _value = [float(item) for item in _value]
                    elif _type == "int":
                        _value = [int(item) for item in _value]
                elif _op == "regex":
                    if _type != "str":
                        raise QueryParamValidationError(
                            msg=f"regex search only supports type str, got {_type}"
                        )
                else:
                    if _type == "bool":
                        _value = str_to_bool(_value)
                    elif _type == "float":
                        _value = float(_value)
                    elif _type == "int":
                        _value = int(_value)
            except ValueError:
                raise QueryParamValidationError(
                    msg=f"could not transform attribute {_attr} with value {_value} into type {_type}"
                )
            query[f"{base_attribute}.{_attr}"][f"${_op}"] = _value


class Format:
    @staticmethod
    def _format(item):
        item.pop("_id", None)
        return item

    @staticmethod
    def _format_multi(item, count=None):
        return {"result": item, "meta": {"result_size": count}}


class PaginationSkipMixIn:
    @staticmethod
    def _pagination_skip(page, limit):
        return page * limit


class ProjectionMixIn:
    @staticmethod
    def _projection(fields):
        if not fields:
            return None
        result = {}
        for field in fields:
            result[field] = 1
        return result


class SortMixIn:
    @staticmethod
    def _sort(sort, sort_order):
        if sort_order == "ascending":
            return [(sort, pymongo.ASCENDING)]
        else:
            return [(sort, pymongo.DESCENDING)]

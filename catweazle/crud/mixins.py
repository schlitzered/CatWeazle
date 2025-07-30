import pymongo


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

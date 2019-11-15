__author__ = 'schlitzer'

import uuid

import pymongo
from bson.binary import Binary, STANDARD

from catweazle.errors import InvalidSelectors
from catweazle.errors import InvalidFields
from catweazle.errors import InvalidParameterValue
from catweazle.errors import InvalidPaginationLimit
from catweazle.errors import InvalidSortCriteria
from catweazle.errors import InvalidUUID


def pagination_from_schema(schema, path):
    for item in schema['paths'][path]['get']['parameters']:
        if item['name'] == 'limit':
            fields = (item['description'].split(':', maxsplit=1)[1].split(','))
            fields = [x.strip(' ') for x in fields]
            result = list()
            for field in fields:
                result.append(int(field))
            result.sort()
            return result


def projection_from_schema(schema, path):
    for item in schema['paths'][path]['get']['parameters']:
        if item['name'] == 'fields':
            fields = (item['description'].split(':', maxsplit=1)[1].split(','))
            fields = [x.strip(' ') for x in fields]
            result = dict()
            for field in fields:
                result[field] = 1
            return result


def sort_from_schema(schema, path):
    for item in schema['paths'][path]['get']['parameters']:
        if item['name'] == 'sort':
            fields = (item['description'].split(':', maxsplit=1)[1].split(','))
            fields = [x.strip(' ') for x in fields]
            result = list()
            for field in fields:
                result.append([field, pymongo.ASCENDING])
            return result


class ID(object):
    @staticmethod
    def _str_uuid_2_bin(_id):
        try:
            return Binary(uuid.UUID(_id).bytes, STANDARD)
        except ValueError:
            raise InvalidUUID(_id)

    def _str_uuid_2_bin_list(self, _ids):
        uuids = list()
        for _id in _ids:
            try:
                uuids.append(self._str_uuid_2_bin(_id))
            except ValueError:
                raise InvalidUUID(_id)
        return uuids

    @staticmethod
    def _bin_uuid_2_str_list(_ids):
        uuids = list()
        for _id in _ids:
            try:
                uuids.append(str(_id))
            except ValueError:
                raise InvalidUUID(_id)
        return uuids


class Format(object):
    @staticmethod
    def _format(item, multi=False, keep_id=False):
        if multi:
            return {"data": {"results": item}}
        else:
            if not keep_id:
                item.pop('_id', None)
        return {"data": item}


class FilterMixIn(object):
    @staticmethod
    def _filter_boolean(query, field, selector):
        if selector is None:
            return
        if selector in [True, 'true', 'True', '1']:
            selector = True
        elif selector in [False, 'false', 'False', '0']:
            selector = False
        else:
            raise InvalidSelectors('Selector is not a boolean')
        query[field] = selector

    @staticmethod
    def _filter_list(query, field, selector):
        if selector is None:
            return
        if type(selector) is not list:
            selector = list(set(selector.split(',')))
        query[field] = {'$in': selector}

    @staticmethod
    def _filter_list_uuid(query, field, selector):
        if selector is None:
            return
        if type(selector) is not list:
            selector = list(set(selector.split(',')))
        uuid_selector = list()
        for _id in selector:
            uuid_selector.append(Binary(uuid.UUID(_id).bytes, STANDARD))
        query[field] = {'$in': uuid_selector}

    @staticmethod
    def _filter_re(query, field, selector):
        if selector is None:
            return
        query[field] = {'$regex': selector}


class ProjectionMixIn(object):
    def __init__(self):
        self.projection_fields = {}

    def _projection(self, fields=None):
        if not fields:
            return self.projection_fields
        fields = fields.split(sep=',')
        for field in fields:
            if field not in self.projection_fields:
                raise InvalidFields('{0} is not a valid field'.format(field))
        result = {}
        for field in fields:
            result[field] = 1
        return result


class PaginationSkipMixIn(object):
    pagination_limit = 1000
    pagination_steps = [10, 25, 50, 100, 250, 500, 1000]

    def _pagination_skip(self, page=None, limit=None):
        if not page:
            page = 0
        else:
            try:
                page = int(page)
                if page < 1:
                    raise ValueError
            except ValueError:
                raise InvalidParameterValue("got {0} expected integer for parameter page".format(page))
        if not limit:
            limit = self.pagination_limit
        else:
            try:
                limit = int(limit)
                if limit < 1:
                    raise ValueError
            except ValueError:
                raise InvalidPaginationLimit(self.pagination_steps)
        return page * limit

    def _pagination_limit(self, limit=None):
        if not limit:
            limit = self.pagination_limit
        else:
            limit = int(limit)
            if limit not in self.pagination_steps:
                raise InvalidPaginationLimit(self.pagination_steps)
        return limit


class SortMixIn(object):
    sort_fields = []

    def _sort(self, sort=None, strict_order=True):
        if not sort:
            return self.sort_fields
        result = []
        items = []
        sort = sort.split(sep=',')
        for item in sort:
            if item.startswith('-'):
                order = pymongo.DESCENDING
                item = item[1:]
            else:
                order = pymongo.ASCENDING
            self._sort_valid_criteria(item)
            if item not in items:
                items.append(item)
            else:
                raise InvalidSortCriteria('{0} has been specified multiple times'.format(item))
            result.append((item, order))
        if strict_order:
            result = self._sort_strict_order(result)
        return result

    def _sort_valid_criteria(self, item):
        for allowed in self.sort_fields:
            if allowed[0] == item:
                return
        raise InvalidSortCriteria('{0} is not allowed as sort criteria'.format(item))

    def _sort_strict_order(self, items):
        for element in range(len(self.sort_fields)):
            try:
                if not self.sort_fields[element][0] == items[element][0]:
                    raise InvalidSortCriteria('sort criteria number {0} should be {1} but is {2}'.format(
                        element, self.sort_fields[element][0], items[element][0]
                    ))
            except IndexError:
                items.append(self.sort_fields[element])
        return items

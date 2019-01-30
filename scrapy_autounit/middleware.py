import random
import scrapy
from pathlib import Path
from scrapy.utils.reqser import request_to_dict

from .utils import (
    add_file,
    get_project_dir,
    response_to_dict,
    get_or_create_fixtures_dir,
    parse_request,
    parse_items_with_requests,
    get_autounit_base_path,
    write_test
)


class AutounitMiddleware(object):
    def __init__(self, settings):
        if not settings.getbool('AUTOUNIT_ENABLED'):
            raise scrapy.exceptions.NotConfigured(
                'scrapy-autounit is not enabled'
            )

        self.max_fixtures = settings.getint(
            'AUTOUNIT_MAX_FIXTURES_PER_CALLBACK',
            default=10
        )
        self.max_fixtures = self.max_fixtures if self.max_fixtures >= 10 else 10

        self.base_path = get_autounit_base_path()
        Path.mkdir(self.base_path, exist_ok=True)

        self.fixture_counters = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def add_sample(self, index, fixtures_dir, data):
        filename = 'fixture%s.json' % str(index)
        path = fixtures_dir / filename
        add_file(data, path)
        write_test(path)

    def process_spider_output(self, response, result, spider):
        items = []
        for item in result: items.append(item)

        request = parse_request(response.request, spider)
        callback_name = request['callback']

        data = {
            'request': request,
            'response': response_to_dict(response),
            'items': parse_items_with_requests(items, spider)
        }

        callback_counter = self.fixture_counters.setdefault(callback_name, 0)
        self.fixture_counters[callback_name] += 1

        fixtures_dir = get_or_create_fixtures_dir(
            self.base_path,
            spider.name,
            callback_name
        )

        if callback_counter < self.max_fixtures:
            self.add_sample(callback_counter + 1, fixtures_dir, data)
        else:
            r = random.randint(0, callback_counter)
            if r < self.max_fixtures:
                self.add_sample(r + 1, fixtures_dir, data)

        return items
# coding=utf-8
# See main file for licence
#
"""
  Abstract storage/queue.
"""


import sys
import logging
_logger = logging.getLogger("doi.db")
_logger.addHandler(logging.NullHandler())

try:
    import redis
except:
    print "redis could not be imported"
    sys.exit(1)


class db(object):

    magic_sep = "@@@"

    def __init__(self, host="localhost", port=6379):
        self.db_to_process = redis.StrictRedis(host=host, port=port, db=0)
        self.db_processing = redis.StrictRedis(host=host, port=port, db=1)
        self.db_count = redis.StrictRedis(host=host, port=port, db=2)
        self.db_errors = redis.StrictRedis(host=host, port=port, db=3)

    def imported_size(self):
        c = self.db_count.get("imported")
        return int(c) if c is not None else -1

    def ok_size(self):
        c = self.db_count.get("ok")
        return int(c) if c is not None else -1

    def errors_size(self):
        return self.db_errors.dbsize()

    def processing_size(self):
        return self.db_processing.dbsize()

    def added(self, amount):
        return self.db_count.incrby("imported", amount)

    def ok(self):
        return self.db_count.incr("ok")

    def set_added(self):
        return self.db_count.set("imported", 0)

    def set_ok(self):
        return self.db_count.set("ok", 0)

    def imported(self, doi, url):
        return self.db_to_process.set(doi, url)

    def done_imported(self, doi):
        return self.db_to_process.delete(doi)

    def processing(self, doi, url):
        return self.db_processing.set(doi, url)

    def done_processing(self, doi):
        return self.db_processing.delete(doi)

    def done_errors(self, doi):
        return self.db_errors.delete(doi)

    def error(self, doi, url, problem):
        return self.db_errors.set(doi, url + db.magic_sep + problem)

    def imported_to_processed(self):
        while True:
            key = self.db_to_process.randomkey()
            value = self.db_to_process.get(key)
            if 1 != self.done_imported(key):
                continue
            self.processing(key, value)
            return key, value

    def processed_to_imported(self, doi, url):
        self.done_processing(doi)
        self.imported(doi, url)

    def error_to_processed(self, filter_re=None):
        while True:
            doi = self.db_errors.randomkey()
            v = self.db_errors.get(doi)
            msg = ""
            try:
                url, msg = v.split(self.magic_sep)
            except:
                url = v
            if filter_re is not None and filter_re.match(msg) is None:
                continue
            if 1 != self.done_errors(doi):
                continue
            self.processing(doi, url)
            return doi, url

    def error_to_processed_old_yield(self, filter_re=None):
        for doi, url, msg in self.iter_errors():
            if filter_re is not None and filter_re.match(msg) is None:
                continue
            if 1 != self.done_errors(doi):
                continue
            self.processing(doi, url)
            yield doi, url

    def processed_to_error(self, doi, url, problem):
        self.error(doi, url, problem)
        return self.done_processing(doi)

    def iter_errors(self):
        for doi in self.db_errors.scan_iter(count=1000):
            v = self.db_errors.get(doi)
            msg = ""
            try:
                url, msg = v.split(self.magic_sep)
            except:
                url = v
            yield doi, url, msg

    def iter_processing(self):
        for doi in self.db_processing.scan_iter(count=1000):
            url = self.db_processing.get(doi)
            yield doi, url

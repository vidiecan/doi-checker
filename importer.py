# coding=utf-8
# See main file for licence
#
"""
  Import doi;s
"""

import logging
from urllib2 import urlopen
import json
import time
from settings import settings
from db import db

_logger = logging.getLogger("doi.import")
_logger.addHandler(logging.NullHandler())


class api(object):
    url = "http://api.crossref.org/works?rows={rows}&offset={offset}"

    def _parse(self, resp, url):
        status = "unknown"
        try:
            data = json.loads(resp)
            status = data["status"]
            if "ok" != status:
                raise AttributeError("response status - {} - {}".format(status, url))
            data = data["message"]
        except Exception, e:
            _logger.exception(repr(e) + " happened for [%s]", url)
            raise AttributeError("response status - {} - {}".format(status, url))
        return data

    def dois_count(self):
        data = self.dois(0, 0)
        return data["total-results"]

    def dois(self, offset, rows=1000, timeout=10000):
        assert isinstance(offset, int)
        assert isinstance(rows, int)

        url = api.url.format(rows=rows, offset=offset)
        resp = urlopen(
            url,
            timeout=timeout
        )
        # items, total-results
        data = self._parse(resp.read(), url)
        return data


def main(d):
    max_repeat = settings["import"]["max_repeat"]
    crossref = api()
    queues = db(**settings["db"])

    import socket
    socket.setdefaulttimeout(settings["import"]["timeout"])

    done = queues.imported_size()
    # nothing done
    if 0 > done:
        queues.set_added()
        done = queues.imported_size()
    assert done >= 0

    dois_count = crossref.dois_count()
    _logger.info("Starting at [%d] up to [%d]", done, dois_count)
    while done < dois_count:
        data = None
        for i in range(max_repeat):
            try:
                data = crossref.dois(done)
                break
            except Exception, e:
                if i == max_repeat - 1:
                    raise e
                time.sleep(5)

        # import
        done_in_this_run = 0
        for item in data["items"]:
            queues.imported(item["DOI"], item["URL"])
            done_in_this_run += 1
            # stats
            d[item.get("prefix", "unknown")] += 1

        # store new offset
        queues.added(done_in_this_run)
        # something fishy
        if 0 == done_in_this_run:
            _logger.warning("Count has not increased [%d]", done)
            return
        done += done_in_this_run
        # from time to time update doi count
        if 0 < done and 0 == done % 100000:
            dois_count = crossref.dois_count()
            _logger.info("Done [%d] up to [%d]", done, dois_count)
        # sleep
        time.sleep(settings["import"]["min_sleep"])


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    from collections import defaultdict
    d = defaultdict(int)
    try:
        main(d)
    except Exception, e:
        _logger.exception("Exception occurred")
        raise
    finally:
        import pprint
        pprint.pprint(d)
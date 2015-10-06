# coding=utf-8
# See main file for licence
#
"""
  Live status reporting.
"""


import sys
import logging
import time
from datetime import datetime
from settings import settings
from db import db
import importer

_logger = logging.getLogger("doi.reporter")
_logger.addHandler(logging.NullHandler())


class report_sheet(object):
    """
        Abstract ggl report shit.
    """

    def __init__(self):
        from status import sheet
        self.s = sheet(
            settings["status"]["doc_key"],
            user_id=settings["status"]["user_id"],
            user_key=settings["status"]["user_key"],
        )

    def report(self, ok_size, processing_size, importer_size, errors_size, total_size):
        time_now = str(datetime.now())
        # set info
        self.s.set_wshit("progress")
        b = self.s.build_batch()
        self.s.set_cell(str(time_now), 2, 1, b)
        self.s.set_cell(str(ok_size), 2, 2, b)
        self.s.set_cell(str(importer_size), 2, 3, b)
        self.s.set_cell(str(errors_size), 2, 4, b)
        self.s.set_cell(str(processing_size), 2, 5, b)
        self.s.set_cell(str(total_size), 2, 6, b)
        self.s.exe_batch(b)


def main():
    max_repeat = settings["import"]["max_repeat"]
    queues = db(**settings["db"])
    status_sht = report_sheet()
    while True:
        ok_size = queues.ok_size()
        processing_size = queues.processing_size()
        imported_size = queues.imported_size()
        errors_size = queues.errors_size()
        total_size = importer.api().dois_count()
        for i in range(max_repeat):
            try:
                status_sht.report(
                    ok_size, processing_size, imported_size, errors_size, total_size
                )
                break
            except Exception, e:
                if i == max_repeat - 1:
                    raise e

        _logger.info("Reported [ok:%6d] [processed:%3d] [imported:%6d] [errors:%4d]...",
                     ok_size, processing_size, imported_size, errors_size)
        time.sleep(settings["status"]["min_sleep"])


def main_errors(to_show=100):
    max_repeat = settings["import"]["max_repeat"]
    queues = db(**settings["db"])
    status_sht = report_sheet()

    from collections import defaultdict
    errors = defaultdict(int)
    errors_prefix = defaultdict(int)
    for doi, url, msg in queues.iter_errors():
        if msg.startswith("IncompleteRead"):
            msg = "IncompleteRead"
        elif "IOError('http error', 401, 'Unauthorized'," in msg:
            msg = "IOError('http error', 401, 'Unauthorized',...)"
        errors[msg] += 1
        errors_prefix[doi.split("/", 2)[0]] += 1

    # first N topmost
    first_n = 20
    # show messages count
    status_sht.s.set_wshit("errors messages")
    top_n = defaultdict(list)
    for msg, count in errors.iteritems():
        top_n[count].append(msg)

    for count in sorted(top_n.keys(), reverse=True):
        for msg in top_n[count]:
            status_sht.s.add_row({
                "count": str(count),
                "message": msg,
            })

    # show prefix error count
    status_sht.s.set_wshit("errors prefix")
    top_n = defaultdict(list)
    for prefix, count in errors_prefix.iteritems():
        top_n[count].append(prefix)

    for count in sorted(top_n.keys(), reverse=True)[:first_n]:
        for prefix in top_n[count]:
            status_sht.s.add_row({
                "count": str(count),
                "prefix": prefix,
            })

    # show real errors
    status_sht.s.set_wshit("errors")
    done = 0
    for doi, url, msg in queues.iter_errors():
        done += 1
        for i in range(max_repeat):
            try:
                status_sht.s.add_row({
                    "doi": doi,
                    "url": url,
                    "error": msg,
                })
                break
            except Exception, e:
                if i == max_repeat - 1:
                    raise e
        if done > to_show:
            break


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    try:
        if 1 < len(sys.argv) and "errors" == sys.argv[1]:
            to_show = 100 if 3 > len(sys.argv) else int(sys.argv[2])
            main_errors(to_show)
        else:
            main()
    except Exception, e:
        _logger.exception("Exception occurred")
        raise
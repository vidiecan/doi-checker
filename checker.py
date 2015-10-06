# coding=utf-8
# See main file for licence
#
"""
  Check doi resolution.
"""


import logging
import os
import socket
import time
import urllib2
import cookielib
import sys
import re
import logging.config

from settings import settings
import tor

_logger = logging.getLogger("doi.checker")
_logger.addHandler(logging.NullHandler())


def check(queues, doi, url, err, use_tor=False, to_append=None):
    if os.path.exists(settings["checker"]["die"]):
        raise EOFError("Die file present - aborting...")

    last_url = url
    args = [doi, url]
    time_taken = time.time()
    msg = "ok"
    to_append = to_append or ""
    old_socket = None
    try:
        if use_tor:
            port, port_ctl = settings["checker"]["tor"]["ports"]
            pwd = open(settings["checker"]["tor"]["pwd_file"], mode="rb").read()
            old_socket = tor.new_identity(port, port_ctl, pwd)

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
            cookielib.CookieJar())
        )
        opener.addheaders = settings["checker"]["headers"]
        f = opener.open(url)

        last_url = f.url
        html = f.read()
        if use_tor and old_socket is not None:
            socket.socket = old_socket
            old_socket = None

        if 200 != f.code:
            err(args, f.url, f.fp, f.code, f.msg + to_append)

        if 2 == len(args):
           queues.ok()
        else:
           msg = "error in resolving"

        # already in error db if error
        queues.done_processing(doi)

    except tor.TorAuthException, e:
        _logger.exception("Problem - %s - %s - %s", msg, doi, last_url)
        queues.processed_to_imported(doi, url)
        msg = str(e)
        sys.exit(1)
    except Exception, e:
        if use_tor and old_socket is not None:
            socket.socket = old_socket
        msg = str(e) + to_append
        _logger.exception("Problem - %s - %s - %s", msg, doi, last_url)
        queues.processed_to_error(doi, last_url, msg)
    finally:
        time_taken = time.time() - time_taken
        _logger.info(
            "[%15s] - resolved in %ss - %s [%s]",
            doi, round(time_taken / 1000., 3), msg, last_url
        )


def main(process_errors=False):
    from db import db
    queues = db(**settings["db"])
    _logger.info("Starting with backlog of [%d]", queues.imported_size())

    import socket
    socket.setdefaulttimeout(settings["checker"]["timeout"])

    def err(doi_args, url, fp, errcode, errmsg):
        """ Check for errors in resolution. """
        if errcode in (200, 301, 302, 307):
            return
        doi_args.append(errcode)
        doi, url = doi_args[0], doi_args[1]
        queues.processed_to_error(doi, url, str(errcode))
        _logger.warning("Error fetching [%s] [%s] - %s (%s)", doi, url, errmsg, errcode)

    tor_enabled = settings["checker"]["tor"]["enabled"]
    old_errors = False
    #old_errors = True
    to_append = None
    # debugging branch for specific error checking
    if old_errors and process_errors:
        for doi, url in queues.error_to_processed_old_yield(re.compile(".*orbidden.*(?!torred)")):
            to_append = "-torred"
            check(queues, doi, url, err, tor_enabled, to_append)
            # sleep
            time.sleep(settings["checker"]["min_sleep"])

    else:
        while True:
            if not old_errors and process_errors:
                doi, url = queues.error_to_processed()
            else:
                doi, url = queues.imported_to_processed()
            check(queues, doi, url, err, tor_enabled, to_append)
            time.sleep(settings["checker"]["min_sleep"])


if __name__ == "__main__":
    logging.config.dictConfig(settings["checker"]["logger"])
    try:
        process_errors = 1 < len(sys.argv) and "errors" == sys.argv[1]
        main(process_errors)
    except Exception, e:
        _logger.exception("Exception occurred")
        raise

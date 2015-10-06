# coding=utf-8
# See main file for licence
# pylint: disable=W0401,W0403
#
# by jm
"""
    Stripped down version of google wrapper.
"""

import os
import logging

import gdata
import gdata.spreadsheet.service
import gdata.gauth
import gdata.spreadsheets.client
import gdata.spreadsheets.data
import httplib2
from oauth2client.client import SignedJwtAssertionCredentials
from googleapiclient.discovery import build

_logger = logging.getLogger("ggl")

settings = {
    "sa_id": "",
    "sa_key": "",
    "doc_key": "",
    "share_user": "",

    "scope": (
        "https://www.googleapis.com/auth/drive",
        "https://spreadsheets.google.com/feeds/",
        "https://docs.google.com/feeds/",
        "https://docs.googleusercontent.com/"
    ),
    "token_uri": "https://accounts.google.com/o/oauth2/token",
    "goo_service": ("drive", "v2"),
}


# project specifics for easier debugging
#
if os.path.exists(os.path.join(os.path.dirname(__file__), "settings.py")):
    from settings import settings as project_settings
    settings.update(project_settings)


def authorise(id=None, key=None, scope=None, uri=None):
    """
        Authorise our requests, build new service API but
        can be used with older ggl API using auth2token.
    """
    with open(key or settings["sa_key"], mode="rb") as f:
        sa_key = f.read()

    credentials = SignedJwtAssertionCredentials(
        id or settings["sa_id"],
        sa_key,
        scope or settings["scope"],
        token_uri=uri or settings["token_uri"],
    )
    http = credentials.authorize(httplib2.Http())
    auth2token = gdata.gauth.OAuth2TokenFromCredentials(credentials)
    service = build(settings["goo_service"][0], settings["goo_service"][1], http=http)
    return auth2token, service


class sheet(object):
    """
        Ggl sht.
    """

    def __init__(self, key=None, wshit=None, user_id=None, user_key=None):
        key = key or settings["doc_key"]
        auth2token, _1 = authorise(id=user_id, key=user_key)
        self.service = gdata.spreadsheets.client.SpreadsheetsClient()
        auth2token.authorize(self.service)
        self.doc_key = key
        self.wshit_id = wshit

    #
    #
    def add_wshit(self, title, w=100, h=500):
        wkshit = self.service.add_worksheet(self.doc_key, title, w, h)
        self.wshit_id = wkshit.id.text.rsplit('/', 1)[1]
        return wkshit

    def set_wshit(self, wshittitle):
        feed = self.service.get_worksheets(self.doc_key)
        wkshit = None
        for item in feed.entry:
            if item.title.text == wshittitle:
                wkshit = item
                self.wshit_id = item.id.text.rsplit('/', 1)[1]
                break
        # create new and store wshit
        if self.wshit_id is None:
            _logger.warn("Adding new work sheet")
            wkshit = self.add_wshit(wshittitle)
        return wkshit

    #
    #

    def build_batch(self):
        return gdata.spreadsheets.data.BuildBatchCellsUpdate(
            self.doc_key, self.wshit_id)

    def exe_batch(self, batch):
        return self.service.batch(batch, force=True)

    #
    #

    def add_row(self, d):
        """
            Dictionary keys must be top header keys!
        """
        entry = gdata.spreadsheets.data.ListEntry()
        for k, v in d.iteritems():
            entry.set_value(k, v)
        self.service.add_list_entry(entry, self.doc_key, self.wshit_id)

    def set_cell(self, value, row, col, batch=None):
        query = gdata.spreadsheets.client.CellQuery(
            min_row=row,
            max_row=row,
            min_col=col,
            max_col=col,
            return_empty=True
        )
        c = self.service.get_cells(self.doc_key, self.wshit_id, q=query)
        item = c.entry[0]
        item.cell.input_value = value
        if batch is not None:
            batch.add_batch_entry(
                item, item.id.text, batch_id_string=item.title.text, operation_string='update')
        else:
            self.service.update(item)

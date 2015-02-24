# -*- coding: utf-8 -*-

from cookielib import MozillaCookieJar
from json import load
from urllib import urlencode
from urllib2 import build_opener, HTTPCookieProcessor
from os import path
import logging


log = logging.getLogger("RDLog");
hndlr = logging.FileHandler("testLog.log");
log.addHandler(hndlr);
hndlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));
log.setLevel(logging.DEBUG);


class RDError(Exception):
    """
    Base class for all Real-Debrid related exceptions
    """

    DEFAULT_CODE = -100

    def __init__(self, message, code=DEFAULT_CODE):
        self.message = message
        self.code = code

    def __str__(self):
        log.error('[Error %i] %s' % (self.code, self.message));
        return '[Error %i] %s' % (self.code, self.message)


class UnrestrictionError(RDError):
    """
    Exception class representing errors that occur when trying to unrestrict a link
    """

    DEDICATED_SERVER = 3
    UNSUPPORTED = 4
    UPGRADE_NEEDED = 2
    NO_SERVER = 9
    UNAVAILABLE = 11

    @classmethod
    def fixable_errors(cls):
        """
        Get the set of errors that are not fatal
        :return:
        """
        return cls.UPGRADE_NEEDED, cls.NO_SERVER, cls.DEDICATED_SERVER


class LoginError(RDError):
    """
        Exception class representing errors that occur when trying to log into Real-Debrid
    """
    MISSING_INFO = -1
    BAD_CREDENTIALS = 1
    TOO_MANY_ATTEMPTS = 3


class RDWorker:
    """
    Worker class to perform RealDebrid related actions:
    - format login info so they can be used by RealDebrid
    - login
    - unrestricting links
    - keeping cookies
    """

    _endpoint = 'http://www.real-debrid.com/ajax/%s'

    def __init__(self, cookie_file):
        self._cookie_file = cookie_file
        self.cookies = MozillaCookieJar(self._cookie_file)

    def login(self, username, password_hash):
        """
        Log into Real-Debrid. password_hash must be a MD5-hash of the password string.
        :param username:
        :param password_hash:
        :return: :raise:
        """
        if path.isfile(self._cookie_file):
            self.cookies.load(self._cookie_file)

            for cookie in self.cookies:
                if cookie.name == 'auth' and not cookie.is_expired():
                    return  # no need for a new cookie

        # request a new cookie if no valid cookie is found or if it's expired
        opener = build_opener(HTTPCookieProcessor(self.cookies))
        headers = [
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
            ("User-Agent", "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36")
            ];
        opener.addheaders = headers;
        try:
            response = opener.open(self._endpoint % 'login.php?%s' % urlencode({'user': username, 'pass': password_hash}))
            resp = load(response)
            opener.close()

            if resp['error'] == 0:
                self.cookies.save(self._cookie_file)
            else:
                raise LoginError(resp['message'].encode('utf-8'), resp['error'])
        except Exception as e:
            raise Exception('Login failed: %s' % str(e))

    def unrestrict(self, link, password=''):
        """
        Unrestrict a download URL. Returns tuple of the unrestricted URL and the filename.
        :param link: url to unrestrict
        :param password: password to use for the unrestriction
        :return: :raise:
        """
        opener = build_opener(HTTPCookieProcessor(self.cookies))
        headers = [
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
            ("User-Agent", "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36")
            ];
        opener.addheaders = headers;
        response = opener.open(self._endpoint % 'unrestrict.php?%s' % urlencode({'link': link, 'password': password}))
        resp = load(response)
        opener.close()

        if resp['error'] == 0:
            info = resp['generated_links'][0]
            return info[2], info[0].replace('/', '_')
        else:
            raise UnrestrictionError(resp['message'].encode('utf-8'), resp['error'])
#!/usr/bin/python3

"""Module for TKL Nella service.
Code by zini 2017, API by Tieto.
"""

import sys
import getpass
import os
import datetime as dt
from urllib.parse import urljoin
from urllib.parse import urlencode

import requests


__VERSION__ = "1.0"


class NellaAuthFailedError(Exception):
    """Exception for failed authentication"""
    pass

class NellaNotAuthenticatedError(Exception):
    """Exception for situations where user tries to perform actions while not
    authenticated"""
    pass

class NellaRequestFailedError(Exception):
    """Exception for failed API request"""
    pass


class NellaUser:
    """Represents TKL user

    Attributes:
        email (str): User email address
        username (str): Username
    """
    username = ""
    email = ""

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return "<NellaUser [\"%s\", \"%s\"]>" % (self.username, self.email)

class NellaCard:
    """Represents TKL Travelcard

    Attributes:
        card_id (str): Card ID
        creation_date (datetime.datetime): Card creation date
        expiry_date (datetime.datetime): Card expiration date
        is_active (bool): Is the card active
        name (str): Card name
        number (str): Card number
        tickets (list): Ticket listing
    """
    name = ""
    number = ""
    card_id = ""
    expiry_date = None
    is_active = False
    creation_date = None
    tickets = []

    def __init__(self, name, number, card_id, expiry_date, is_active, creation_date, tickets):
        self.name = name
        self.number = number
        self.card_id = card_id
        self.expiry_date = expiry_date
        self.is_active = is_active
        self.creation_date = creation_date
        self.tickets = tickets

    def __repr__(self):
        return "<NellaCard [\"%s\", %s, %d tickets, created %s]>" % (self.name, self.number,
                                                                     len(self.tickets),
                                                                     self.creation_date)

class NellaCardTicket:
    """Represents Travelcard ticket

    Attributes:
        balance (float): Ticket balance
        balance_upd_date (datetime.datetime): Last blanace update date
        state (str): Ticket state
        type_ (str): Ticket type
        valid_areas (list): Valid zone listing
    """
    balance = 0.0
    balance_upd_date = None
    state = ""
    type_ = ""
    zones = []

    def __init__(self, balance, balance_upd_date, state, type_, zones):
        self.balance = balance
        self.balance_upd_date = balance_upd_date
        self.state = state
        self.type_ = type_
        self.zones = zones

    def __repr__(self):
        return "<NellaCardTicket [%.2f€, zones: %s]>" % (self.balance, self.zones)

class NellaClient:
    """Client for TKL Nella service

    Attributes:
        auth_url (str): URL for authentication endpoint
        backend_url (str): URL for API endpoint
        base_url (str): Base URL for auth_url and backend_url
        login_expiry_date (datetime.datetime): Login expiry date
    """
    base_url    = "https://nella.tampere.fi/mobiili/"
    auth_url    = urljoin(base_url, "oauth/token")
    backend_url = urljoin(base_url, "api/v1/")

    login_expiry_date = None

    _sess = None    # Requests session
    _session_timeout_sec = 0    # Session timeout in seconds
    _token = None   # Current login token
    _userid = None  # User ID (username)
    _lang = "en"    # ISO 639-1 language code

    _debug = False  # Print debug messages
    _debug_use_colors = False   # Print coloured debug messages

    def __init__(self, debug=False):
        """Constructor

        Args:
            debug (bool, optional): Print debug messages
        """
        self._sess = requests.Session()
        self._debug = debug

        if self._debug:
            if os.environ.get("LS_COLORS") is not None:
                # Assume that colors are fine
                self._debug_use_colors = True
            self._log("NellaClient init")
            self._log("  Base URL: %s" % self.base_url)
            self._log("  Auth URL: %s" % self.auth_url)
            self._log("  Backend URL: %s" % self.backend_url)
            self._log("  Language code: %s" % self._lang)

    def _log(self, txt):
        if self._debug:
            if self._debug_use_colors:
                print("[\033[93mDEBUG\033[0m] %s" % txt)
            else:
                print("[DEBUG] %s" % txt)

    def _refresh_session(self):
        with open(".nellatoken", "w") as f:
            f.write(self._token)
        self.login_expiry_date = dt.datetime.now() + \
                                 dt.timedelta(seconds=self._session_timeout_sec)

    def auth(self, user, passwd, use_cached=True):
        """Authenticates user against auth server

        Args:
            user (str): Username
            passwd (str): Password
            use_cached (bool, optional): Whether to use token caching

        Returns:
            bool: True if authentication was successful

        Raises:
            NellaAuthFailedException: If authentication fails
        """

        # Use cached token if permitted
        if use_cached:
            if os.path.isfile(".nellatoken"):
                # Token file found
                try:
                    token = ""
                    with open(".nellatoken", "r") as f:
                        token = f.readline().strip()
                    ts = dt.datetime.fromtimestamp(os.path.getmtime(".nellatoken"))
                    diff = (dt.datetime.now() - ts).total_seconds()
                    self._log("Token age: %d" % diff)
                    hour_diff = diff / 60 / 60
                    if hour_diff >= 2:
                        # Too old cached token
                        self._log("Cached token was too old, requesting new")
                        os.remove(".nellatoken")
                    else:
                        # Cached token, test
                        self._log("Testing cached token")
                        self._token = token
                        self._userid = user
                        try:
                            self._do_request("user/%s" % user)
                        except NellaRequestFailedError:
                            # Cached token was invalid
                            self._log("Cached token was invalid, requesting new")
                            self._token = None
                            self._userid = None
                        else:
                            self._log("Cached token was valid, using")
                            self._session_timeout_sec = 7200    # 2 hours
                            self._refresh_session()
                            self.login_expiry_date = dt.datetime.now() + \
                                                     dt.timedelta(seconds=\
                                                        self._session_timeout_sec - diff)
                            return True
                except Exception as e:
                    self._log("Couldn't read token from cache: %s" % e)

        payload = {
            "username": user,
            "password": passwd,
            "grant_type": "password"
        }

        self._log("Authenticating user \"%s\"" % user)

        req = self._sess.post(self.auth_url, data=payload)

        if req.status_code != 200:
            # Auth failed
            self._log("Auth failed with HTTP status %d" % req.status_code)
            j = None
            try:
                j = req.json()
            except ValueError:
                pass

            # Remove cached token
            try:
                os.remove(".nellatoken")
            except:
                pass

            if j is not None:
                self._log("  Error: %s" % j.get("error"))
                self._log("  Description: %s" % j.get("error_description"))
                raise NellaAuthFailedError("Authentication failed: %s"
                                           % j.get("error_description"))
            else:
                raise NellaAuthFailedError("Authentication failed")

        # Auth successful
        self._log("Authentication successful for user \"%s\"" % user)
        self._log("Auth response: %s" % req.text)

        j = req.json()

        self._token = j.get("access_token")
        self._session_timeout_sec = j.get("expires_in")
        self._refresh_session()
        self._userid = user

        return True

    def logout(self):
        """Removes cached token"""
        # TODO: Is there a logout API method?
        try:
            os.remove(".nellatoken")
        except:
            pass
        self._session_timeout_sec = 0
        self._token = None
        self._userid = None
        self.login_expiry_date = None

    def _do_request(self, url, payload=None, method="get"):
        """Performs API request

        Args:
            url (str): URL fragment after endpoint
            payload (dict, optional): Request payload
            method (str, optional): HTTP method, "get" or "post"

        Returns:
            dict: Response from the API

        Raises:
            NellaNotAuthenticatedError: If user is not authenticated
            NellaRequestFailedError: If API request fails
        """
        if self._token is None:
            raise NellaNotAuthenticatedError("Not authenticated")

        url = urljoin(self.backend_url, url)    # Join to endpoint URL
        url += "?%s" % urlencode({
            "lang": self._lang
        })

        self._log("API request URL: %s" % url)

        headers = {
            "Authorization": "bearer %s" % self._token, # Auth with token
            "Accept":        "application/json",        # Make API return JSON
            "Cache-Control": "no-cache",
            "Pragma":        "no-cache"
        }

        # By default do GET requests
        method_func = self._sess.get
        if method == "post":
            method_func = self._sess.post
        req = method_func(url, headers=headers, data=payload)

        self._log("API request status: %d" % req.status_code)
        self._log("API request response: %s" % req.text)

        self._refresh_session()

        try:
            j = req.json()
        except:
            # Couldn't parse as JSON
            raise NellaRequestFailedError("Request failed")

        # If request failed server side
        if req.status_code != 200:
            raise NellaRequestFailedError("Request failed")

        # Return JSON
        return j

    @staticmethod
    def _parse_api_date(date_str):
        """Parse string date to datetime instance, format
           "%Y-%m-%dT%H:%M:%S(.\\d+)?"

        Args:
            date_str (str): Datetime string to parse

        Returns:
            datetime.datetime: Datetime instance
        """
        # Ignore possible milliseconds
        split = date_str.split(".")
        date_str = split[0]

        return dt.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")

    def get_user(self, get_raw=False):
        """Get user information for currently logged in user

        Returns:
            NellaUser: User information

        Args:
            get_raw (bool, optional): Return parsed JSON response instead of NellaUser
        """
        url = "user/%s" % self._userid
        result = self._do_request(url)
        if get_raw:
            return result

        u_name = result["UserName"]
        u_email = result["Email"]
        user = NellaUser(u_name, u_email)

        return user

    def get_cards(self, get_raw=False):
        """Get cards of currently logged in user

        Returns:
            list (NellaCard): List of cards

        Args:
            get_raw (bool, optional): Return parsed JSON response instead of list of NellaCards
        """
        url = "cards/"
        result = self._do_request(url)
        if get_raw:
            return result

        cards = []
        for card in result:
            c_num = card["Number"]
            new_card = self.get_card(c_num)
            cards.append(new_card)

        self._log("Got %d card(s)" % len(cards))

        return cards

    def get_card(self, card_id, get_raw=False):
        """Get card information for given card name

        Args:
            card_id (str): Card ID
            get_raw (bool, optional): Return parsed JSON response instead of NellaCard

        Returns:
            NellaCard: Card information
        """
        url = "cards/%s" % card_id
        result = self._do_request(url)
        if get_raw:
            return result

        c_name = result["Name"]
        c_num  = result["Number"]
        c_id   = result["Id"]
        c_exp  = result["ExpiryDate"]
        c_act  = result["IsActive"]
        c_crea = result["DeliveredDate"]

        c_exp = self._parse_api_date(c_exp)
        c_crea = self._parse_api_date(c_crea)

        # Parse tickets
        c_tickets = []
        for ticket in result["Tickets"]:
            t_balance = ticket["Balance"]
            t_upd_date = ticket["BalanceUpdatedDate"]
            t_state = ticket["State"]
            t_type = ticket["TicketType"]

            t_upd_date = self._parse_api_date(t_upd_date)

            t_areas = []
            for val_area in ticket["ValidityArea"]:
                t_areas.append({
                    "from": val_area["FromZone"]["Name"],
                    "to": val_area["ToZone"]["Name"]
                })

            new_ticket = NellaCardTicket(t_balance, t_upd_date, t_state,
                                         t_type, t_areas)
            c_tickets.append(new_ticket)

        new_card = NellaCard(c_name, c_num, c_id, c_exp, c_act, c_crea, c_tickets)
        return new_card

    def get_card_products(self, card_id):
        """Get card products that can be bought

        Args:
            card_id (str): Card ID

        Returns:
            list: Raw product listing
        """
        # TODO: Return class instances
        url = "cards/products/ThatCanBeBought/%s" % card_id
        result = self._do_request(url)
        return result

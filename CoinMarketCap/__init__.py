# -*- coding: utf-8 -*-

"""Shortcut to quickly show the stats of crypto currencies of CoinmMarketCap.com

For max readability the units are omitted. The values of "Change" are the hourly, daily and weekly
changes of the price in percent. "Cap" is the market capitalisation in USD. Volume is the volume of
the last 24 hours in USD."""

from albertv0 import *
from threading import Thread, Event
from locale import format as lformat
from urllib import request
from urllib.parse import urlencode
from urllib.request import urlretrieve
import re
import os
from concurrent.futures import ThreadPoolExecutor

import json

__iid__ = "PythonInterface/v0.2"
__prettyname__ = "CoinMarketCap"
__version__ = "1.2"
__trigger__ = "cmc "
__author__ = "Manuel Schneider"
__dependencies__ = []

iconPath = os.path.dirname(__file__)+"/emblem-money.svg"
cachePath = os.path.join(cacheLocation(), __name__)
thread = None
coins = None


class Coin():
    def __init__(self, identifier, name, symbol, rank, price,
                 cap, vol, change_hour, change_day, change_week):
        self.identifier = identifier
        self.name = name
        self.symbol = symbol
        self.rank = rank
        self.price = price
        self.cap = cap
        self.vol = vol
        self.change_hour = change_hour
        self.change_day = change_day
        self.change_week = change_week


class UpdateThread(Thread):
    def __init__(self):
        super().__init__()
        self._stopevent = Event()

    def run(self):

        while True:
            url = "%s?%s" % ("https://api.coinmarketcap.com/v1/ticker/", urlencode({'limit': 0}))
            req = request.Request(url)
            with request.urlopen(req) as response:
                if self._stopevent.is_set():
                    return

                def colorize_float(value: str):
                    if value is None:
                        return value
                    elif float(value) < 0:
                        return "<font color=\"DarkRed\">%s</font>" % value
                    elif float(value) > 0:
                        return "<font color=\"DarkGreen\">%s</font>" % value
                    else:
                        return value

                # Get coin data
                data = json.load(response)
                newCoins = []
                for coindata in data:
                    cap = coindata['market_cap_usd']
                    cap = lformat("%d", float(cap), True) if cap else "?"
                    vol = coindata['24h_volume_usd']
                    vol = lformat("%d", float(vol), True) if vol else "?"
                    newCoins.append(Coin(identifier=coindata['id'],
                                         name=coindata['name'],
                                         symbol=coindata['symbol'],
                                         rank=coindata['rank'],
                                         price=coindata['price_usd'],
                                         cap=cap,
                                         vol=vol,
                                         change_hour=colorize_float(coindata['percent_change_1h']),
                                         change_day=colorize_float(coindata['percent_change_24h']),
                                         change_week=colorize_float(coindata['percent_change_7d'])))
                global coins
                coins = newCoins

            # Create cache path if not exists
            if not os.path.isdir(cachePath):
                os.mkdir(cachePath)

            # Download all the coin pictures
            for coin in coins:
                filename = "%s.png" % coin.identifier
                url = "https://files.coinmarketcap.com/static/img/coins/128x128/%s" % filename
                filePath = os.path.join(cachePath, filename)
                executor = ThreadPoolExecutor(max_workers=40)
                if not os.path.isfile(filePath):
                    executor.submit(urlretrieve, url, filePath)
                executor.shutdown()

            self._stopevent.wait(900)  # Sleep 15 min, wakeup on stop event
            if self._stopevent.is_set():
                return

    def stop(self):
        self._stop_event.set()


def initialize():
    thread = UpdateThread()
    thread.start()


def finalize():
    if thread is not None:
        thread.stop()
        thread.join()


def handleQuery(query):
    if not query.isTriggered or coins is None:
        return

    stripped = query.string.strip().lower()
    items = []
    if stripped:
        pattern = re.compile(stripped, re.IGNORECASE)
        for coin in coins:
            if coin.name.lower().startswith(stripped) or coin.symbol.lower().startswith(stripped):
                coinIconPath = os.path.join(cachePath, "%s.png" % coin.identifier)
                items.append(Item(
                    id=__prettyname__,
                    icon=coinIconPath if os.path.isfile(coinIconPath) else iconPath,
                    text="#%s %s <i>(%s) <b>%s$</b></i>" % (coin.rank, pattern.sub(lambda m: "<u>%s</u>" % m.group(0), coin.name),
                                                            pattern.sub(lambda m: "<u>%s</u>" % m.group(0), coin.symbol), coin.price),
                    subtext="Change: <i>%s/%s/%s</i>, Cap: <i>%s</i>, Volume: <i>%s</i>" % (coin.change_hour, coin.change_day, coin.change_week, coin.cap, coin.vol),
                    completion=query.rawString,
                    actions=[UrlAction("Show on CoinMarketCap website", "https://coinmarketcap.com/currencies/%s/" % coin.identifier)]
                ))
    else:
        for coin in coins:
            coinIconPath = os.path.join(cachePath, "%s.png" % coin.identifier)
            items.append(Item(
                id=__prettyname__,
                icon=coinIconPath if os.path.isfile(coinIconPath) else iconPath,
                text="#%s %s <i>(%s) <b>%s$</b></i>" % (coin.rank, coin.name, coin.symbol, coin.price),
                subtext="Change: <i>%s/%s/%s</i>, Cap: <i>%s</i>, Volume: <i>%s</i>" % (coin.change_hour, coin.change_day, coin.change_week, coin.cap, coin.vol),
                completion=query.rawString,
                actions=[UrlAction("Show on CoinMarketCap website", "https://coinmarketcap.com/currencies/%s/" % coin.identifier)]
            ))
    return items

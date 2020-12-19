import os
import json
import time
import sys
import csv
import logging as log
from datetime import datetime
from html.parser import HTMLParser

import requests

class NoSearchResultsException(Exception):
    pass

class BeckettParser(HTMLParser):
    DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
    DEFAULT_ITEMS_PER_PAGE = 1000
    
    # Before we encounter the name of a card, we must encounter
    # <li class="title">, <ul>, <li>, then the <a> containing the title.
    START = 0
    LI_TITLE = 1
    UL = 2
    LI = 3
    A = 4

    def __init__(self):
        super(BeckettParser, self).__init__()
        self.log = log
        self.state = BeckettParser.START
        self.cards = []
        self.headers = BeckettParser.DEFAULT_HEADERS
        self.items_per_page = BeckettParser.DEFAULT_ITEMS_PER_PAGE
        self._itemcheck_count = 0
    
    def handle_starttag(self, tag, attrs):
        if self.state == BeckettParser.START: 
            want = tag == 'li' and ('class', 'title') in attrs
        elif self.state == BeckettParser.LI_TITLE:
            want = tag == 'ul'
        elif self.state == BeckettParser.UL:
            want = tag == 'li'
        elif self.state == BeckettParser.LI:
            want = tag == 'a'
        else:
            want = False

        if want:
            self.state += 1
        else:
            self.state = BeckettParser.START

    def handle_data(self, data):
        if self.state == BeckettParser.A:
            new_card = data.strip()
            self.cards.append(new_card)
            print(new_card)
            print(new_card, file=sys.stderr)
            self.state = BeckettParser.START

    def set_cookies(self, cookiesfile):
        with open(cookiesfile) as infile:
            all_cookies = json.load(infile)
            self.cookies = {c['name']: c['value'] for c in all_cookies}

    def parse_one_page(self, url, saveto=None):
        r = requests.get(url, headers=self.headers, cookies=self.cookies)
        self.cookies = r.cookies

        if saveto:
            with open(saveto, 'w') as outfile:
                outfile.write(r.text)

        for line in r.text.split('\n'):
            line = line.strip()
            noitems = True
            if line.startswith('items:'):
                items = int(line.split()[-1][:-1]) # Total number of search results
                noitems = False
            elif line.startswith('itemsOnPage:'):
                itemsOnPage = int(line.split()[-1][:-1]) # Number of seach results per page
            elif line.startswith('pages:'):
                pages = int(line.split()[-1][:-1]) # Number of pages of results
            elif line.startswith('currentPage:'):
                currentPage = int(line.split()[-1][:-1]) # Current page

            self.feed(line)

        if noitems:
            raise NoSearchResultsException("No search results at {}".format(url))

        return items, itemsOnPage, pages, currentPage

    def _make_search_url(self, term=None, player=None, sport=None, year=None,
                         rowNum=1000, page=1,
                         base_url='https://www.beckett.com/search/?'):
        url = base_url
        if term:
            url += '&term={}'.format(term)
        if player:
            url += '&player={}'.format(player)
        if sport:
            url += '&sport={}'.format(sport)
        if year:
            url += '&year_start={}'.format(year)
        if rowNum:
            url += '&rowNum={}'.format(rowNum)
        if page:
            url += '&page={}'.format(page)

        return url

    def _pause_sequence(self, intro_msg, outro_msg):
        if intro_msg:
            self.log.info(intro_msg)
        self.log.info("Waiting 15 seconds...")
        time.sleep(5)
        self.log.info("Waiting 10 seconds...")
        time.sleep(5)
        self.log.info("Waiting 5 seconds...")
        time.sleep(5)
        if outro_msg:
            self.log.info(outro_msg)

    def _itemcheck(self, expected_since_last):
        new_items = len(self.cards) - self._itemcheck_count
        assert new_items == expected_since_last, "Found {} items, expected {}".format(new_items, expected_since_last)
        self._itemcheck_count = len(self.cards)

    def search(self, term, player, sport, base_url='https://www.beckett.com/search/?',
               save_outdir=None, save_fn_prefix=''):
        # Initialize, will be correct after first page is loaded
        currentPage = 1
        pages = 99
        handler_items = len(self.cards)

        while currentPage < pages:
            url = self._make_search_url(term=term, player=player, base_url=base_url,
                                        sport=sport, page=currentPage, rowNum=self.items_per_page)
            self.log.info(url)
            saveto = os.path.join(
                save_outdir,
                '{}pg{:03}_{}.html'.format(save_fn_prefix, currentPage, datetime.now().isoformat())
            )
            try:
                items, itemsOnPage, pages, currentPage = self.parse_one_page(url, saveto=saveto)
            except NoSearchResultsException as e:
                self.log.info(e)
                break

            # Check we got the expected # of items
            if currentPage != pages:
                self._itemcheck(expected_since_last=itemsOnPage)
                self._pause_sequence(
                    intro_msg="Done page {} of {}".format(currentPage, pages),
                    outro_msg="Doing page {}".format(currentPage+1),
                )
            else:
                assert len(handler.cards) == items

    def search_by_year(self, term, player, sport, save_outdir, year_from, year_to):
        """ When search returns more than 10000 results, can't view, so search by year """
        for year in range(year_from, year_to+1):
            base_url_for_year = self._make_search_url(year=year)
            self.search(
                term, player, sport, base_url=base_url_for_year,
                save_outdir=save_outdir, save_fn_prefix='yr{}'.format(year),
            )
            self._pause_sequence(
                intro_msg="Done {}".format(year),
                outro_msg="Doing {}".format(year+1) if year != year_to else "All done."
            )

if __name__ == '__main__':
    log.basicConfig(format='%(asctime)s %(message)s', level=log.INFO)
    
    handler = BeckettParser()
    handler.set_cookies('cookies.json')
    handler.search_by_year(player='414579', term='frank+thomas', sport='185223', save_outdir='raw_pages', year_from=1988, year_to=2020)

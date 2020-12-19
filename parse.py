from html.parser import HTMLParser
from urllib.request import Request, urlopen
from datetime import datetime
import csv

import requests

import json
import time
import sys

class BeckettParser(HTMLParser):
    
    # Before we encounter the name of a card, we must encounter
    # <li class="title">, <ul>, <li>, then the <a> containing the title.
    START = 0
    LI_TITLE = 1
    UL = 2
    LI = 3
    A = 4

    def __init__(self):
        super(BeckettParser, self).__init__()
        self.state = BeckettParser.START
        self.cards = []
    
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

if __name__ == '__main__':
    handler = BeckettParser()
    orig_url = f'https://www.beckett.com/search/?term=frank+thomas+&player=414579&sport=185223&rowNum=1000&page=1' # removed '&set_type=204'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
    url = orig_url

    # Load cookies
    with open('cookies.json') as infile:
        all_cookies = json.load(infile)
        cookies = {c['name']: c['value'] for c in all_cookies}
    
    # Initialize, will be corrected after first page is loaded
    handler_items = 0
    currentPage = 1
    pages = 99

    while currentPage < pages:
        r = requests.get(url, headers=headers, cookies=cookies)
        cookies = r.cookies

        outfn = 'raw_pages/pg{:03}_{}.html'.format(currentPage, datetime.now().isoformat())
        with open(outfn, 'w') as outf:
            outf.write(r.text)

        for line in r.text.split('\n'):
            line = line.strip()
            if line.startswith('items:'):
                items = int(line.split()[-1][:-1]) # Total number of search results
            elif line.startswith('itemsOnPage:'):
                itemsOnPage = int(line.split()[-1][:-1]) # Number of seach results per page
            elif line.startswith('pages:'):
                pages = int(line.split()[-1][:-1]) # Number of pages of results
            elif line.startswith('currentPage:'):
                currentPage = int(line.split()[-1][:-1]) # Current page

            handler.feed(line)

        # Check correct # items
        if currentPage != pages:
            new_items = len(handler.cards) - handler_items
            assert new_items == itemsOnPage, "Found {} items on page {}, expected {}".format(
                new_items, currentPage, itemsOnPage)
            handler_items = len(handler.cards)
        else:
            assert len(handler.cards) == items
        
        url = orig_url[:-1] + str(currentPage + 1)

        print("Done page {}".format(currentPage), file=sys.stderr)

        print("15")
        time.sleep(5)
        print("10")
        time.sleep(5)
        print("5")
        time.sleep(5)
        print("doing next page")

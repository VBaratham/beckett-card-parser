from html.parser import HTMLParser
from urllib.request import Request, urlopen
import requests

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
            print(self.state)
        else:
            self.state = BeckettParser.START

    def handle_data(self, data):
        if self.state == BeckettParser.A:
            self.cards.append(str(data).strip())
            self.state = BeckettParser.START

if __name__ == '__main__':
    handler = BeckettParser()
    url = 'https://www.beckett.com/search/?term=frank+thomas&player=414579&sport=185223&team=370834&set_type=202|201&rowNum=500&page=1'

    handler_items = 0
    currentPage = 1
    pages = 99 # will be corrected after first page is loaded

    while currentPage < pages:
        req = Request(
                url,
                data=None,
                headers={
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
                        }
            )
        print("Getting {}".format(req.get_full_url()))

        for line in urlopen(req).readlines():
            line = line.decode('utf-8').strip()
            if line.startswith('items:'):
                items = int(line.split()[-1][:-1]) # Total number of search results
            elif line.startswith('itemsOnPage:'):
                itemsOnPage = int(line.split()[-1][:-1]) # Number of seach results per page
            elif line.startswith('pages:'):
                pages = int(line.split()[-1][:-1]) # Number of pages of results
            elif line.startswith('currentPage:'):
                currentPage = int(line.split()[-1][:-1]) # Current page

            print(line)
            handler.feed(line)

        # Check correct # items
        new_items = len(handler.cards) - handler_items
        import ipdb; ipdb.set_trace()
        assert new_items == itemsOnPage, "Found {} items on page {}, expected {}".format(
            new_items, currentPage, itemsOnPage)
        handler_items = len(handler.cards)
        
        url = url[:-1] + str(currentPage + 1)

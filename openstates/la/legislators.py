import re

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import scrapelib
import lxml.html


class LALegislatorScraper(LegislatorScraper):
    state = 'la'

    def scrape(self, chamber, term):
        if term != self.metadata['terms'][-1]['name']:
            raise NoDataForPeriod(term)

        list_url = "http://www.legis.state.la.us/bios.htm"
        with self.urlopen(list_url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(list_url)

            if chamber == 'upper':
                contains = 'senate'
            else:
                contains = 'house'

            for a in page.xpath("//a[contains(@href, '%s')]" % contains):
                name = a.text.strip().decode('utf8')
                leg_url = a.attrib['href']
                try:
                    if chamber == 'upper':
                        self.scrape_senator(name, term, leg_url)
                    else:
                        self.scrape_rep(name, term, leg_url)
                except scrapelib.HTTPError:
                    self.warning('Unable to retrieve legislator %s (%s) ' % (
                        name, leg_url))

    def scrape_rep(self, name, term, url):
        # special case names that confuses name_tools
        if name == 'Franklin, A.B.':
            name = 'Franklin, A. B.'
        elif ', Jr., ' in name:
            name = name.replace(', Jr., ', ' ')
            name += ', Jr.'
        elif ', III, ' in name:
            name = name.replace(', III, ', ' ')
            name += ', III'

        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            district = page.xpath(
                "//a[contains(@href, 'district')]")[0].attrib['href']
            district = re.search("district(\d+).pdf", district).group(1)

            if "Democrat&nbsp;District" in text:
                party = "Democratic"
            elif "Republican&nbsp;District" in text:
                party = "Republican"
            elif "Independent&nbsp;District" in text:
                party = "Independent"
            else:
                party = "Other"

            leg = Legislator(term, 'lower', district, name, party=party,
                             url=url)
            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_senator(self, name, term, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            district = page.xpath(
                "string(//*[starts-with(text(), 'Senator ')])")

            district = re.search(r'District (\d+)', district).group(1)

            try:
                party = page.xpath(
                    "//b[contains(text(), 'Party')]")[0].getnext().tail
                party = party.strip()
            except IndexError:
                party = 'N/A'

            if party == 'No Party (Independent)':
                party = 'Independent'
            elif party == 'Democrat':
                party = 'Democratic'

            leg = Legislator(term, 'upper', district, name, party=party,
                             url=url)
            leg.add_source(url)
            self.save_legislator(leg)

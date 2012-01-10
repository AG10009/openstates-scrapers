import re
import urlparse
import htmlentitydefs

from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import clean_committee_name, DBFMixin

import scrapelib
from dbfpy import dbf

class NJLegislatorScraper(LegislatorScraper, DBFMixin):
    state = 'nj'

    def scrape(self, chamber, term):
        year = term[0:4]
        if chamber == 'upper':
            self.scrape_legislators(year, term)
        elif chamber == 'lower':
            self.scrape_legislators(year, term)

    def scrape_legislators(self, year_abr, term_name):

        file_url, db = self.get_dbf(year_abr, 'ROSTER')

        for rec in db:
            first_name = rec["firstname"]
            middle_name = rec["midname"]
            last_name = rec["lastname"]
            suffix = rec["suffix"]
            full_name = first_name + " " + middle_name + " " + last_name + " " + suffix
            full_name = full_name.replace('  ', ' ')
            full_name = full_name[0: len(full_name) - 1]

            district = int(rec["district"])
            party = rec["party"]
            if party == 'R':
                party = "Republican"
            elif party == 'D':
                party = "Democratic"
            else:
                party = party
            chamber = rec["house"]
            if chamber == 'A':
                chamber = "lower"
            elif chamber == 'S':
                chamber = "upper"

            title = rec["title"]
            legal_position = rec["legpos"]
            leg_status = rec["legstatus"]
            address = rec["address"]
            city = rec["city"]
            state = rec["state"]
            zipcode = rec["zipcode"]
            phone = rec["phone"]
            if 'email' in rec:
                email = rec["email"]
            else:
                email = ''

            leg = Legislator(term_name, chamber, str(district), full_name,
                             first_name, last_name, middle_name, party,
                             suffixes=suffix, title=title,
                             legal_position=legal_position,
                             leg_status=leg_status, address=address, city=city,
                             state=state, zipcode=zipcode, phone=phone,
                             email=email)
            leg.add_source(file_url)
            self.save_legislator(leg)

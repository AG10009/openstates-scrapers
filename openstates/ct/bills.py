import re
import csv
import datetime
from operator import itemgetter
from collections import defaultdict

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from billy.scrape import NoDataForPeriod
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.ct.utils import parse_directory_listing

import lxml.html


class CTBillScraper(BillScraper):
    state = 'ct'

    _committee_names = {}
    _introducers = defaultdict(set)

    def __init__(self, *args, **kwargs):
        super(CTBillScraper, self).__init__(*args, **kwargs)
        self.scrape_committee_names()
        self.scrape_introducers('upper')
        self.scrape_introducers('lower')

    def scrape(self, chamber, session):
        if session != '2011':
            raise NoDataForPeriod(session)

        self.bills = {}
        self.scrape_bill_info(chamber, session)
        self.scrape_bill_history()
        self.scrape_versions(chamber, session)

        for bill in self.bills.itervalues():
            self.save_bill(bill)

    def scrape_bill_info(self, chamber, session):
        info_url = "ftp://ftp.cga.ct.gov/pub/data/bill_info.csv"
        page = self.urlopen(info_url)
        page = csv.DictReader(StringIO.StringIO(page))

        abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        for row in page:
            bill_id = row['bill_num']
            if not bill_id[0] == abbrev:
                continue

            if re.match(r'^(S|H)J', bill_id):
                bill_type = 'joint resolution'
            elif re.match(r'^(S|H)R', bill_id):
                bill_type = 'resolution'
            else:
                bill_type = 'bill'

            bill = Bill(session, chamber, bill_id, row['bill_title'],
                        type=bill_type)
            bill.add_source(info_url)

            self.scrape_bill_page(bill)

            for introducer in self._introducers[bill_id]:
                    bill.add_sponsor('introducer', introducer)

            self.bills[bill_id] = bill

    def scrape_bill_page(self, bill):
        url = ("http://www.cga.ct.gov/asp/cgabillstatus/"
               "cgabillstatus.asp?selBillType=Bill"
               "&bill_num=%s&which_year=%s" % (bill['bill_id'],
                                               bill['session']))
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)
            bill.add_source(url)

            for link in page.xpath("//a[contains(@href, '/FN/')]"):
                bill.add_document(link.text.strip(), link.attrib['href'])

            for link in page.xpath("//a[contains(@href, '/BA/')]"):
                bill.add_document(link.text.strip(), link.attrib['href'])

            for link in page.xpath("//a[contains(@href, 'VOTE')]"):
                self.scrape_vote(bill, link.text.strip(),
                                 link.attrib['href'])

            subject_link = page.xpath("//a[contains(@href, 'Similar')]")[0]
            self.scrape_subjects(bill, subject_link.attrib['href'])

    def scrape_vote(self, bill, name, url):
        if "VOTE/H" in url:
            vote_chamber = 'lower'
            cols = (1, 5, 9, 13)
            name_offset = 3
            yes_offset = 0
            no_offset = 1
        else:
            vote_chamber = 'upper'
            cols = (1, 6)
            name_offset = 4
            yes_offset = 1
            no_offset = 2

        with self.urlopen(url) as page:
            if 'BUDGET ADDRESS' in page:
                return

            page = lxml.html.fromstring(page)

            yes_count = page.xpath(
                "string(//span[contains(., 'Those voting Yea')])")
            yes_count = int(re.match(r'[^\d]*(\d+)[^\d]*', yes_count).group(1))

            no_count = page.xpath(
                "string(//span[contains(., 'Those voting Nay')])")
            no_count = int(re.match(r'[^\d]*(\d+)[^\d]*', no_count).group(1))

            other_count = page.xpath(
                "string(//span[contains(., 'Those absent')])")
            other_count = int(re.match(r'[^\d]*(\d+)[^\d]*', other_count).group(1))

            need_count = page.xpath(
                "string(//span[contains(., 'Necessary for')])")
            need_count = int(re.match(r'[^\d]*(\d+)[^\d]*', need_count).group(1))

            date = page.xpath("string(//span[contains(., 'Taken on')])")
            date = re.match(r'.*Taken\s+on\s+(\d+/\s?\d+)', date).group(1)
            date = date.replace(' ', '')
            date = datetime.datetime.strptime(date + " " + bill['session'],
                                              "%m/%d %Y").date()

            vote = Vote(vote_chamber, date, name, yes_count > need_count,
                        yes_count, no_count, other_count)
            vote.add_source(url)

            table = page.xpath("//table")[0]
            for row in table.xpath("tr"):
                for i in cols:
                    name = row.xpath("string(td[%d])" % (
                        i + name_offset)).strip()

                    if not name:
                        continue

                    if "Y" in row.xpath("string(td[%d])" %
                                        (i + yes_offset)):
                        vote.yes(name)
                    elif "N" in row.xpath("string(td[%d])" %
                                          (i + no_offset)):
                        vote.no(name)
                    else:
                        vote.other(name)

            bill.add_vote(vote)

    def scrape_subjects(self, bill, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            bill['subjects'] = [td.text.replace('&nbsp', '').strip()
                                for td in page.xpath("//td[@colspan='4']")]

    def scrape_bill_history(self):
        history_url = "ftp://ftp.cga.ct.gov/pub/data/bill_history.csv"
        page = self.urlopen(history_url)
        page = csv.DictReader(StringIO.StringIO(page))

        action_rows = defaultdict(list)

        for row in page:
            bill_id = row['bill_num']

            if bill_id in self.bills:
                action_rows[bill_id].append(row)

        for (bill_id, actions) in action_rows.iteritems():
            bill = self.bills[bill_id]

            actions.sort(key=itemgetter('act_date'))
            act_chamber = bill['chamber']

            for row in actions:
                date = row['act_date']
                date = datetime.datetime.strptime(
                    date, "%Y-%m-%d %H:%M:%S").date()

                action = row['act_desc'].strip()
                act_type = []

                match = re.search('COMM(ITTEE|\.) ON$', action)
                if match:
                    comm_code = row['qual1']
                    comm_name = self._committee_names.get(comm_code,
                                                          comm_code)
                    action = "%s %s" % (action, comm_name)
                    act_type.append('committee:referred')
                elif row['qual1']:
                    if bill['session'] in row['qual1']:
                        action += ' (%s' % row['qual1']
                        if row['qual2']:
                            action += ' %s)' % row['qual2']
                    else:
                        action += ' %s' % row['qual1']

                match = re.search(r'REFERRED TO OLR, OFA (.*)',
                                  action)
                if match:
                    action = ('REFERRED TO Office of Legislative Research'
                              ' AND Office of Fiscal Analysis %s' % (
                                  match.group(1)))

                if re.match(r'^ADOPTED, (HOUSE|SENATE)', action):
                    act_type.append('bill:passed')

                match = re.match(r'^Joint ((Un)?[Ff]avorable)', action)
                if match:
                    act_type.append('committee:passed:%s' % match.group(1))

                if not act_type:
                    act_type = ['other']

                bill.add_action(act_chamber, action, date,
                                type=act_type)

                if 'TRANS.TO HOUSE' in action:
                    act_chamber = 'lower'

                if 'TRANSMITTED TO SENATE' in action:
                    act_chamber = 'upper'

    def scrape_versions(self, chamber, session):
        chamber_letter = {'upper': 's', 'lower': 'h'}[chamber]
        versions_url = "ftp://ftp.cga.ct.gov/%s/tob/%s/" % (
            session, chamber_letter)

        with self.urlopen(versions_url) as page:
            files = parse_directory_listing(page)

            for f in files:
                match = re.match(r'^\d{4,4}([A-Z]+-\d{5,5})-(R\d\d)',
                                 f.filename)
                bill_id = match.group(1).replace('-', '')

                try:
                    bill = self.bills[bill_id]
                except KeyError:
                    continue

                url = versions_url + f.filename
                bill.add_version(match.group(2), url)

    def scrape_committee_names(self):
        comm_url = "ftp://ftp.cga.ct.gov/pub/data/committee.csv"
        page = self.urlopen(comm_url)
        page = csv.DictReader(StringIO.StringIO(page))

        for row in page:
            comm_code = row['comm_code'].strip()
            comm_name = row['comm_name'].strip()
            comm_name = re.sub(r' Committee$', '', comm_name)
            self._committee_names[comm_code] = comm_name

    def scrape_introducers(self, chamber):
        chamber_letter = {'upper': 's', 'lower': 'h'}[chamber]
        url = "http://www.cga.ct.gov/asp/menu/%slist.asp" % chamber_letter

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath("//a[contains(@href, 'MemberBills')]"):
                name = link.xpath("string(../../td[1])").strip()
                name = re.match("^S?\d+\s+-\s+(.*)$", name).group(1)

                self.scrape_introducer(name, link.attrib['href'])

    def scrape_introducer(self, name, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for link in page.xpath("//a[contains(@href, 'billstatus')]"):
                bill_id = link.text.strip()
                self._introducers[bill_id].add(name)

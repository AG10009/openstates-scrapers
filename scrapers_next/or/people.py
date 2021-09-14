from spatula import URL, XmlPage, HtmlPage, CSS, SelectorError, XPath
from openstates.models import ScrapePerson
import re

# from .apiclient import OregonLegislatorODataClient
# from .utils import SESSION_KEYS


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        # this guy's html/image is different
        if p.name == "Rob Wagner":
            img = "https://www.oregonlegislature.gov/wagner/PublishingImages/member_photo.jpg"
        else:
            img = CSS("h1 img").match_one(self.root).get("src")
        p.image = img

        try:
            district_info = XPath("//p//strong[contains(text(), 'District')]").match(
                self.root
            )
            for tag in district_info:
                if re.search(r"District\sPhone:", tag.text_content()):
                    if tag.tail is None and p.name == "Boomer Wright":
                        p.district_office.voice = (
                            tag.getnext().getnext().text_content().strip()
                        )
                    elif tag.tail is None:
                        p.district_office.voice = tag.getnext().text_content().strip()
                    else:
                        p.district_office.voice = tag.tail.strip()
                elif re.search(
                    r"District(\s|\xa0)(Mailing)?\s?Address:", tag.text_content()
                ):
                    if tag.tail is None or tag.tail.strip() == "":
                        p.district_office.address = tag.getnext().text_content().strip()
                    else:
                        p.district_office.address = tag.tail.strip()
                else:
                    if (
                        tag.getnext() is not None
                        and tag.getnext().text_content().strip() == "Phone:"
                    ):
                        p.district_office.voice = tag.getnext().tail.strip()
                    elif tag.tail is not None and tag.tail.strip() == "Address:":
                        p.district_office.address = tag.getparent().tail.strip()
        except SelectorError:
            pass

        return p


class LegList(XmlPage):
    source = URL(
        "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions('2021R1')/Legislators"
    )

    def process_page(self):
        legislators = self.root[4:]
        for leg in legislators:
            content = leg[9]

            first_name = content[0][2].text
            last_name = content[0][3].text
            name = first_name.strip() + " " + last_name.strip()

            chamber = content[0][7].text
            if chamber.strip() == "H":
                chamber = "lower"
            elif chamber.strip() == "S":
                chamber = "upper"

            party = content[0][8].text
            if party.strip() == "Democrat":
                party = "Democratic"

            district = content[0][9].text

            p = ScrapePerson(
                name=name,
                state="or",
                chamber=chamber,
                district=district,
                party=party,
            )

            p.add_source(self.source.url)

            p.family_name = last_name.strip()
            p.given_name = first_name.strip()

            cap_address = content[0][4].text
            p.capitol_office.address = cap_address.strip()

            cap_phone = content[0][5].text
            if cap_phone:
                p.capitol_office.voice = cap_phone.strip()

            title = content[0][6].text
            if title.strip() not in ["Senator", "Representative"]:
                p.extras["title"] = title.strip()

            email = content[0][10].text
            p.email = email.strip()

            website = content[0][11].text
            p.add_link(website, note="homepage")
            p.add_source(website)

            # this guy's website is messed up
            if p.name == "Daniel Bonham":
                p.image = "https://www.oregonlegislature.gov/bonham/PublishingImages/member_photo.jpg"
                yield p
            else:
                yield LegDetail(p, source=website)

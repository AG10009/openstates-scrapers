import datetime

#start date of each session is the first tuesday in January after new years

metadata = dict(
    name = 'Tennessee',
    abbreviation = 'tn',
    legislature_name = 'Tennessee General Assembly',
    lower_chamber_name = 'House',
    upper_chamber_name = 'Senate',
    lower_chamber_title = 'Represenative',
    upper_chamber_title = 'Senator',
    lower_chamber_term = 2,
    upper_chamber_term = 4,
    terms = [
        {'name': '106', 'sessions' : ['106'],
            'start_year': 2009, 'end_year': 2010},
        {'name': '107', 'sessions': ['107'],
            'start_year': 2010, 'end_year': 2011} 
    ],
    session_details={
        '107': {
            'start_date' : datetime.date(2011, 1, 11),
            'end_date' : datetime.date(2012, 1, 10),
            'type' : 'primary',
            'display_name': '107th Regular Session',},
        '106': {
            'type' : 'primary',
            'display_name' : '106th Regular Session',},
    },
    feature_flags=[],
    _ignored_scraped_sessions = [
        '106th General Assembly',
        '105th General Assembly', '104th General Assembly',
        '103rd General Assembly', '102nd General Assembly',
        '101st General Assembly', '100th General Assembly',
        '99th General Assembly'
    ]
)

def session_list():
    # Special sessions are aviable in the archive, but not in current session.
    # Solution is to scrape special session as part of regular session
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.capitol.tn.gov/legislation/archives.html',
        "//div[@class='col1']/ul/li[@class='show']/text()")

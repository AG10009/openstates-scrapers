metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        #{'name': '2009-2010',
        # 'sessions': ['2009 Regular Session',
        #              '2009 First Special Session',
        #              '2009 Second Special Session',
        #              '2009 Third Special Session',
        #              '2010 Regular Session',
        #              '2010 First Special Session',
        #              '2010 Second Special Session',
        #             ],
        # 'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session',
                     ],
         'start_year': 2011, 'end_year': 2012},
     ],
    session_details={
        '2011 Regular Session': {'display_name': '2011 Regular Session'},
    },
    feature_flags=['subjects'],
    _ignored_scraped_sessions = ['2011', '2010', '2009', '2008', '2007', '2006',
        '2005', '2004', '2003', '2002', '2001', '2000', '1999']    
)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://www.capitol.hawaii.gov/archives/main.aspx',
            "//div[@class='roundedrect gradientgray shadow']/a/text()"
        )
    sessions.remove("Archives Main")
    return sessions

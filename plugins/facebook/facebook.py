#!/usr/bin/env python

import urllib2
import re
#import BeautifulSoup
#from BeautifulSoup import BeautifulStoneSoup 
from optparse import OptionParser

DOI_LOOKUP_URL = "http://dx.doi.org/%s"

SOURCE_URL = "http://api.facebook.com/restserver.php?method=links.getStats&urls=%s"
DEBUG = False

FACEBOOK_SHARE_PATTERN = re.compile("<share_count>(?P<stats>\d+)</share_count>", re.DOTALL)
FACEBOOK_LIKE_PATTERN = re.compile("<like_count>(?P<stats>\d+)</like_count>", re.DOTALL)
FACEBOOK_COMMENT_PATTERN = re.compile("<comment_count>(?P<stats>\d+)</comment_count>", re.DOTALL)
FACEBOOK_CLICK_PATTERN = re.compile("<click_count>(?P<stats>\d+)</click_count>", re.DOTALL)

def get_redirect_url(doi):
    if not doi:
        return(None)
    doi_url = DOI_LOOKUP_URL % doi
    doi_redirect_url = urllib2.urlopen(doi_url).url
    
    #if (DEBUG):
    #    print doi_url
    #    print doi_redirect_url
    
    return(doi_redirect_url)    

def get_page(lookup):
    if not lookup:
        return(None)
    url = SOURCE_URL % lookup
    #if (DEBUG):
    #    print url
    page = urllib2.urlopen(url).read()
    #if (DEBUG):
    #    print page
    return(page) 
    
def get_stats(page):
    if not page:
        return(None)
    #print page
    if (False):
        soup = BeautifulStoneSoup(page)
        like_count = soup.like_count.text
        share_count = soup.share_count.text
        click_count = soup.click_count.text
        comment_count = soup.comment_count.text
        
    matches = FACEBOOK_SHARE_PATTERN.search(page)
    share_count = matches.group("stats")
        
    matches = FACEBOOK_LIKE_PATTERN.search(page)
    like_count = matches.group("stats")
        
    matches = FACEBOOK_COMMENT_PATTERN.search(page)
    comment_count = matches.group("stats")
        
    matches = FACEBOOK_CLICK_PATTERN.search(page)
    click_count = matches.group("stats")
        
    stats = {"like count":like_count, "share count":share_count, "click_count":click_count, "comment_count":comment_count}
    return(stats)  



def main():
    parser = OptionParser(usage="usage: %prog [options] filename",
                          version="%prog 1.0")
    #parser.add_option("-x", "--xhtml",
    #                  action="store_true",
    #                  dest="xhtml_flag",
    #                  default=False,
    #                  help="create a XHTML template instead of HTML")
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("wrong number of arguments")

    #print options
    #print args
    
    id = args[0]
    redirect_url = get_redirect_url(id)
    page = get_page(redirect_url)
    response = get_stats(page)
   
    print response
    return(response)


if __name__ == '__main__':
    main()  
          
#test_input = "10.1371/journal.pcbi.1000361"
#test_input = "10.1371/journal.pmed.0040215"
#test_input = "10.1371/journal.pone.0000308"

#redirect_url = get_redirect_url(test_input)
#page = get_page(redirect_url)
#stats = get_stats(page)
#print stats
#!/usr/bin/env python

# Conforms to API specified here:  https://github.com/mhahnel/Total-Impact/wiki/Plugin-requirements

import re
from BeautifulSoup import BeautifulStoneSoup
from optparse import OptionParser
import string
import simplejson
import time
import nose
from nose.tools import assert_equals
import httplib2
    
def skip(f):
    f.skip = True
    return f
                
# To do automated tests with nosy                
# nosy plugin.py -A \'not skip\'
                
SOURCE_NAME = "CrossRef"
SOURCE_DESCRIPTION = "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."
SOURCE_URL = "http://www.crossref.org/"
SOURCE_ICON = "http://www.crossref.org/favicon.ico"
SOURCE_METRICS = dict(  journal="the journal where the paper was published",
                        year="the year of the publication",
                        title="the title of the publication", 
                        authors="the authors of the publication", 
                        doi="the DOI of the publication, if applicable",
                        url="the url of the full text of the publication",
                        pmid="the PubMed identifier of the publication, if applicable")


TEST_GOLD_ABOUT = {'metrics': {'doi': 'the DOI of the publication, if applicable', 'title': 'the title of the publication', 'url': 'the url of the full text of the publication', 'journal': 'the journal where the paper was published', 'authors': 'the authors of the publication', 'year': 'the year of the publication', 'pmid': 'the PubMed identifier of the publication, if applicable'}, 'url': 'http://www.crossref.org/', 'icon': 'http://www.crossref.org/favicon.ico', 'desc': 'An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation.'}
TEST_GOLD_JSON_RESPONSE_STARTS_WITH = '{"artifacts": {}, "about": {"metrics": {"date": "the date of the publication", "doi": "the DOI of the publication, if applicable", "title": "the title of the publication", "url": "the url of the full text of the publication", "journal": "the journal where the paper was published", "pmid": "the PubMed identifier of the publication, if applicable"}, "url": "http://www.crossref.org/", "icon": "http://www.crossref.org/favicon.ico", "desc": "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."}, "error": "false", "source_name": "CrossRef", "last_update": 130'
TEST_INPUT = '{"10.1371/journal.pcbi.1000361":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}'
TEST_GOLD_PARSED_INPUT = {u'10.1371/journal.pcbi.1000361': {u'url': u'FALSE', u'pmid': u'FALSE', u'doi': u'FALSE'}}
TEST_INPUT_DOI = {"10.1371/journal.pcbi.1000361":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}
TEST_INPUT_BAD_DOI = {"10.1371/abc.abc.123":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}
TEST_INPUT_PMID = {"17808382":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}
TEST_INPUT_URL = {"http://onlinelibrary.wiley.com/doi/10.1002/asi.21512/abstract":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}
TEST_INPUT_DUD = {"NotAValidID":{"doi":"FALSE","url":"FALSE","pmid":"FALSE"}}
TEST_INPUT_ALL = TEST_INPUT_DUD.copy()
TEST_INPUT_ALL.update(TEST_INPUT_URL)
TEST_INPUT_ALL.update(TEST_INPUT_PMID)
TEST_INPUT_ALL.update(TEST_INPUT_DOI)
TEST_INPUT_ALL.update(TEST_INPUT_BAD_DOI)

DOI_LOOKUP_URL = "http://dx.doi.org/%s"
DEBUG = False

MAX_ELAPSED_TIME = 30 # seconds, part of plugin API specification

# All CrossRef DOI prefixes begin with "10" followed by a number of four or more digits
#f rom http://www.crossref.org/02publishers/doi-guidelines.pdf
CROSSREF_DOI_PATTERN = re.compile(r"^10\.(\d)+/(\S)+$", re.DOTALL)

# PMIDs are 1 to 8 digit numbers, as per http://www.nlm.nih.gov/bsd/mms/medlineelements.html#pmid    
PMID_PATTERN = re.compile(r"^\d{1,8}$", re.DOTALL)


# each plugin needs to write one of these    
def get_page(doi):
    if not doi:
        return(None)
    url = DOI_LOOKUP_URL % doi
    if (DEBUG):
        print url
    try:
        page = get_cache_timeout_response(url, header_addons={'Accept':'application/unixref+xml'})
        if (DEBUG):
            print page
    except:
        page = None
    return(page)

# plugin-specific helper function
def get_doi_from_pmid(pmid):
    TOOL_EMAIL = "total-impact@googlegroups.com"
    url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s&retmode=xml&email=%s" % (pmid, TOOL_EMAIL)
    (response, xml) = get_cache_timeout_response(url)
    try:
        doi = re.search('<ArticleId IdType="doi">(?P<doi>.*?)</ArticleId>', xml).group("doi")
    except:
        doi = ""
    return(doi)

# plugin-specific helper function
def get_pmid_from_doi(doi):
    TOOL_EMAIL = "total-impact@googlegroups.com"
    url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?term=%s&email=%s" % (doi, TOOL_EMAIL)
    (response, xml) = get_cache_timeout_response(url)
    try:
        pmid = re.search("<Id>(?P<pmid>\d*)</Id>", xml).group("pmid")
    except:
        pmid = ""
    return(pmid)
    
# each plugin needs to write one of these    
## curl -D - -L -H "Accept: application/unixref+xml" "http://dx.doi.org/10.1126/science.1157784" 
def extract_stats(page, doi):
    ## curl -D - -L -H "Accept: application/unixref+xml" "http://dx.doi.org/10.1126/science.1157784" 
    if not page:
        return(None)        
    (response_header, content) = page
    
    soup = BeautifulStoneSoup(content)
    try:
        title = str(soup.title.text)
        if (title == "DOI Not Found"):
            return(None)
    except:
        title = ""

    try:
        year = str(soup.year.text)
    except:
        year = ""        
        
    try:
        journal = str(soup.abbrev_title.text)
    except:
        journal = ""
        
    try:
        authors = ", ".join([str(a.surname.text) for a in soup.findAll(contributor_role="author")])
    except:
        authors = ""
    
    # To get full text, try to follow the doi url then get the final landing page
    doi_initial_url = DOI_LOOKUP_URL % doi
    try:
        (redirected_header, redirected_page) = get_cache_timeout_response(doi_initial_url)
        url = redirected_header["content-location"]
    except:
        url = ""
       
    response = dict(url=url, title=title, journal=journal, year=year, authors=authors)
    return(response)  

# each plugin needs to write relevant versions of this
def is_crossref_doi(id):
    response = (CROSSREF_DOI_PATTERN.search(id) != None)
    return(response)

# each plugin needs to write relevant versions of this    
def is_pmid(id):
    response = (PMID_PATTERN.search(id) != None)
    return(response)
            
# each plugin needs to write relevant versions of this
def artifact_type_recognized(id):
    is_recognized = (is_crossref_doi(id) or is_pmid(id))
    return(is_recognized)   
            
## this changes for every plugin        
def test_build_artifact_response():
    response = build_artifact_response('10.1371/journal.pcbi.1000361')
    assert_equals(response, {'doi': '10.1371/journal.pcbi.1000361', 'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'url': 'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361', 'journal': 'PLoS Comput Biol', 'authors': 'Shotton, Portwin, Klyne, Miles', 'year': '2009', 'pmid': '19381256', 'type': 'article'})
        
## this changes for every plugin        
def build_artifact_response(artifact_id):
    if is_crossref_doi(artifact_id):
        doi = artifact_id
        pmid = get_pmid_from_doi(doi)
    elif is_pmid(artifact_id):
        pmid = artifact_id
        doi = get_doi_from_pmid(pmid)
    if not is_crossref_doi(doi):
        return(None)
    metrics_response = get_metric_values(doi)
    if not pmid and not metrics_response:
        return(None)
    response = dict(type="article", pmid=pmid, doi=doi)    
    if metrics_response:
        response.update(metrics_response)
    return(response)

## this changes for every plugin        
def test_get_artifacts_metrics():
    response = get_artifacts_metrics(TEST_GOLD_PARSED_INPUT)
    assert_equals(response, ({u'10.1371/journal.pcbi.1000361': {'doi': u'10.1371/journal.pcbi.1000361', 'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'url': 'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361', 'journal': 'PLoS Comput Biol', 'authors': 'Shotton, Portwin, Klyne, Miles', 'year': '2009', 'pmid': '19381256', 'type': 'article'}}, None))
    
## every plugin should check API limitations and make sure they are respected here    
## Crossref API doesn't seem to have limits, though we should check every few months to make sure still true            
def get_artifacts_metrics(query):
    response_dict = dict()
    error_msg = None
    time_started = time.time()
    for artifact_id in query:
        if artifact_type_recognized(artifact_id):
            artifact_response = build_artifact_response(artifact_id)
            if artifact_response:
                response_dict[artifact_id] = artifact_response
        if (time.time() - time_started > MAX_ELAPSED_TIME):
            error_msg = "TIMEOUT"
            break
    return(response_dict, error_msg)

def test_parse_input():
    response = parse_input(TEST_INPUT)
    assert_equals(response, TEST_GOLD_PARSED_INPUT)
        
def parse_input(json_in):
    query = simplejson.loads(json_in)
    return(query)
                
def test_build_about():
    response = build_about()
    assert_equals(response, TEST_GOLD_ABOUT)

def build_about():
    response = dict(desc=SOURCE_DESCRIPTION,
                            url=SOURCE_URL, 
                            icon=SOURCE_ICON, 
                            metrics=SOURCE_METRICS)
    return(response)
        
def test_build_json_response():
    response = build_json_response()
    response_no_timestamp = re.sub('130\d+', '130', response)
    assert_equals(response_no_timestamp, '{"about": {"metrics": {"doi": "the DOI of the publication, if applicable", "title": "the title of the publication", "url": "the url of the full text of the publication", "journal": "the journal where the paper was published", "authors": "the authors of the publication", "year": "the year of the publication", "pmid": "the PubMed identifier of the publication, if applicable"}, "url": "http://www.crossref.org/", "icon": "http://www.crossref.org/favicon.ico", "desc": "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."}, "source_name": "CrossRef", "artifacts": {}, "error_msg": "NA", "has_error": "FALSE", "last_update": "130"}')

def test_build_json_response_error_handling():
    response = build_json_response({}, "TIMEOUT")
    response_no_timestamp = re.sub('130\d+', '130', response)
    assert_equals(response_no_timestamp, '{"about": {"metrics": {"doi": "the DOI of the publication, if applicable", "title": "the title of the publication", "url": "the url of the full text of the publication", "journal": "the journal where the paper was published", "authors": "the authors of the publication", "year": "the year of the publication", "pmid": "the PubMed identifier of the publication, if applicable"}, "url": "http://www.crossref.org/", "icon": "http://www.crossref.org/favicon.ico", "desc": "An official Digital Object Identifier (DOI) Registration Agency of the International DOI Foundation."}, "source_name": "CrossRef", "artifacts": {}, "error_msg": "TIMEOUT", "has_error": "TRUE", "last_update": "130"}')
    
def build_json_response(artifacts={}, error_msg=None):
    if (error_msg):
        has_error = "TRUE"
    else:
        has_error = "FALSE"
        error_msg = "NA"
    response = dict(source_name=SOURCE_NAME, 
        last_update=str(int(time.time())),
        has_error=has_error,
        error_msg=error_msg, 
        about=build_about(),
        artifacts=artifacts)
    json_response = simplejson.dumps(response)
    return(json_response)

def get_cache_timeout_response(url, 
                                http_timeout_in_seconds = 20, 
                                max_cache_age_seconds = (1) * (24 * 60 * 60), # (number of days) * (number of seconds in a day), 
                                header_addons = {}):
    http_cached = httplib2.Http(".cache", timeout=http_timeout_in_seconds)
    header_dict = {'cache-control':'max-age='+str(max_cache_age_seconds)}
    header_dict.update(header_addons)
    (response, content) = http_cached.request(url, headers=header_dict)
    return(response, content)

# each plugin needs to write a get_page and extract_stats    
def get_metric_values(doi):
    page = get_page(doi)
    if page:
        response = extract_stats(page, doi)    
    else:
        response = None
    return(response)    

#each plugin should make sure its range of inputs are covered
def test_run_plugin_doi():
    response = run_plugin(simplejson.dumps(TEST_INPUT_DOI))
    assert_equals(len(response), 1078)

def test_run_plugin_pmid():
    response = run_plugin(simplejson.dumps(TEST_INPUT_PMID))
    assert_equals(len(response), 962)

def test_run_plugin_url():
    response = run_plugin(simplejson.dumps(TEST_INPUT_URL))
    assert_equals(len(response), 686)

def test_run_plugin_invalid_id():
    response = run_plugin(simplejson.dumps(TEST_INPUT_DUD))
    assert_equals(len(response), 686)
    
def test_run_plugin_multiple():
    response = run_plugin(simplejson.dumps(TEST_INPUT_ALL))
    assert_equals(len(response), 1356)
    
def run_plugin(json_in):
    query = parse_input(json_in)
    (artifacts, error_msg) = get_artifacts_metrics(query)
    json_out = build_json_response(artifacts, error_msg)
    return(json_out)

# can call "python plugin.py" from command line, no args, to get sample output
def main():
    parser = OptionParser(usage="usage: %prog [options] filename",
                          version="%prog 1.0")
    (options, args) = parser.parse_args()
    if len(args) == 1:
        json_in = args[0]
    else:    
        json_in = simplejson.dumps(TEST_INPUT_ALL)
        print("Didn't get any input args, so going to use sample input: ")
        print(json_in)
        print("")
    
    json_out = run_plugin(json_in)
    print json_out
    return(json_out)

if __name__ == '__main__':
    main() 
            
#test_input = "10.1371/journal.pcbi.1000361"

    
        

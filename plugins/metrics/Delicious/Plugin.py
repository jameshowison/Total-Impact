#!/usr/bin/env python
import simplejson
import json
import urllib
import urllib2
import hashlib
import time
import re
import nose
from nose.tools import assert_equals
import sys
import os
# This hack is to add current path when running script from command line
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import BasePlugin
from BasePlugin.BasePlugin import BasePluginClass
from BasePlugin.BasePlugin import TestBasePluginClass

# Permissions: RWX for owner, WX for others.  Set this here so that .pyc are created with these permissions
os.umask(022) 
    
# Conforms to API specified here:  https://github.com/mhahnel/Total-Impact/wiki/Plugin-requirements
# To do automated tests with nosy                
# nosy CrossrefPlugin.py -A \'not skip\'
    
def skip(f):
    f.skip = True
    return f

class PluginClass(BasePluginClass):
                           
    # each plugin needs to customize this stuff                
    SOURCE_NAME = "Delicious"
    SOURCE_DESCRIPTION = "The tastiest bookmarks on the web."
    SOURCE_URL = "http://www.delicious.com/"
    SOURCE_ICON = "http://www.delicious.com/favicon.ico"
    SOURCE_METRICS = dict(bookmarks="The number of bookmarks to this artifact (maximum=100)")

    DEBUG = False

    DELICIOUS_API_URL = "http://feeds.delicious.com/v1/json/url/%s?count=100"

    def get_page(self, url):
        if not url:
            return(None)
        if (self.DEBUG):
            print url
        try:
            page = self.get_cache_timeout_response(url)
            if (self.DEBUG):
                print page
        except:
            page = None
        return(page)

    def extract_stats(self, page, url):
        if not page:
            return(None)        
        (response_header, content) = page
                
        bookmarks_hits = re.findall('"dt":"', content, re.MULTILINE)            
        metrics_dict = dict(bookmarks=len(bookmarks_hits))
        return(metrics_dict)
    
    
    def get_metric_values(self, url):
        md5_of_url = hashlib.md5(url).hexdigest()
        query_url = self.DELICIOUS_API_URL % md5_of_url
        page = self.get_page(query_url)
        if page:
            show_details_url = "http://www.delicious.com/url/" + md5_of_url
            response = {"show_details_url":show_details_url}
            response.update(self.extract_stats(page, url))
        else:
            response = None
        return(response)    
                                
    def artifact_type_recognized(self, id):
        response = self.is_url(id)
        return(response)   
        
    def build_artifact_response(self, artifact_id):
        metrics_response = self.get_metric_values(artifact_id)
        metrics_response.update({"type":"unknown"})
        return(metrics_response)
                
    def get_artifacts_metrics(self, query):
        response_dict = dict()
        error = None
        time_started = time.time()
        for artifact_id in query:
            (artifact_id, lookup_id) = self.get_relevant_id(artifact_id, query[artifact_id], ["url"])
            if (artifact_id):
                artifact_response = self.build_artifact_response(lookup_id)
                if artifact_response:
                    response_dict[artifact_id] = artifact_response
            if (time.time() - time_started > self.MAX_ELAPSED_TIME):
                error = "TIMEOUT"
                break
        return(response_dict, error)
    
    
class TestPluginClass(TestBasePluginClass):

    def setup(self):
        self.plugin = PluginClass()
        self.test_parse_input = self.testinput.TEST_INPUT_DOI
    
    ## this changes for every plugin        
    def test_build_artifact_response(self):
        response =  self.plugin.build_artifact_response('10.1371/journal.pcbi.1000361')
        assert_equals(response, {'doi': '10.1371/journal.pcbi.1000361', 'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'url': 'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361', 'journal': 'PLoS Comput Biol', 'authors': 'Shotton, Portwin, Klyne, Miles', 'year': '2009', 'pmid': '19381256', 'type': 'article'})

    ## this changes for every plugin        
    def test_get_artifacts_metrics(self):
        response = self.plugin.get_artifacts_metrics(self.test_parse_input)
        assert_equals(response, ({u'10.1371/journal.pcbi.1000361': {'doi': u'10.1371/journal.pcbi.1000361', 'title': 'Adventures in Semantic Publishing: Exemplar Semantic Enhancements of a Research Article', 'url': 'http://www.ploscompbiol.org/article/info%3Adoi%2F10.1371%2Fjournal.pcbi.1000361', 'journal': 'PLoS Comput Biol', 'authors': 'Shotton, Portwin, Klyne, Miles', 'year': '2009', 'pmid': '19381256', 'type': 'article'}}, 'NA'))

    #each plugin should make sure its range of inputs are covered
    def test_run_plugin_doi(self):
        response = self.plugin.run_plugin(simplejson.dumps(self.testinput.TEST_INPUT_DOI))
        assert_equals(len(response), 1077)

    def test_run_plugin_pmid(self):
        response = self.plugin.run_plugin(simplejson.dumps(self.testinput.TEST_INPUT_PMID))
        assert_equals(len(response), 961)

    def test_run_plugin_url(self):
        response = self.plugin.run_plugin(simplejson.dumps(self.testinput.TEST_INPUT_URL))
        assert_equals(len(response), 685)

    def test_run_plugin_invalid_id(self):
        response = self.plugin.run_plugin(simplejson.dumps(self.testinput.TEST_INPUT_DUD))
        assert_equals(len(response), 685)
    
    def test_run_plugin_multiple(self):
        response = self.plugin.run_plugin(simplejson.dumps(self.testinput.TEST_INPUT_ALL))
        assert_equals(len(response), 1710)
    
        

    
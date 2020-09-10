#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Wappalyzer import Wappalyzer, WebPage
import warnings
import requests

'''
import subprocess
def execWappalyzer(target):
    p = subprocess.Popen(["wappalyzer", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #p = subprocess.Popen(["/usr/bin/nodejs","/usr/share/wappalyzer/node_modules/wappalyzer/index.js", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out,err
'''
def execWappalyzer(r):
    warnings.filterwarnings("ignore")
    wappalyzer = Wappalyzer.latest()
    #response = requests.get('http://www.vidaeforma.com.br', verify=False, timeout=4)
    webpage = WebPage.new_from_response(r)
    return(wappalyzer.analyze(webpage))
    

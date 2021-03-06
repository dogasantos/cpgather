#!/usr/bin/env python
# -*- coding: utf-8 -*-
# /*
#
#
# */
__version__ = '1.0'

import argparse
import sys
import os
import json

from modules.mod_amass import execAmass, parseAmass
from modules.mod_sublist3r import execSublist3r, parseSublist3r
from modules.mod_subfinder import execSubfinder, parseSubfinder
from modules.mod_massdns import execMassdns, parseMassdns
from modules.mod_masscan import execMasscan
from modules.masstomap import execMton
from modules.mod_nmap import nmap_LoadXmlObject
from modules.misc import saveFile, readFile, appendFile, filterTargetDomainList
from modules.mod_s3scanner import execS3Scanner
from modules.mod_waybackmachine import WayBackMachine
from modules.mod_crtsh import crtshQuery
from modules.mod_webcheck import FindWeb, RetrieveWebContent, wappFormat, normalize_jsfiles, GetJsCommonDirectoriesURI, getUrlPath, ExtractJsLinks

SUBWL="/usr/share/wordlists/commonspeak2-wordlists/subdomains/subdomains.txt"
RESOLVERS="/usr/share/massdns/lists/resolvers.txt"                                      # List of open DNS we can use to resolve / brute dns subdomains

global CPPATH
CPPATH=os.path.dirname(os.path.realpath(__file__))


def banner():
    print("cpgather "+str(__version__)+" @ dogasantos")
    print("------------------------------------------------")
    print("     A wrapper arround a few recon tools ")
    print("------------------------------------------------")

def parser_error(errmsg):
    banner()
    print("Usage: python " + sys.argv[0] + " [Options] use -h for help")
    print("Error: %s" %errmsg)
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(epilog='\tExample: \r\npython ' + sys.argv[0] + " -d target.com -l target-ip-list.txt -s phase")
    parser.error = parser_error
    parser._optionals.title = "Options:"
    parser.add_argument('-d', '--domain', help="Domain name we should work with", required=True)
    parser.add_argument('-l', '--sublist', help="List of already known hosts that should be parsed", required=False)
    parser.add_argument('-s', '--skipdiscover', help="Just parse the list provided via -i. Do not run otehr discovery tools", required=False)
    parser.add_argument('-ps', '--ports', help='Specify comma separated list of ports that should be scanned (all tcp by default)', required=False, nargs='?')
    parser.add_argument('-v', '--verbose', help='Enable Verbosity',  required=False, action='store_true')
    parser.add_argument('-sw', '--wordlist', help='Specify a wordlist for subdomain discovery (otherwise default one)', required=False, nargs='?')
    return parser.parse_args()


def TargetDiscovery(domain,wordlist,skipdiscovery,hostlist):
    print("[*] Subdomain discovery phase")
    ips = list()
    hosts = list()
    if skipdiscovery == False:
        print("  + Running amass")
        execAmass(domain)

        print("  + Running sublist3r")
        execSublist3r(domain)
    
        print("  + Running WayBack machine query")
        wayback_found_list = WayBackMachine(domain)
    
        print("  + Running subfinder (bruteforce mode)")
        execSubfinder(domain,wordlist)

        print("  + Parsing subfinder report")
        subfinder_found_list = parseSubfinder(domain)
        for item in subfinder_found_list:
            hosts.append(item.rstrip("\n"))

        print("  + Parsing WayBack machine report")
        for item in wayback_found_list:
            hosts.append(item.rstrip("\n"))

        print("  + Parsing amass report")
        amass_found_list = parseAmass(domain)
        for item in amass_found_list:
            hosts.append(item.rstrip("\n"))

        print("  + Parsing sublist3r report")
        sublist3r_found_list = parseSublist3r(domain)
        for item in sublist3r_found_list:
            hosts.append(item.rstrip("\n"))

    else:
        hosts = readFile(hostlist)

    #just to make sure...
    uhosts = filterTargetDomainList(list(set(hosts)),domain)

    saveFile(domain + ".hosts", uhosts)
    print("  + Hosts file created: " + domain + ".hosts")

    print("  + Running massdns")
    execMassdns(domain,RESOLVERS)
    print("  + Parsing massdns report")
    massdns_iplist = parseMassdns(domain)
    for nip in massdns_iplist:
        ips.append(nip)

    unique_ips = list(set(ips))
    saveFile(domain + ".ips", unique_ips)
    print("  + IPs file created: " + domain + ".ips")
    print("[*] Done: %d ips and %d hosts discovered" % (len(unique_ips), len(uhosts)))

    return unique_ips,uhosts

def WebDiscovery(nmapObj, domain, verbose):
    print("[*] Web Discovery phase has started")
    if os.path.isfile(domain+".web") == False or os.path.getsize(domain+".web") == 0:
        webhosts=FindWeb(domain, nmapObj)
        saveFile(domain + ".web", webhosts)
    else:
        webhosts = readFile(domain + ".web")

    print("[*] Web Stack identification via Wappalyzer")
    if os.path.isfile(domain+".wapp") == False or os.path.getsize(domain+".wapp") == 0:
        list_of_webstack = RetrieveWebContent(webhosts)
        list_of_webstack = wappFormat(domain,list_of_webstack)
        totalsize=len(list_of_webstack)
        itemcount=1
        appendFile(domain + ".wapp", '{"data":[')
        for item in list_of_webstack:
            njson = json.dumps(item)
            appendFile(domain + ".wapp", njson)
            if itemcount < totalsize:
                appendFile(domain + ".wapp", ',')
            itemcount+=1
            appendFile(domain + ".web." + str(item['status']) + ".txt", item['url']+"\n")

        appendFile(domain + ".wapp", ']}')
    else:
        list_of_webstack = readFile(domain + ".wapp")

    print("[*] Javascript files identification")
    if os.path.isfile(domain+".js.allfiles") == False or os.path.getsize(domain+".js.allfiles") == 0:
        if verbose > 0:
            print("  + Compiling a list of all js references found")
        list_of_js_files_all=list()
        all_lists_of_all_js_of_all_nodes=list()
        list_of_webstack = readFile(domain+".wapp")
        for rawdata in list_of_webstack:
            jdata = json.loads(rawdata)['data']
            for jnode in jdata:
                for js in normalize_jsfiles(jnode['url'],jnode['js']):
                    list_of_js_files_all.append(js)
                    if verbose > 0:
                        print("  + Found js file: {}".format(str(js)))
                    appendFile(domain + ".js.allfiles", js+"\n")
        if verbose>0:
            if len(list_of_js_files_all)==0:
                print("  + Could not find any js files on target hosts")
        #list_of_js_files_all = readFile(domain + ".js.allfiles")
        list_of_jsdirs_uri = GetJsCommonDirectoriesURI(domain,list_of_js_files_all)
        list_of_js_dir = list()

        for js_dir_uri_item in list_of_jsdirs_uri:
            js_dir_path = getUrlPath(js_dir_uri_item).replace("//","/")
            if verbose > 0:
                print("  + Found js common directory: {}".format(str(js_dir_path)))
            list_of_js_dir.append(js_dir_path)

        list_of_js_dir = list(set(list_of_js_dir))

            # js_dir_uri holds the full uri of directories with js files:
            # http://target/dir1/dir2/js/
            # 
            # list_of_js_dir holds the path portion of that uri:
            # /dir1/dir2/js/
        for jsdir in list_of_js_dir:
            appendFile(domain + ".js.dirs", jsdir +"\n")
        
        for jsdiruri in list_of_jsdirs_uri:
            appendFile(domain + ".js.dirsuri", jsdiruri  +"\n")

        ###
        ###
        if len(list_of_js_files_all)>0: 
            print("[*] Extracting more endpoints from js files via LinkFinder")
            if os.path.isfile(domain+".js.endpoints") == False or os.path.getsize(domain+".js.endpoints") == 0:
                all_js_files = list(set(readFile(domain+".js.allfiles")))
                all_endpoints_found_inside_js = ExtractJsLinks(domain,all_js_files)
                jsondata = json.dumps(all_endpoints_found_inside_js)
                print("[*] Generating endpoints json file: {}".format(str(domain+".js.endpoints")))
                appendFile(domain+".js.endpoints",jsondata)
            else:
                print("[*] Skipping: " + domain+".js.endpoints found")
    else:
        print("[*] Skipping: " + domain+".js.allfiles found")

    return webhosts,list_of_webstack

def S3Discovery(domain,verbose):
    print("[*] S3 Buckets Discovery phase has started")
    execS3Scanner(domain)
    list_of_buckets = readFile(domain+".buckets")
    print("  + {} buckets found.".format(str(len(list_of_buckets))))
    return True


if __name__ == "__main__":
    if os.geteuid() != 0:
        printf("[x] Must be root to run custom portscan.")
        sys.exit(1)

    args = parse_args()
    user_domain = args.domain
    user_verbose = args.verbose
    user_subdomain_wordlist = args.wordlist
    user_ports = args.ports
    user_sublist = args.sublist 
    user_skipdiscover = args.skipdiscover 



    banner()

    if user_ports is not None:
        ports = user_ports
    else:
        ports="80,443,8080,8443,9000,9090,8081,9443"
    nmapObj = False
    


    ips,hosts = TargetDiscovery(user_domain,user_subdomain_wordlist,user_skipdiscover,user_sublist)

    if len(ips) == 0:
        user_noscan = True
    else: 
        user_noscan = False

    if not user_noscan:
        print("[*] Port Scanning phase started")
        if os.path.isfile(user_domain + ".nmap.xml") == False or os.path.getsize(user_domain + ".nmap.xml") == 0:
            print("  + Running masscan against %s targets" % str(len(ips)))
            out,err=execMasscan(user_domain, ports)
            if "You don't have permission" in err:
                sys.exit("[x] You don't have permission to run portscan. You must run as root.")
            oports = readFile(user_domain + ".masscan")
            if len(oports) > 0:
                print("  + Running nmap fingerprinting and scripts")
                execMton(user_domain)
            else:
                print("[x] No open ports found for this domain. Aborting...")
                sys.exit(1)
        else:
            print("  + Nmap report found, loading data...")
        nmapObj = nmap_LoadXmlObject(user_domain + ".nmap.xml")

    if nmapObj:
        list_of_webservers_found, list_of_webstack = WebDiscovery(nmapObj, user_domain, user_verbose)

    else:
        print("[*] Web discovery skipped (no open ports found)")

    S3Discovery(user_domain, user_verbose)

    print("[*] cpgather finished! ")





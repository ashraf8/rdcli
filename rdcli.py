#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Command line utility named `rdcli`
"""

from datetime import datetime
from getopt import GetoptError, gnu_getopt
from getpass import getpass
from hashlib import md5
from json import dump, load
from os import path, makedirs, getcwd, access, W_OK, X_OK
from sys import argv
from RDWorker import RDWorker, UnrestrictionError
from urllib2 import HTTPCookieProcessor, build_opener
import time,subprocess,os
import sys
from cookielib import MozillaCookieJar

base = path.join(path.expanduser('~'), '.config', 'rdcli-py')
conf_file = path.join(base, 'conf.json')
cookie_file = path.join(base, 'cookie.txt')

def usage(status=0):
    """
    Print rdcli usage information
    """
    print 'Usage: rdcli [OPTIONS] LINK'

    print '\nOPTIONS:'
    print '  -h\tHelp. Display this help.'
    print '  -i\tInit. Force rdcli to ask for your login and password.'
    print '\tUseful if you made a typo or if you changed your login information since you first used rdcli.'
    print '  -l\tList. Write a list of the successfully unrestricted links on STDOUT, without downloading.'
    print '\t-t and -q options have no effect if -l is used.'
    print '  -o\tOutput directory. Download files into a specific directory.'
    print '  -O\tOutput file. Specify a name for the downloaded file instead of using the original file\'s name.'
    print '\t-O has no effect if several files will be downloaded.'
    print '  -p\tPassword. Provide a password for protected downloads.'
    print '  -q\tQuiet mode. No output will be generated.'
    print '  -t\tTest mode. Perform all operations EXCEPT file downloading.'
    print '  -x\t nottification time'
    print '  -L\t List Information'
    print '  -x\t nottification time.'
    print '  -X\t Google Gcm Notification.'
    # print '  -T\tTimeout. The maximum number of seconds to wait for a download to start.'
    print '\n`LINK` can be the URL to a file you want to download (i.e. http://host.com/myFile.zip) or the path to a ' \
          'file containing one ore several URL(s).'
    print '\nExample: rdcli http://host.com/myFile.zip'
    print 'Example: rdcli urls.txt'
    print 'Example: rdcli -t links-to-test.txt'
    print '\nReport rdcli bugs to https://github.com/MrMitch/realdebrid-CLI/issues/new'

    exit(status)


def ask_credentials():
    """
    Ask for user credentials
    """
    username = raw_input('What is your RealDebrid username?\n')
    raw_pass = getpass('What is your RealDebrid password '
                       '(won\'t be displayed and won\'t be stored as plain text)?')
    password = md5(raw_pass).hexdigest()

    return username, password


def save_credentials(conf_file, username, password_hash):
    """
    Save the credentials to a file on disk
    """
    try:
        with open(conf_file, 'wb') as output:
            dump({'username': username, 'password': password_hash}, output, indent=4)
    except BaseException as e:
        exit('Unable to save login information: %s' % str(e))


def getOpener(cookies):
    opener = build_opener(HTTPCookieProcessor(cookies))
    headers = [
                            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
                            ("User-Agent", "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36")
                        ];
    opener.addheaders = headers;
    return opener;

def getAccountInfo():
    print "getting account information"
    cookies = MozillaCookieJar(cookie_file)

    opener = getOpener(cookies);
    o = opener.open("https://real-debrid.com/api/account.php");

    print o.read(1024);
    o.close();
     
def download(filepath,url):
    # savedir = filename = ""

    # if filepath and os.path.isdir(filepath):
    #     savedir, filename = filepath, self.generate_filename()

    # elif filepath:
    #     savedir, filename = os.path.split(filepath)

    # else:
    #     filename = self.generate_filename(meta=meta)

    # filepath = os.path.join(savedir, filename)
    temp_filepath = filepath + ".temp"

    status_string = ('  {:.3f} MB [{:.2%}] received. Rate: [{:4.0f} '
                     'KB/s].  ETA: [{:.0f} min {:.0f} secs]')

    opener = build_opener()
    headers = [
                            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
                            ("User-Agent", "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36")
                        ];
    opener.addheaders = headers;

    response = opener.open(url);
    total = int(response.info()['Content-Length'].strip())
    chunksize, bytesdone, t0 = 16384, 0, time.time()

    fmode, offset = "wb", 0

    if os.path.exists(temp_filepath):
        if os.stat(temp_filepath).st_size < total:

            offset = os.stat(temp_filepath).st_size
            fmode = "ab"

    outfh = open(temp_filepath, fmode)

    if offset:
        # partial file exists, resume download
        resuming_opener = build_opener()
        resuming_opener.addheaders = [('User-Agent', "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36"),
                                      ("Range", "bytes=%s-" % offset)]
        response = resuming_opener.open(url)
        bytesdone = offset

    _active = True

    elapsed = 0;
    rate = 0;
    start = datetime.now()

    try:
        while _active:
            chunk = response.read(chunksize)
            outfh.write(chunk)
            elapsed = time.time() - t0
            bytesdone += len(chunk)
            rate = ((bytesdone - offset) / 1024) / elapsed
            eta = (total - bytesdone) / (rate * 1024)
            progress_stats = (bytesdone/1024.0/1024.0, bytesdone * 1.0 / total, rate, eta/60,eta%60)

            if not chunk:
                outfh.close()
                break
            
            status = status_string.format(*progress_stats)
            sys.stdout.write("\r" + status + ' ' * 4 + "\r")
            sys.stdout.flush()
    except KeyboardInterrupt:
            print "\r\nCaught Keyboard Interrupt... Stopping\r\n";

    final_status = '\r\n%.2fMB [%.3f%%] downloaded in %s (= %.2f MB/s)' \
                                           % (bytesdone/1024.0/1024.0, (bytesdone * 100. / total),
                                              str(datetime.now() - start).split('.')[0], rate/1024.0)
    
    print(final_status);
    print("Download finished");

    #if _active:
    if bytesdone == total:
        os.rename(temp_filepath, filepath)
        return (filepath,final_status)
    else:  # download incomplete, return temp filepath
        outfh.close()
        return (temp_filepath,final_status)

gcmNotify = False;

def sendNotification(title,body):
    global gcmNotify
    if(gcmNotify):
        os.popen("myNotify.sh " + "'%s' '%s'" % (title,body) );
    
    
def main():
    """
    Main program
    """

    list_only = False
    test = False
    verbose = True
    timeout = 120

    download_password = ''
    output_dir = getcwd()

    def debug(s):
        if verbose:
            print s,

    # make sure the config dir exists
    if not path.exists(base):
        makedirs(base)

    worker = RDWorker(cookie_file)

    # parse command-line arguments
    try:
        opts, args = gnu_getopt(argv[1:], 'hiqtlpXxL:o:T:O:')
    except GetoptError as e:
        print str(e)
        usage(1)
	
    n_time = 0;
    for option, argument in opts:
        if option == '-h':
            usage()
        elif option == '-i':
            username, password = ask_credentials()
            save_credentials(conf_file, username, password)
        elif option == '-q':
            if not list_only:
                verbose = False
        elif option == '-t':
            if not list_only:
                test = True
        elif option == '-l':
            list_only = True
            test = False
            verbose = False
        elif option == '-o':
            output_dir = argument
        elif option == '-p':
            download_password = argument
        elif option == '-T':
            timeout = int(argument)
        elif option == '-O':
            filename = argument
        elif option == '-x':
            n_time = int(argument)
        elif option == '-L':
            getAccountInfo();
        elif option == '-X':
            global gcmNotify 
            gcmNotify = True;
            n_time = -100;

    # stop now if no download and no output wanted
    if test and not verbose:
        exit(0)

    debug("Start Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n');

    # make sure we have something to process
    if len(args) > 0:
        output_dir = path.abspath(path.expanduser(output_dir))
        # ensure we can write in output directory
        if not output_dir == getcwd() and not path.exists(unicode(output_dir)):
            debug('%s no such directory' % unicode(output_dir))
            exit(1)
        else:
            if not access(output_dir, W_OK | X_OK):
                debug('Output directory not writable')
                exit(1)
            else:
                debug(u'Output directory: %s\n' % output_dir)

        # retrieve login info
        try:
            with open(conf_file, 'r') as conf:
                obj = load(conf)
                username = obj['username']
                password = obj['password']
        except BaseException:
            username, password = ask_credentials()
            save_credentials(conf_file, username, password)

        # login
        try:
            worker.login(username, password)
        except BaseException as e:
            exit('Login failed: %s' % str(e))

        if path.isfile(args[0]):
            with open(args[0], 'r') as f:
                links = f.readlines()
        else:
            links = args[0].splitlines()

        # unrestrict and download

        for link in links:
            link = link.strip()
            if link.strip() == "":
                print "";
                continue;
            if link[0] == "#":
                debug(link);
                print "\n";
                continue;

            debug('\nUnrestricting %s' % link)

            try:
                unrestricted, original_filename = worker.unrestrict(link, download_password)
                debug(u'==> ' + unrestricted + '\n')
            except UnrestrictionError as e:
                debug('==> WARNING, unrestriction failed (%s)' % str(e) + '\n')
                sendNotification("WARNING, unrestriction failed", str(e));
                continue;

            if list_only:
                print unrestricted
            elif not test:

                if len(links) == 1:
                    try:
                        fullpath = path.join(output_dir, filename)
                    except NameError:
                        fullpath = path.join(output_dir, original_filename)
                else:
                    fullpath = path.join(output_dir, original_filename)

                if os.path.isfile(fullpath):
                    print "File Exists [%s]" % original_filename;
                    continue;

                try:
                    to_mb = lambda b: b / 1048576.
                    to_kb = lambda b: b / 1024.

                    opener = build_opener(HTTPCookieProcessor(worker.cookies))
                    headers = [
                        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"),
                        ("User-Agent", "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36")
                    ];
                    opener.addheaders = headers;
                    stream = opener.open(unrestricted)
                    info = stream.info().getheaders('Content-Length')

                    total_size = 0
                    downloaded_size = 0

                    not_time = time.time();

                    if len(info):
                        total_size = float(info[0])
                        start = 'Downloading: %s (%.2f MB)\n' % (fullpath, to_mb(total_size))
                    else:
                        start = 'Downloading: %s (unknown size)\n' % fullpath

                    debug(start)                    
                    res = download(fullpath,unrestricted);
                    if (n_time == -100):
                        sendNotification( "Downloaded " + original_filename,res[1]);
                   
#                    os.popen("echo 'Done downloading' | netcat 127.0.0.1 5566");
                    debug("End Time: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n');
                except BaseException as e:
                    debug('\nDownload failed: %s\n' % e);

        debug('End\n')
        return 0
    else:
        usage(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit('^C caught, exiting...')

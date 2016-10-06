import argparse
import requests
import sys
import errno
from lxml import html
from shared.Utils import Utils
from shared.Utils import HTTPUtils
from shared.Parser import parser as html_parser
import datetime
import pymongo
import re
from sklearn import linear_model

class Worker:

    def __init__(self):
        """
        Class Constructor : Initializes MongoDB
        configuration on a dictionary
        """

        params = {}
        params['server'] = '127.0.0.1'
        params['port'] = '27017'
        params['database'] = 'topfree'
        #params['username'] = 'user'
        #params['password'] = 'user'
        params['seed_collection'] = 'PlayStore_QueuedApps_' + now_str
        params['apps_collection'] = 'PlayStore_' + now_str
        #params['auth_database'] = 'MobileAppsData'
        params['write_concern'] = True
        client = pymongo.MongoClient(params['server'],int(params['port']))
        tmp_mongodb = client[now_str]
        tmp_app = tmp_mongodb[params['apps_collection']]
        params['count'] = tmp_app.count()
        print params['count']
        client.close()
        self._params = params

    def get_arguments_parser(self):
        """
        Creates a parsing object using the argsparse
        lib
        """

        parser = argparse.ArgumentParser(description='Scraper / Worker layer \
                                                     of the Google Play Store \
                                                     Crawler')

        # All arguments start with "-", hence, they are all handled as optional
        parser.add_argument('--console-log-verbosity',
                            type=str,
                            choices=['INFO', 'DEBUG', 'WARN',
                                     'ERROR', 'CRITICAL'],
                            help='Log Verbosity Level (default=INFO)',
                            default='INFO')

        parser.add_argument('--file-log-verbosity',
                            type=str,
                            choices=['INFO', 'DEBUG', 'WARN',
                                     'ERROR', 'CRITICAL'],
                            help='Log Verbosity Level (default=ERROR)',
                            default='ERROR')

        parser.add_argument('--log-file',
                            type=str,
                            help='Path of the output log file (default=\
                                  console-only logging)')

        parser.add_argument('--max-errors',
                            type=int,
                            default=100,
                            help='Max http errors allowed on workers \
                                 phase. (default=100)')

        parser.add_argument('--debug-https',
                            action='store_true',
                            default=False,
                            help='Turn this flag on to enable Fiddler to \
                                 hook and debug HTTPS Requests')

        parser.add_argument('--proxies-path',
                            type=file,
                            default=None,
                            help='Path to the file of proxies \
                            (read the documentation)')

        parser.add_argument('--limit',
                            type=int,
                            default=10000,
                            help='limit of the total scrap number')

        return parser

    def scrape_apps(self,language):
        """
        Main method of the 'Worker' layer of this project.

        This method starts the distributed working phase which will
        consume urls from the seed database and scrape apps data out
        of the html pages, storing the result into the
        apps_data collection on MongoDB
        """

        # Arguments Parsing
        args_parser = self.get_arguments_parser()
        self._args = vars(args_parser.parse_args())

        # Log Handler Configuring
        self._logger = Utils.configure_log(self._args)

        # MongoDB Configuring
        if not Utils.configure_mongodb(self,**self._params):
            self._logger.fatal('Error configuring MongoDB')
            sys.exit(errno.ECONNREFUSED)

        # Making sure indexes exist
        self._mongo_wrapper.ensure_index('IsBusy');
        self._mongo_wrapper.ensure_index('_id', self._params['apps_collection'])

        # Proxies Loading
        self._proxies = Utils.load_proxies(self._args)

        # if "Debug Http" is set to true, "verify" must be "false"
        self._verify_certificate = not self._args['debug_https']
        self._is_using_proxies = self._proxies != None

        # Control Variables - Used on the 'retrying logic'
        retries, max_retries = 0, 8

        parser = html_parser()

        # customized limit number
        self._params['limit'] = self._args['limit']

        # Loop only breaks when there are no more apps to be processed
        while True:
            #if self._params['count'] >= self._params['limit']:
            #    break
            # Finds an app to be processed and toggles it's state to 'Busy'
            seed_record = self._mongo_wrapper.find_and_modify()
            if not seed_record:
                break

            try:
                url = seed_record['_id']
                rank = seed_record['Rank']

                # Do we need to normalize the url ?
                if 'http://' not in url and 'https://' not in url:
                    url = 'https://play.google.com' + url

                self._logger.info('Processing: %s' % url)

                # Is this app processed already ?
                if self._mongo_wrapper.app_processed(url, self._params['apps_collection']):

                    self._logger.info('Duplicated App : %s. Skipped' % url)
                    self._mongo_wrapper.remove_app_from_queue(seed_record)
                    continue

                # Get Request for the App's Page
                response = requests.get(url + ('&hl=' + language),
                                        HTTPUtils.headers,
                                        verify=self._verify_certificate,
                                        proxies=Utils.get_proxy(self))

                # Sanity Checks on Response
                if not response.text or response.status_code != requests.codes.ok:
                    self._logger.info('Error Opening App Page : %s' % url)

                    retries += 1

                    # Retries logic are different if proxies are being used
                    if self._is_using_proxies:
                        Utils.sleep()
                try:
                    # Scraping Data from HTML
                    app = parser.parse_app_data(response.text)
                    # Compute the actual average star
                    tmp_list = app['Score']
                    total_num = tmp_list['OneStars'] + tmp_list['TwoStars'] + tmp_list['ThreeStars'] + tmp_list['FourStars'] + tmp_list['FiveStars']
                    star_num = 1*tmp_list['OneStars'] + 2*tmp_list['TwoStars'] + 3*tmp_list['ThreeStars'] + 4*tmp_list['FourStars'] + 5*tmp_list['FiveStars']
                    average_score = star_num / float(total_num)
                    app['Score']['AverageScore'] = average_score
                    app['Rank'] = rank

                    '''
                    if lastone != '':
                      last_app = last_app_mongo.find_one({'_id':url})
                      app['Delta'] = {}
                      if last_app != None:
                        app['Delta']['AverageScore'] = average_score - last_app['Score']['AverageScore']
                        app['Delta']['OneStars'] = tmp_list['OneStars'] - last_app['Score']['OneStars']
                        app['Delta']['TwoStars'] = tmp_list['TwoStars'] - last_app['Score']['TwoStars']
                        app['Delta']['ThreeStars'] = tmp_list['ThreeStars'] - last_app['Score']['ThreeStars']
                        app['Delta']['FourStars'] = tmp_list['FourStars'] - last_app['Score']['FourStars']
                        app['Delta']['FiveStars'] = tmp_list['FiveStars'] - last_app['Score']['FiveStars']
                        app['Delta']['Reviewers'] = app['Reviewers'] - last_app['Reviewers']
                    '''

                    # Stamping URL into app model
                    app['Url'] = url
                    app['_id'] = url

                    # Reaching related apps
                    related_apps = parser.parse_related_apps(response.text)
                    if not related_apps:
                        app['RelatedUrls'] = None
                    else:
                        app['RelatedUrls'] = related_apps
                        self._logger.info('Related Apps: %s - %d' % (url, len(related_apps)))
		    
                    # Inserting data into MongoDB
                    self._mongo_wrapper._insert(app, self._params['apps_collection'])
                    self._params['count'] += 1
		    
                    # Re-Feeding seed collection with related-app urls
                    #if app['RelatedUrls']:
                    #    for url in app['RelatedUrls']:

                    #        if not self._mongo_wrapper.app_processed(url, self._params['apps_collection']) and \
                    #           not self._mongo_wrapper.app_processed(url, self._params['seed_collection']):
                    #            self._mongo_wrapper.insert_on_queue(url, self._params['seed_collection'])

                except Exception as exception:
                    self._logger.error(exception)
		    print retries
                    if retries > max_retries:
		        continue
                    retries += 1
                    # Toggling app state back to false
                    self._mongo_wrapper.toggle_app_busy(url,False, self._params['seed_collection'])

            except Exception as exception:
                self._logger.error(exception)



if __name__ == '__main__':
  now = datetime.datetime.now()
  now_str = now.strftime("%Y%m%d") + '_topfree'
  print now_str
  language = 'zh-tw'

  requests.packages.urllib3.disable_warnings()
  worker = Worker()
  worker.scrape_apps(language)

  print 'finish!!'

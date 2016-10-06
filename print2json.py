import json
import time
import datetime
import pymongo

now = datetime.datetime.now()
this_date = now.strftime("%Y%m%d") + '_topfree'
user = ''
password = ''
database_name = 'topfree'
host = 'localhost'
client = pymongo.MongoClient(host,27017)
ITEM_NUM = 2000
check_update = True

this_mongodb = client[database_name]
this_queue = this_mongodb['PlayStore_' + this_date]

total_dict = {}

this_cur = this_queue.find()
for doc in this_cur:
  rank = doc['Rank']
  total_dict[rank] = doc



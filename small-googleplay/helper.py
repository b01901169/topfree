import numpy as np
import time
import json
import ast
import pymongo

def readData(path):
  f = open(path,'r')
  value_list = []
  #tmp = f.readline()
  #tmp_list = tmp[:-1].split(' ')
  #user_num = int(tmp_list[1])
  #item_num = int(tmp_list[3])
  while 1:
    tmp = f.readline()
    if tmp == '':
      break
    tmp_list = tmp[:-1].split(' ')
    value_list.append((int(tmp_list[0]),int(tmp_list[1])))
  user_num = max(value_list,key=lambda x:x[0])[0] + 1
  item_num = max(value_list,key=lambda x:x[1])[1] + 1
  return user_num,item_num,value_list

def readCorrelation(path):
  f = open(path,'r')
  item_num = int(f.readline()[:-1])
  correlation = np.zeros((item_num,item_num))
  for i in range(item_num):
    correlation[i] = np.array([float(x) for x in f.readline()[:-1].split()])
  return correlation

def precomputeCorrelation(item_list,correlation):
  s = len(item_list)
  vector_correlation = np.zeros((s,s))
  for i in range(s):
    tmp_q = item_list[i]
    vector_correlation[i] = [np.inner(tmp_q-x,tmp_q-x) for x in item_list]
  if s != len(correlation):
    print 'WARNING!!!'
  multiply_correlation = np.multiply(vector_correlation,correlation[0:s,0:s])
  return multiply_correlation

def sigmoid(x):
  return 1 / (1 + np.exp(-x))

def dsigmoid(x):
  sx = sigmoid(x)
  return sx * (1-sx)

def updateCorrelation(j,item_list,multiply_correlation,content_correlation_j):
  s = len(item_list)
  tmp_q = item_list[j]
  new_item_correlation = [np.inner(tmp_q-x,tmp_q-x) for x in item_list]
  new_j_correlation = np.multiply(new_item_correlation,content_correlation_j[0:s])
  multiply_correlation[j] = new_j_correlation
  multiply_correlation[:,j] = new_j_correlation
  return multiply_correlation

def updateCorrelation2(i,j,item_list,multiply_correlation,content_correlation_i,content_correlation_j):
  s = len(item_list)
  tmp_i = item_list[i]
  new_item_i_correlation = [np.inner(tmp_i-x,tmp_i-x) for x in item_list]
  tmp_j = item_list[j]
  new_item_j_correlation = [np.inner(tmp_j-x,tmp_j-x) for x in item_list]
  new_i_correlation = np.multiply(new_item_i_correlation,content_correlation_i[0:s])
  new_j_correlation = np.multiply(new_item_j_correlation,content_correlation_j[0:s])
  multiply_correlation[i] = new_i_correlation
  multiply_correlation[j] = new_j_correlation
  multiply_correlation[:,i] = new_i_correlation
  multiply_correlation[:,j] = new_j_correlation
  return multiply_correlation

def extractDict(train_set,user_num,item_num):
  user_dict = {}
  item_dict = {}
  for i in range(user_num):
    user_dict[i] = []
  for i in range(item_num):
    item_dict[i] = []
  for pair in train_set:
    user_dict[pair[0]].append(pair[1])
    item_dict[pair[1]].append(pair[0])
  return user_dict,item_dict

def buildCorrespond(datalist):
  # -------------- mongodb part -------------------
  print 'build corresponding dictionary ...'
  start_time = time.time()
  user = ''
  password = ''
  host = 'localhost'
  client = pymongo.MongoClient(host,27017)
  this_date = '20160701'
  database_name = 'free-app'
  this_mongodb = client[database_name]
  this_queue = this_mongodb['PlayStore_QueuedApps_' + this_date]
  this_app = this_mongodb['PlayStore_' + this_date]

  prefix = 'https://play.google.com/store/apps/details?id='
  all_dict_no_filter = {}
  datanum = len(datalist)
  all_dict_no_filter = {}
  correspond_dict = {}
  for i in range(datanum):
    tmp = datalist[i]
    tmp_list = tmp['apps'][2:-2].split('},{')
    tmp_dict = {}
    for tmp_item in tmp_list:
      item = json.loads('{' + tmp_item + '}')
      item_name = item['name']
      if not all_dict_no_filter.has_key(item_name):
        all_dict_no_filter[item_name] = 1
  start_time = time.time()
  for item_name in all_dict_no_filter:
    tmp_item_name_list = item_name.split('.')
    tmp_num = len(tmp_item_name_list)
    for j in range(tmp_num-1,-1,-1):
      surfix = '.'.join(tmp_item_name_list[:j+1])
      true_item_name = prefix + surfix
      if this_app.find({'_id':true_item_name}).count() >= 1:
        correspond_dict[item_name] = surfix
        break
    if j == 0:
      correspond_dict[item_name] = 'null'
  return correspond_dict

def updateCorrespondDict(item_name,large_date):
  user = ''
  password = ''
  host = 'localhost'
  port = 27017
  try:
    client = pymongo.MongoClient(host,port)
  except:
    return
  database_name = 'free-app'
  large_mongodb = client[database_name]
  large_queue = large_mongodb['PlayStore_QueuedApps_' + large_date]
  large_app = large_mongodb['PlayStore_' + large_date]

  prefix = 'https://play.google.com/store/apps/details?id='
  tmp_item_name_list = item_name.split('.')
  tmp_num = len(tmp_item_name_list)
  for j in range(tmp_num-1,-1,-1):
    surfix = '.'.join(tmp_item_name_list[:j+1])
    true_item_name = prefix + surfix
    if large_app.find({'_id':true_item_name}).count() >= 1:
      return surfix
  if j == 0:
    return 'null'

def read_top_100(path):
  f_top = open(path,'r')
  top_100 = []
  category_100 = []
  tmp = f_top.readline()[:-1].split(' ')
  top_100.append(tmp[1])
  category_100.append(tmp[2])
  tmpflag = 0
  while 1:
    tmp = f_top.readline()
    if tmp == '':
      break
    if tmpflag == 1:
      tmp2 = tmp[:-1].split(' ')
      top_100.append(tmp2[1])
      category_100.append(tmp2[2])
      tmpflag = 0
    if tmp[:-1] == '>>>>>>>':
      tmpflag = 1
  return top_100,category_100

def read_popular(path,num,star):
  f = open(path,'r')
  popular_list = {}
  rank = 0
  count = 0
  while 1:
    if count >= num:
      break
    tmp = f.readline()
    if tmp == '':
      break
    if ('*' in tmp) and star:
      continue
    name = tmp[:-1].split()[0]
    name = name[46:]
    popular_list[name] = rank
    rank += 1
    count += 1
  return popular_list

def read_user_locale(path):
  f = open(path,'r')
  user_locale_dict = {}
  while 1:
    tmp = f.readline()
    if tmp == '':
      break
    user,userid,locale = tmp[:-1].split()
    user_locale_dict[int(user)] = (userid,locale)
  return user_locale_dict

def read_user_id2locale(path):
  f = open(path,'r')
  user_locale_dict = {}
  while 1:
    tmp = f.readline()
    if tmp == '':
      break
    user,userid,locale = tmp[:-1].split()
    user_locale_dict[userid] = locale
  return user_locale_dict

def read_block_list(path):
  f = open(path,'r')
  block_list = []
  while 1:
    tmp = f.readline()
    if tmp == '':
      break
    block_list.append(tmp[:-1])
  return block_list

def read_system(path):
  f = open(path,'r')
  system_json = {}
  while 1:
    tmp = f.readline()
    if tmp == '':
      break
    tmp_list = [x for x in tmp[:-1].split()]
    i = int(tmp_list[0][:-1])
    system_json[i] = []
    for j in tmp_list[1:]:
      system_json[i].append(int(j))
  return system_json

def read_model(path,item_num,user_num):
  f_m = open(path,'r')
  count = int(f_m.readline()[:-1].split()[1])
  m = int(f_m.readline()[:-1].split()[1])
  n = int(f_m.readline()[:-1].split()[1])
  f = int(f_m.readline()[:-1].split()[1])
  b = float(f_m.readline()[:-1].split()[1])
  p = [] # player
  q = [] # item
  while 1:
    tmp = f_m.readline()
    if tmp == '':
      break
    if tmp[0] == 'p':
      tmpa = np.array([float(x) for x in tmp[:-1].split(' ')[2:-1]])
      p.append(tmpa)
    if tmp[0] == 'q':
      tmpb = np.array([float(x) for x in tmp[:-1].split(' ')[2:-1]])
      q.append(tmpb)
  for i in range(len(q),item_num):
    q.append([0] * f)
  for i in range(len(p),user_num):
    p.append([0] * f)
  p = np.array(p)
  q = np.array(q)
  return p,q


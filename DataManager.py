# coding=utf-8

# The DataManager class define operations of data management
# refresh_data([symbols]) : get fresh daily data from web and store locally
# get_daily_data([symbols], start, end, local): get data from local or web
# get_basic_date([symbols])
# get_current_data([symbols])
# get_finance_data([synbols])


import ConfigParser
import traceback
import os
import shutil
import json
import h5py

import datetime
import time
import numpy as np
import pandas as pd
import tushare as ts
import matplotlib as plt
from datetime import timedelta
from datetime import date
from keras.utils import np_utils
from sklearn import preprocessing
import keras.backend as K

ffeatures = ['pe', 'outstanding', 'totals', 'totalAssets', 'liquidAssets', 'fixedAssets', 'reserved',
             'reservedPerShare', 'esp', 'bvps', 'pb', 'undp', 'perundp', 'rev', 'profit', 'gpr',
             'npr', 'holders']
bfeatures = ['pe', 'outstanding', 'reservedPerShare', 'esp', 'bvps', 'pb', 'perundp', 'rev', 'profit',
             'gpr', 'npr']
tsfeatures = ['open', 'high', 'close', 'low', 'p_change', 'turnover']
dfeatures = ['price_change', 'ma5', 'ma10', 'ma20', 'v_ma5', 'v_ma10', 'v_ma20']
tfeatures = ['open', 'high', 'close', 'low', 'p_change']  # , 'volume']


def mydate(datestr):
    if isinstance(datestr, list) or isinstance(datestr, np.ndarray):
        datelist = []
        for ds in datestr:
            datelist.append(mydate(ds))
        return datelist
    else:
        datearr = datestr.split('-')
        if len(datearr) !=3: raise "Wrong date string format " + datestr
        return date(int(datearr[0]), int(datearr[1]), int(datearr[2]))


def intdate(dt):
    if isinstance(dt, list) or isinstance(dt, np.ndarray):
        intdatelist = []
        for d in dt:
            intdatelist.append(intdate(d))
        return intdatelist
    else:
        return dt.year*10000+dt.month*100+dt.day


def intstr(ints):
    if isinstance(ints, list) or isinstance(ints, np.ndarray):
        intarr = []
        for i in ints:
            intarr.append(int(i))
        return intarr
    else:
        return int(ints)


def int2str(ints):
    sb = '000000'
    if isinstance(ints, list) or isinstance(ints, np.ndarray):
        lst = []
        for i in ints:
            lst.append(sb[0:6-len(str(int(i)))] + str(i))
        return lst
    else:
        return sb[0:6-len(str(int(ints)))] + str(int(ints))


def minmax_scale(arr):
    mi = np.min(arr)
    mx = np.max(arr)
    arr = (arr-mi)/(mx-mi+K.epsilon())
    return arr


def pricechange_scale(arr):
    mi = np.min(arr)
    arr = (arr-mi)/(mi+K.epsilon())*100
    return arr


class DataManager():
    def __init__(self, cfgfile='config.cfg', data_path='data/', logfile='dm.log'):
        pass
        # self.configParser = ConfigParser.ConfigParser()
        # self.configParser.read(cfgfile)
        # self.data_path = data_path
        # self.storage = self.configParser.get('dbconfig', 'storage')
        # self.logfile = logfile

    def refresh_data(self, start='2005-01-01', trytimes=10):
        # refresh history data
        # trytimes, times to try

        # edate = datetime.date.today()
        edate = datetime.date.today() - timedelta(days=1)
        edate = edate.strftime('%Y-%m-%d')
        data_path = './data/' + edate + '/'
        if os.path.exists(data_path):
            return
        else:
            os.makedirs(data_path)
        print ("[ refresh_data ]... start date:%s"%(start))
        basics = ts.get_stock_basics()
        basics.to_csv('./data/basics.csv')
        all_data = ts.get_today_all()
        symbols = all_data['code']

        def trymore(symbs, times):
            failsymbs = []
            i = 0
            while i < len(symbs):
                try:
                    df = ts.get_hist_data(symbs[i], start)
                except:
                    failsymbs.append(symbs[i])
                    print "Exception when processing " + symbs[i]
                    traceback.print_exc()
                    i = i + 1
                    continue

                if df is not None and len(df) > 0:
                    df = df[::-1]
                    df.to_csv(data_path + symbs[i] + '.csv')
                    df.to_csv('./data/daily/'+ symbs[i] + '.csv')
                else:
                    # TODO: add log trace
                    failsymbs.append(symbs[i])
                i = i + 1
            if len(failsymbs) > 0:
                print "In round " + str(times) + " following symbols can't be resolved:\n" + str(failsymbs)
                if times - 1 > 0:
                    times = times -1
                    trymore(failsymbs, times)
                else:
                    return
        trymore(symbols, trytimes)

    def get_data(self, symb_num):
        print ("[ get_data ]... for %i symbols" %(symb_num))
        # if symbols is None: return
        self.refresh_data()
        basics = self.get_bsdata()
        symbols = int2str(list(basics.index))
        dict = {}
        i = 0
        while i < len(symbols) and i < symb_num:
            try:
                df = pd.read_csv('./data/daily/' + symbols[i] + '.csv', index_col=0, dtype={'code': str})
                if df is not None:
                    dict[symbols[i]] = df
            except:
                print "Can't get data for symbol:" + str(symbols[i])
                # traceback.print_exc()
                i = i + 1
                continue
            i = i + 1
        return dict

    def get_newly_data(self, days=None):
        print ("[ get_today data]... ")
        edate = datetime.date.today() - timedelta(days=1)
        edate = edate.strftime('%Y-%m-%d')
        today_file = './data/' + edate + '/newlydata.h5'
        if os.path.exists(today_file):
            f = h5py.File(today_file, 'r')
            return f
        self.refresh_data()
        basics = self.get_bsdata()
        symbols = int2str(list(basics.index))
        f = h5py.File(today_file, 'w')
        i = 0
        while i < len(symbols):
            try:
                df = pd.read_csv('./data/daily/' + symbols[i] + '.csv', index_col=0, dtype={'code': str})
            except:
                print "Can't get data for symbol:" + str(symbols[i])
            if df is not None:
                df = df[-days:][tsfeatures]
                f.create_dataset(symbols[i], data=np.array(df.astype(float)))
            i += 1
        f.flush()
        return f


    def get_bsdata(self, online=False, cache=False):
        print ("[ get_bsdata ]... online(%s)"%(str(online)))
        if online is False:
            basics = pd.read_csv('./data/basics.csv', index_col =0,dtype={'code':str})
        else:
            basics = ts.get_stock_basics()
            if cache is True: basics.to_csv('./data/basics.csv')
        return basics

    def create_dataset_simple(self, sym_num, lookback=5, days=None):
        """
        The function takes two arguments: the `dataset`, which is a NumPy array that we want to convert into a dataset,
        and the `lookback`, which is the number of previous time steps to use as input variables
        to predict the next time period — in this case defaulted to 5.
        symbs
        lookback: number of previous time steps as int
        returns a list of data cells of format([np.array(bsdata), tsdata, rtdata, lbdata])
        """

        print "[ create_dataset simple]... "
        data_all = []
        bsset = self.get_bsdata()[bfeatures]
        bsset = bsset[bsset['pb'] > 0]
        symblist = intstr(list(bsset.index))
        bsset = preprocessing.scale(bsset)
        bsset = np.hstack([np.array(symblist).reshape(len(symblist),1), bsset])

        stockset = self.get_data(sym_num)
        for symb in stockset:
            if int(symb) not in symblist: continue
            if days is None:
                data_stock = stockset[symb][tsfeatures]
            else:
                data_stock = stockset[symb][tsfeatures][-days-lookback:]
            datelist = mydate(list(data_stock.index))
            datecol = np.array(intdate(datelist)).reshape(-1,1)
            bsdata = bsset[bsset[:,0]==int(symb)][0]  # sym,...
            for i in range(len(data_stock) - lookback):
                if data_stock['p_change'][i + lookback-1] >=9.96: continue  # clean data un-operational
                dtcell = np.array(data_stock)[i:(i+lookback+1)]
                ohcl = minmax_scale(dtcell[:-1,0:4])
                # 应该直对testcase进行normalization
                tsdata = np.hstack([datecol[i: i+lookback], ohcl, dtcell[:-1, 4:]])
                # tsdata_v = np.hstack([datecol[i: i+lookback], dtcell[:-1,:]])
                # rtdata = np.hstack([[int(symb)], datecol[i+lookback], ohcl[-1], dtcell[-1, 4:]])
                # rtdata_v = np.hstack([[int(symb)], datecol[i+lookback], dtcell[-1]])
                # lbdata = np.hstack([[int(symb)], datecol[i+lookback+1], ohcl[-1], dtcell[-1,4:]])
                lbdata_v = np.hstack([[int(symb)], datecol[i + lookback], dtcell[-1]])
                data_cell = [bsdata, tsdata, lbdata_v]
                data_all.append(data_cell)
        print "[ Finish ]"
        return data_all

    def split_dataset(self, dataset, train_psize, batch_size=1, seed=None):
        """
        Splits dataset into training and test datasets. The last `lookback` rows in train dataset
        will be used as `lookback` for the test dataset.
        :param dataset: source dataset
        :param train_psize: specifies the percentage of train data within the whole dataset
        :return: tuple of training data and test dataset
        """
        if seed == None: seed = time.mktime(time.localtime())
        print "[ split_dateset ]... into train and test with seed:" + str(seed)
        np.random.seed(int(seed))
        np.random.shuffle(dataset)
        # only take effect for array, so need to convert to numpy.array before shuffle
        # 多维矩阵中，只对第一维（行）做打乱顺序操作
        train_size = (long(len(dataset) * train_psize) / batch_size) * batch_size
        test_size = (len(dataset) - train_size) / batch_size * batch_size
        train = dataset[0:train_size]
        test = dataset[train_size: train_size + test_size]
        print('[ Finish ] train_dataset: {}, test_dataset: {}'.format(len(train), len(test)))
        return train, test

    def create_feeddata_hp(self, dataset):
        """
        Splits dataset into data and labels.
        :param dataset: source dataset, a list of data cell of [bsdata, tsdata, rtdata, lbdata, tsdata_v, rtdata_v, lbdata_v]
        :return: tuple of (bsdata, tsdata, rtdata, lbdata, tsdata_v, rtdata_v, lbdata_v)
        """
        print "[ create_feeddata hp]..."
        rows = [len(dataset)]
        bsdata = np.zeros(rows + list(dataset[0][0].shape))
        tsdata = np.zeros(rows + list(dataset[0][1].shape))
        rtdata = np.zeros(rows + list(dataset[0][2].shape))
        lbdata = np.zeros(rows + list(dataset[0][3].shape))
        tsdata_v = np.zeros(rows + list(dataset[0][4].shape))
        rtdata_v = np.zeros(rows + list(dataset[0][5].shape))
        lbdata_v = np.zeros(rows + list(dataset[0][6].shape))
        tsdata_f = np.zeros(rows + list(dataset[0][7].shape))
        i = 0
        while i < len(dataset):
            bsdata[i] = dataset[i][0]
            tsdata[i] = dataset[i][1]
            rtdata[i] = dataset[i][2]
            lbdata[i] = dataset[i][3]
            tsdata_v[i] = dataset[i][4]
            rtdata_v[i] = dataset[i][5]
            lbdata_v[i] = dataset[i][6]
            tsdata_f[i] = dataset[i][7]
            i += 1
        return bsdata, tsdata, rtdata, lbdata, tsdata_v, rtdata_v, lbdata_v,tsdata_f

    def create_feeddata_hp_simple(self, dataset):
        """
        Splits dataset into data and labels.
        :param dataset: source dataset, a list of data cell of [bsdata, tsdata, rtdata, lbdata, tsdata_v, rtdata_v, lbdata_v]
        :return: tuple of (bsdata, tsdata, rtdata, lbdata, tsdata_v, rtdata_v, lbdata_v)
        """
        print "[ create_feeddata hp simple]..."
        rows = [len(dataset)]
        bsdata = np.zeros(rows + list(dataset[0][0].shape))
        tsdata = np.zeros(rows + list(dataset[0][1].shape))
        lbdata_v = np.zeros(rows + list(dataset[0][2].shape))
        i = 0
        while i < len(dataset):
            bsdata[i] = dataset[i][0]
            tsdata[i] = dataset[i][1]
            lbdata_v[i] = dataset[i][2]
            i += 1
        return bsdata, tsdata, lbdata_v

    def catnorm_data(self, data):
        data_y = data.copy()
        # K.clip(data_y, -10, 10)
        data_y[data_y < -2] = 1000
        data_y[data_y < 2] = 1001
        data_y[data_y < 1000] = 1002
        data_y = data_y - 1000
        data_y = np_utils.to_categorical(data_y, 3)
        return data_y

    def catnorm_data4(self, data):
        data_y = data.copy()
        # K.clip(data_y, -10, 10)
        data_y[data_y < -2] = 1000
        data_y[data_y < 2] = 1001
        data_y[data_y < 5] = 1002
        data_y[data_y < 1000] = 1003
        data_y = data_y - 1000
        data_y = np_utils.to_categorical(data_y, 4)
        return data_y

    def create_today_dataset_simple(self, lookback=5):
        """
        The function takes two arguments: the `dataset`, which is a NumPy array that we want to convert into a dataset,
        and the `lookback`, which is the number of previous time steps to use as input variables
        to predict the next time period — in this case defaulted to 5.
        symbs
        lookback: number of previous time steps as int
        returns a list of data cells of format([np.array(bsdata), tsdata, rtdata, lbdata])
        """
        rtlabels = ['code', 'open', 'high', 'trade', 'low', 'changepercent', 'turnoverratio']
        tsdataset = []
        rtdataset = []
        print ("[ create today's dataset ]... for price prodiction")

        tsdata_dict = self.get_newly_data(days=22)
        rtdata_df = ts.get_today_all()[rtlabels]
        symbs = np.array(rtdata_df['code'])
        rtset = np.array(rtdata_df.astype(float))
        for symb in tsdata_dict:
            if int(symb) not in intstr(symbs): continue
            tsdata_df= tsdata_dict[symb]
            rtdata_v = rtset[rtset[:,0] == int(symb)][0]
            if len(tsdata_df) >= lookback -1:
                if rtdata_v[-2] > 9.98 or rtdata_v[-1] == 0: continue
                tsdata_v = np.vstack([np.array(tsdata_df), rtdata_v[1:]])[-lookback:]
                ohcl = minmax_scale(tsdata_v[:,0:4])
                tsdata = np.hstack([ohcl, tsdata_v[:, 4:]])
                tsdataset.append(tsdata)
                rtdataset.append(rtdata_v)
        tsdataset = np.array(tsdataset)
        rtdataset = np.array(rtdataset)
        tsdata_dict.close()
        return tsdataset, rtdataset

    def create_val_dataset(self, lookback=5, days=1):
        """
        The function create day by day dataset for validating model
        The function takes two arguments: the `lookback`, which is the number of previous time steps to
        use as input variables to predict the next time period — in this case defaulted to 5.

        lookback: number of previous time steps as int
        days: days' of data to be used for validation
        returns a list of data cells of format([bsdata, tsdata, tsdata_v, lbdata_v])
        """
        rtlabels = ['code', 'open', 'high', 'trade', 'low', 'changepercent', 'turnoverratio']
        data_all = []
        print ("[ create dataset ]... for validation day by day")
        sdate = datetime.date.today() - timedelta(days=30)
        sdate = sdate.strftime('%Y-%m-%d')

        # get basic data(array) for all stocks
        bsset = self.get_bsdata()[bfeatures]
        bsset = bsset[bsset['pb'] > 0]
        symblist = intstr(list(bsset.index))
        bsset = preprocessing.scale(bsset)
        bsset = np.hstack([np.array(symblist).reshape(len(symblist),1), bsset])

        tsdata_dict = self.get_data(3100)
        for symb in tsdata_dict:
            if int(symb) not in symblist: continue

            tsdata_df= tsdata_dict[symb][tsfeatures]
            datelist = list(tsdata_df.index)
            datecol = np.array(intdate(mydate(datelist))).reshape(-1,1)
            bsdata = bsset[bsset[:,0]==int(symb)][0]  # sym,...
            if len(tsdata_df) >= lookback + days:
                dtcell = np.array(tsdata_df)[-lookback-days:]
                ohcl = minmax_scale(dtcell[:,0:4]) ## TODO error here, not testcase level normalization
                tsdata = np.hstack([datecol[-lookback-days:], ohcl, dtcell[:, 4:]])
                tsdata_v = np.hstack([datecol[-lookback-days:], dtcell])
                lbdata_v = np.hstack([np.zeros((days,1))+int(symb), datecol[-days:], dtcell[-days:]])
                data_cell = [bsdata, tsdata, tsdata_v, lbdata_v]
                data_all.append(data_cell)
        rows = [len(data_all)]
        bsdata = np.zeros(rows + list(data_all[0][0].shape))
        tsdata = np.zeros(rows + list(data_all[0][1].shape))
        tsdata_v = np.zeros(rows + list(data_all[0][2].shape))
        lbdata_v = np.zeros(rows + list(data_all[0][3].shape))
        i = 0
        while i < len(data_all):
            bsdata[i] = data_all[i][0]
            tsdata[i] = data_all[i][1]
            tsdata_v[i] = data_all[i][2]
            lbdata_v[i] = data_all[i][3]
            i += 1
        return bsdata, tsdata, tsdata_v, lbdata_v

def plot_out(sortout, x_index, y_index, points=200):
    step = len(sortout) / points
    plot_data = []
    i = 1
    plt.figure(1)
    while i * step < len(sortout):
        s = (i - 1) * step
        e = min(i * step, len(sortout))
        x = np.min(sortout[s:e, x_index])
        y = np.mean(sortout[s:e, y_index])
        plot_data.append([x, y])
        plt.plot(x, y, 'ro')
        i += 1
    plt.show()


def test_plot():
    d = np.loadtxt("./models/2017_02_23_18_23_20/2017_02_23_18_23_20_result.txt")
    plot_out(d, 2, 3)


def main():
    dmr = DataManager()
    # data = dmr.create_dataset(['601866'])
    # print '#####data samples#############'
    # print data[0:2]

    # train, test = dmr.split_dataset(data, 0.7)
    # print '#####train samples#############'
    # print train[0:2]
    #
    # print '#####test samples##############'
    # print test[0:2]
    #
    # data_x, data_y = dmr.split_label(train)
    # print '#####train_x samples############'
    # print data_x[0:2]
    #
    # print '#####train_y samples############'
    # print data_y[0:2]

    # todata = dmr.get_todaydata(22, True, 10)
    # print '#####today data samples############'
    # print todata

    # arr = ['2010-01-10','2014-12-21','2014-1-29']
    # lst = np.array([u'2017-02-27', u'2017-02-24', u'2017-02-23', u'2017-02-22', u'2017-02-21'], dtype=object)
    # mydate(arr)
    # mydate(lst)

    # import copy
    # data = np.array(dmr.create_dataset2(['601866','600151','600152','600153'])[:3])
    # origdata = data.copy()
    # np.random.shuffle(data)
    # print '#####get dataset2 samples############'
    # print data

    dmr.create_today_dataset_simple(5)

    # arr = np.arange(12).reshape(3,4)
    # print arr
    # a = minmax_scale(arr)
    # print a
    # print arr



if __name__ == '__main__':
    main()

"""
import DataManager as dm
dmr = dm.DataManager()
a,b,c = dmr.create_dataset(['601866'])
a,b = dmr.split_dataset(c,0.7)
"""

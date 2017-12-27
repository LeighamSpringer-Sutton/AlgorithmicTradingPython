from clr import AddReference

AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Data import *
from QuantConnect.Algorithm import *
from QuantConnect.Indicators import *
from System.Collections.Generic import List
import decimal as d
import numpy as np
import time
from datetime import datetime
import numpy as np
from scipy import stats
import pandas as pd


class AFCMOM(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''
        self.first = -1
        self.bi_weekly = 0
        self.SetStartDate(2006, 1, 1)
        self.SetEndDate(2009, 1, 1)
        self.SetCash(100000)
        self.spy = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.Debug("numpy test >>> print numpy.pi: " + str(np.pi))
        self.AddUniverse(self.CoarseSelectionFunction, self.FineSelectionFunction)
        self.UniverseSettings.Resolution = Resolution.Daily
        self.spy_200_sma = self.SMA("SPY", 200, Resolution.Daily)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Wednesday, DayOfWeek.Wednesday), \
                         self.TimeRules.At(12, 0), \
                         Action(self.rebalnce))
        self.stocks_to_trade = []

        self.SetWarmUp(201)

    def CoarseSelectionFunction(self, coarse):
        filtered_stocks = filter(lambda x: x.DollarVolume > 250000, coarse)
        filtered_stocks = filter(lambda x: x.HasFundamentalData, filtered_stocks)
        filtered_stocks = filter(lambda x: x.Price >= 20, filtered_stocks)
        filtered_stocks = filtered_stocks[:100]
        return [stock.Symbol for stock in filtered_stocks]

    def FineSelectionFunction(self, fine):
        filtered_stocks = filter(lambda x: x.SecurityReference.IsPrimaryShare, fine)
        return [stock.Symbol for stock in filtered_stocks]

    def OnSecuritiesChanged(self, changes):
        dt = datetime(self.Time.year, self.Time.month, self.Time.day)
        if dt.weekday() != 3 or self.Securities[self.spy].Price < self.spy_200_sma.Current.Value:
            return
        self.stocks_to_trade = [stock.Symbol for stock in changes.AddedSecurities]
        if self.stocks_to_trade:
            for stock in self.stocks_to_trade:
                ATR = self.my_ATR(stock, 14)
                self.stocks_to_trade.sort(key=lambda x: self.get_slope(stock, 90), reverse=True)
                maximum_range = int(round(len(self.stocks_to_trade) * 0.10))
                self.stocks_to_trade[:maximum_range]
                cash = float(self.Portfolio.Cash)
                oo = len(self.Transactions.GetOpenOrders(stock))
                if self.Securities[stock].Price > self.moving_average(stock, 100) and not self.gapper(stock,
                                                                                                      90) and cash > 0 and not oo:
                    self.SetHoldings(stock, self.weight(stock, ATR))

    def rebalnce(self):
        self.bi_weekly += 1
        if self.bi_weekly % 2 == 0:
            for stock in self.Portfolio.Values:
                if stock.Invested:
                    symbol = stock.Symbol
                    shares_held = float(self.Portfolio[symbol].Quantity)
                    if (self.Securities[symbol].Price < self.moving_average(symbol, 100) and shares_held > 0) or (
                        self.gapper(symbol, 90) and shares_held > 0):
                        self.Liquidate(symbol)
                    else:
                        if shares_held > 0:
                            ATR = self.my_ATR(symbol, 20)
                            cost_basis = float(self.Portfolio[symbol].AveragePrice)
                            shares_held = float(self.Portfolio[symbol].Quantity)
                            percent_of_p = ((cost_basis * shares_held) / float(self.Portfolio.TotalPortfolioValue))
                            weight = self.weight(symbol, ATR)
                            diff_in_desired_weight = weight - percent_of_p
                            if diff_in_desired_weight < 0:
                                order_amount = shares_held * diff_in_desired_weight
                                self.MarketOrder(symbol, order_amount)

    def gapper(self, security, period):
        if not self.Securities.ContainsKey(security):
            return True
        security_data = self.History(security, period, Resolution.Daily)
        if 'close' not in security_data.columns:
            return True
        if len(security_data['close']) < 2:
            return True
        close_data = [float(data) for data in security_data['close']]
        return np.max(np.abs(np.diff(close_data)) / close_data[:-1]) >= 0.15

    def get_slope(self, security, period):
        if not self.Securities.ContainsKey(security):
            return 0
        security_data = self.History(security, period, Resolution.Daily)
        if 'close' not in security_data:
            return 0
        y = [np.log(float(data)) for data in security_data['close']]
        x = [range(len(y))]
        slope, r_value = stats.linregress(x, y)[0], stats.linregress(x, y)[2]
        return ((np.exp(slope) ** 252) - 1) * (r_value ** 2)

    def my_ATR(self, security, period):
        if not self.Securities.ContainsKey(security):
            return 0
        self.first += 1
        security_data = self.History([security], period, Resolution.Daily)
        c_data = [float(data) for data in security_data['close']]
        l_data = [float(data) for data in security_data['low']]
        h_data = [float(data) for data in security_data['high']]
        true_range = [h - l for h, l in zip(h_data, l_data)]
        average_true_range = np.mean(true_range)
        average_true_range_smooted = ((average_true_range * 13) + true_range[-1]) / 14
        return average_true_range_smooted if not self.first else average_true_range

    def weight(self, security, atr):
        risk = float(self.Portfolio.TotalPortfolioValue) * 0.0001
        return (
        ((risk / atr) * float(self.Securities[security].Price)) / float(self.Portfolio.TotalPortfolioValue) * 100)

    def moving_average(self, security, period):
        if not self.Securities.ContainsKey(security):
            return 0
        security_data = self.History(security, period, Resolution.Daily)
        return np.mean([close for close in security_data['close']])
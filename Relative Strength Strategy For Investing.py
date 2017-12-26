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
from datetime import timedelta


### <summary>
##Remvoing an if statement increased the returns by 4 %
### </summary>
class BasicTemplateAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.SetStartDate(2010, 10, 07)  # Set Start Date
        self.SetEndDate(2012, 10, 01)  # Set End Date
        self.SetCash(100000)  # Set Strategy Cash
        ## N=Normal (Manufacturing), M=Mining, U=Utility, T=Transportation, B=Bank, I=Insurance
        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddUniverse(self.CoarseSelectionFunction, self.FineSelectionFunction)
        self.bond = self.AddEquity('TLT', Resolution.Daily).Symbol
        self.spy = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.spy_sma = self.SMA('SPY', 200, Resolution.Daily)
        self.first = 0
        self.month = 0
        self.Top_sector = ''
        self.The_sectors = {"XME|M": 0, "KIE|I": 0, "XLU|U": 0, "XLF|B": 0, "IYT|T": 0, }
        for symbol in self.The_sectors:
            self.AddEquity(symbol.split('|')[0], Resolution.Daily)
            self.The_sectors[symbol] = self.MOM(symbol.split('|')[0], 30, Resolution.Daily)
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.At(3, 45), Action(self.rebalance))
        self.SetWarmUp(200)

    def CoarseSelectionFunction(self, coarse):
        filtered_stocks = filter(lambda x: x.HasFundamentalData, coarse)
        filtered_stocks = list(filter(lambda x: x.DollarVolume > 250000, filtered_stocks))
        filtered_stocks.sort(key=lambda x: x.DollarVolume)
        return [stock.Symbol for stock in filtered_stocks[:50]]

    def FineSelectionFunction(self, fine):
        ready = [indicator.IsReady for indicator in self.The_sectors.values()]
        if not ready:
            return
        if not self.first:
            self.Top_sector = max(self.The_sectors, key=self.The_sectors.get).split('|')[-1]
            self.first += 1
        filtered_stocks = list(filter(lambda x: self.Top_sector in str(x.CompanyReference.IndustryTemplateCode), fine))
        return [stock.Symbol for stock in filtered_stocks[:5]]

    def OnSecuritiesChanged(self, changes):
        if self.spy_sma.IsReady:
            if self.Securities[self.spy].Price > self.spy_sma.Current.Value:
                for stock in self.Portfolio.Values:
                    bond = [stock.Symbol for stock in self.Portfolio.Values if
                            stock.Invested and str(stock.Symbol).split(' ')[0] == 'TLT']
                    if bond:
                        self.Liquidate('TLT')
                        self.Log("Bonds were here")
                    else:
                        for stock in changes.AddedSecurities:
                            oo = len(self.Transactions.GetOpenOrders(stock.Symbol))
                            cash = float(self.Portfolio.Cash)
                            if not oo and cash > 0 and str(stock.Symbol).split(' ')[0] != 'SPY':
                                self.SetHoldings(stock.Symbol, 0.10)

    def rebalance(self):
        self.month += 1
        if self.month % 25 == 0:
            curr_best_sector = max(self.The_sectors, key=self.The_sectors.get).split('|')[-1]
            if self.Top_sector != curr_best_sector:
                self.Top_sector = curr_best_sector
                bond = [stock.Symbol for stock in self.Portfolio.Values if
                        stock.Invested and str(stock.Symbol).split(' ')[0] == 'TLT']
                if not bond:
                    self.Liquidate()
                    time.sleep(20)
            if self.spy_sma.IsReady and not self.Portfolio.HoldStock:
                if self.Securities[self.spy].Price < self.spy_sma.Current.Value:
                    self.SetHoldings(self.bond, 1)
                    self.Log('Should buy TLT')
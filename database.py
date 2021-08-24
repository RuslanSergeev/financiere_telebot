import pandas as pd
from functools import partial
from collections import namedtuple

Date = namedtuple('Date', ['day', 'month', 'year'])

class Database:
    def __init__(self, file_name):
        self.file_name = file_name
        self.data = pd.read_csv(self.file_name)

    def add_record(self, record):
        self.data = self.data.append(record, ignore_index=True)
        self.data.to_csv(self.file_name, index=False)

    def get_day_stats(self, day):
        frames = self.data.loc[
            self.data['date']==day, 
            ['date', 'time', 'purpose', 'amount', 'currency', 'description']
        ]
        status = len(frames) > 0
        return status, frames

    def is_same_month(self, date1, date2):
        return date1.month == date2.month and date1.year == date2.year

    def get_month_entries(self, date):
        today_date = Date(*date.split('.'))
        dates = self.data['date'].apply(lambda date: Date(*date.split('.')))
        cur_month = partial(self.is_same_month, today_date)
        frames = self.data.loc[
            dates.apply(cur_month),
        ]
        return frames

    def get_month_stats(self, date):
        today_date = Date(*date.split('.'))
        cur_month = partial(self.is_same_month, today_date)
        frames = self.data.loc[
            cur_month( Date(*self.data['date'].split('.')) ),
            ['date', 'time', 'purpose', 'amount', 'currency', 'description']
        ]
        status = len(frames) > 0
        return status, frames

    def get_duty_entries(self, date):
        '''Everythng without pocket_money and targets is a duty
           Show how much everyone spent on duties. 
           Later on we could substract this from the salary to 
           compute the member debt.
        '''
        frames = self.get_month_entries(date)
        nodept_categories = ['pocket_money', 'targets']
        nodebt_filter = lambda rec: rec['purpose'] not in nodept_categories
        frames = frames.loc [
            frames.apply(nodebt_filter, axis=1),
            ['role', 'amount', 'currency', 'purpose', 'description']
        ]
        status = len(frames) > 0
        return status, frames

    def get_pocket_summary(self, date):
        frames = self.get_month_entries(date)
        frames = frames.loc[
            frames['purpose']=='pocket_money',
            ['role', 'amount', 'currency']
        ]
        status = len(frames) > 0
        return status, frames

    def get_groceries_summary(self, date):
        frames = self.get_month_entries(date)
        frames = frames.loc[
            frames['purpose']=='groceries',
            ['amount', 'currency']
        ]
        status = len(frames) > 0
        return status, frames


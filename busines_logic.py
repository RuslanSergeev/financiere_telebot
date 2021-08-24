from functools import partial
from pay_calc import PayCalc
from database import Database
from telegram import Update
import dataframe_image as dfi
import pandas as pd
import time
import re
import json

class Logic:
    def __init__(self,
        database: str,
        telegram_config: str,
        budget_config: str, 
        currency: str
    ):
        self.database = Database(database)
        self.pay_calc = PayCalc(budget_config, currency)
        self.budget_config = self.load_config(budget_config)
        self.telegram_config = self.load_config(telegram_config)
        self.currency = currency

    def load_config(self, config: str) -> dict:
        with open(config, 'r') as config_file:
            return json.load(config_file)


    def buy(self, update: Update) -> str:
        record, status = self._make_record(update)
        if record is not None:
            self.database.add_record(record)
            reply = f'buy {status} 👌\n'
        else:
            reply = f'buy error 🚫:\n' + status
        return reply

    def get_expenses(self, update: Update) -> str:
        expenses = self._get_raw_expenses()
        expenses = list(map(str.lower, expenses))
        expenses.append('pocket_money')
        expenses.append('targets')
        reply = '\n'.join(expenses)
        return reply

    def get_expenses_stats(self, update: Update) -> bool:
        ''' compute how much family members spent
        on duties this month and who originally should 
        pay for it. As well as how much left to pay.
        '''
        today_date = time.strftime('%d.%m.%Y')
        status, frames = self.database.get_duty_entries(today_date)
        frames['currency'] = frames['currency'].apply(
            self.pay_calc.convert_currency_name
        )
        converter = partial(
            self.pay_calc.convert_currency,
            self.currency
        )
        #conver everything to default currency
        frames = frames.apply(converter, axis=1)
        frames = frames.groupby('purpose').sum()

        # duties accordint the initial plan
        expenses = pd.DataFrame(self.pay_calc.config['expenses'])
        expenses = expenses[['purpose', 'amount', 'currency']]
        expenses = expenses.apply(converter, axis=1)
        expenses = expenses.groupby('purpose').sum()

        #substract frame amounts from incomes
        for purp in expenses.index.tolist():
            if purp in frames.index:
                expenses.loc[purp, 'amount'] += frames.loc[purp, 'amount']

        #export to debt png
        if len(expenses) > 0:
            dfi.export(expenses, 'expenses_stats.png')

        return status

    def get_month_stats(self, update: Update) -> bool:
        reply = 'month stats'
        return reply

    def dayly_job(self) -> list:
        month_day = int(time.strftime('%d'))
        payments = self.pay_calc.get_today_payments(month_day)
        if len(payments) > 0:
            dfi.export(pd.DataFrame(payments), 'payments.png')
        return len(payments) > 0

    def get_day_stats(self, update: Update) -> bool:
        today_date = time.strftime('%d.%m.%Y')
        status, frames = self.database.get_day_stats(today_date)
        print(frames)
        if len(frames) > 0:
            dfi.export(frames, 'daystats.png')
            status = True
        return status

    def get_pocket_summary(self, update: Update, currency: str) -> bool:
        today_date = time.strftime('%d.%m.%Y')
        status, frames = self.database.get_pocket_summary(today_date)
        frames['currency'] = frames['currency'].apply(
            self.pay_calc.convert_currency_name
        )
        converter = partial(
            self.pay_calc.convert_currency,
            currency
        )
        frames = frames.apply(converter, axis=1)
        frames = frames.groupby('role').sum()
        if len(frames) > 0:
            dfi.export(frames, 'pocket_summary.png')
            status=True
        return status

    def get_groceries_summary(self, update: Update, currency: str) -> str:
        today_date = time.strftime('%d.%m.%Y')
        status, frames = self.database.get_groceries_summary(today_date)
        frames['currency'] = frames['currency'].apply(
            self.pay_calc.convert_currency_name
        )
        converter = partial(
            self.pay_calc.convert_currency,
            currency
        )
        frames = frames.apply(converter, axis=1)
        groceries_sum = frames['amount'].sum()
        return status, str(groceries_sum)

    def get_debt_summary(self, update: Update) -> bool:
        ''' Everything earned, except pocket money, 
            and what is spent on duties, should be counted as debt.
        '''
        today_date = time.strftime('%d.%m.%Y')
        status, frames = self.database.get_duty_entries(today_date)
        frames['currency'] = frames['currency'].apply(
            self.pay_calc.convert_currency_name
        )
        converter = partial(
            self.pay_calc.convert_currency,
            self.currency
        )
        #conver everything to default currency
        frames = frames.apply(converter, axis=1)
        frames = frames.groupby('role').sum()
        incomes = self.pay_calc.get_incomes()
        pocket_money = self.pay_calc.get_pocket_money()
        #substract frame amounts from incomes
        for role in frames.index:
            frames.loc[role, 'amount'] += incomes[role] - pocket_money[role]

        #export to debt png
        if len(frames) > 0:
            dfi.export(frames, 'debt_summary.png')

        return status


# private section

    def _get_raw_expenses(self) -> dict:
        expenses = dict(map(
            lambda ex: (ex['purpose'], ex['role']), 
            self.budget_config['expenses']
        ))
        return expenses

    def _get_username_by_id(self, id: int) -> str:
        users = self.telegram_config['allowed_users']
        reverse_config = dict(
            zip(users.values(), users.keys())
        )
        return reverse_config[id]

    def _make_record(self, update: Update):
        lines = list(map(str.strip, update.message.text.split('\n')))
        len_ok = len(lines) >= 2
        if not len_ok:
            return ( None, 
                'wrong message format\n'
                'should be:\n'
                '#purpose\n'
                'description\n'
                '+-amount'
            )
        # everything except the leading # symbol
        category = lines[0][lines[0].index('#')+1:].lower()
        all_categories = list(map(
            str.lower, 
            self._get_raw_expenses()
        ))
        all_categories.append('pocket_money')
        all_categories.append('targets')
        category_ok = category in all_categories
        if not category_ok:
            return ( None, 
                'category unrecognized\n'
                'see \\help\n'
            )
        amount_ok = re.match(
            r'([+-]?([0-9]|\.)+)[\ ]*([$€₽]|rub|eur|usd|EUR|USD|RUB)', 
            lines[-1]
        )
        if not amount_ok:
            return ( None,
                'amount unrecognized\n'
                'should be a number followed by a currency symbol'
            )
        if len_ok and category_ok and amount_ok:
            # get currency in well known format
            rec_currency = self.pay_calc.convert_currency_name(amount_ok.group(3))
            # current date: 'dd.mm.yyyy'
            msg_date = time.strftime('%d.%m.%Y')
            # current time 'hh:mm':
            msg_time = time.strftime('%H:%M')
            return ({
                'date': msg_date,
                'time': msg_time,
                'purpose': category,
                'role': self._get_username_by_id(update.effective_user.id),
                'amount': float(amount_ok.group(1)),
                'currency': rec_currency,
                'description': '\n'.join(lines[1:-1]).replace(',', '.')
            }, 'ok')
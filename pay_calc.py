import json
from functools import partial
from functools import reduce

class PayCalc:
    def __init__(self, config_name: str, currency_name: str):
        self.config_name = config_name
        self.config = self.get_config(config_name, currency_name)
        self.roles = self.get_roles()
        self.expenses = self.get_expenses()
        self.incomes = self.get_incomes()
        self.pocket_money = self.get_pocket_money()
        self.debt = self.get_role_debt()

    def convert_currency_name(self, currency_name: str) -> str:
        return {
            '$': 'usd',
            '₽': 'rub',
            '€': 'eur',
            'EUR': 'eur',
            'RUB': 'rub',
            'USD': 'usd',
            'rub': 'rub',
            'usd': 'usd',
            'eur': 'eur'
        }[currency_name]

    def convert_amount(self, amount, currency_in, currency_out):
        # convert amount from one currency to a given one
        return amount * self.course[currency_in][currency_out]

    def convert_currency(self, currency, record):
        # convert grossbook record amount from one currency to a given one
        record['amount'] = self.convert_amount(record['amount'], record['currency'], currency)
        record['currency'] = currency
        return record

    def section_sum(self, section, role):
        # get sum of section amount for a given role
        role_records = list(filter(lambda rec: rec['role'] == role, section))
        return sum(map(lambda rec: rec['amount'], role_records))

    def get_config(self, config_name:str, currency_name: str) -> dict:
        with open(config_name, 'r') as config_file:
            config = json.load(config_file)
        self.course = config['course']
        converter = partial(self.convert_currency, currency_name)
        config = {k: list(map(converter, v)) for k, v in config.items() if k != 'course'}
        return config

    def get_roles(self) -> list:
        # get roles list
        records = list(reduce(lambda x, y: x + y, self.config.values()))
        roles =  list(set(map(lambda rec: rec['role'], records)))
        return list(filter(lambda role: role, roles))

    def get_expenses(self) -> dict:
        #get role expenses dict
        roles = self.get_roles()
        expenses = dict(map(lambda role: (role, self.section_sum(self.config['expenses'], role)), roles))
        return expenses

    def get_incomes(self) -> dict:
        #get role expenses dict
        roles = self.get_roles()
        incomes = dict(map(lambda role: (role, self.section_sum(self.config['incomes'], role)), roles))
        return incomes

    def get_pocket_money(self) -> dict:
        # get role pocket money dict
        roles = self.get_roles()
        pocket_money = dict(map(lambda role: (role, self.section_sum(self.config['pocket_money'], role)), roles))
        return pocket_money

    def get_today_payments(self, day: int) -> dict:
        with open(self.config_name, 'r') as config_file:
            config = json.load(config_file)
        return list(filter(lambda ex:ex['date'] == day, config['expenses']))

    def get_role_debt(self) -> dict:
        # get role debt dict
        incomes = self.get_incomes()
        expenses = self.get_expenses()
        pocket_money = self.get_pocket_money()
        role_debt = lambda role: incomes[role] - expenses[role] - pocket_money[role]
        return dict(map(lambda role: (role, role_debt(role)), self.get_roles()))
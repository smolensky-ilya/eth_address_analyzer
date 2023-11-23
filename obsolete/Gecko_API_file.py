import requests
import pandas as pd
from time import sleep


class Gecko:
    def __init__(self,
                 sleep_time=30,
                 filename='ticker_prices_gecko.csv',
                 col_names=('timeStamp', 'tokenSymbol', 'hist_price'),
                 save_frequency=1):
        self.col_names = col_names
        self.save_frequency = save_frequency
        self.collected_until_save = 0
        self.sleep_time = sleep_time
        self.filename = filename
        self.dataframe = self.open_existing()
        self.list_of_coins_gecko = self.get_a_list_of_gecko_coins()

    def open_existing(self):
        try:
            return pd.read_csv(self.filename)
        except FileNotFoundError:
            return self.create_empty()

    def create_empty(self, timestamp=None, symbol=None, hist_price=None):
        self.dataframe = pd.DataFrame({self.col_names[0]: [] if timestamp is None else [timestamp],
                                       self.col_names[1]: [] if symbol is None else [symbol],
                                       self.col_names[2]: [] if hist_price is None else [hist_price]})
        return self.dataframe

    def save_data(self):
        self.dataframe.to_csv(self.filename, index=False)

    def update_data(self, token, date, price):
        self.dataframe = pd.concat([self.dataframe, self.create_empty(timestamp=date, symbol=token, hist_price=price)])
        self.collected_until_save += 1
        if self.collected_until_save == self.save_frequency:
            print(f'{self.collected_until_save} new entries were saved to the file.')
            self.save_data()
            self.collected_until_save = 0

    def get_price(self, token, date):
        res = self.check_if_exists(token, date)
        if res is None:
            price_parsed = self.parse_gecko_api(token, date)
            self.update_data(token=token, date=date, price=price_parsed)
            return price_parsed
        else:
            #print(f'Found saved: {token}: {res} on {date}')
            return res

    def check_if_exists(self, token, date):
        try:
            res = self.dataframe[(self.dataframe[self.col_names[1]] ==
                                  token) & (self.dataframe[self.col_names[0]] == date)].\
                                  reset_index()[self.col_names[2]][0]
        #print(res)
            return res
        except KeyError:
            return None

    def parse_gecko_api(self, token, date):
        headers = {'Accept': 'application/json'}
        if_one_ticker = 0
        while True:
            necessary_name = [x['id'] for x in self.list_of_coins_gecko if x['symbol'] == token.lower()]
            if len(necessary_name) == 0:
                print(f'No such coin was found: {token}')
                return 'NO_SUCH_COIN*'
            sleep(3)
            result = requests.get(
                f'https://api.coingecko.com/api/v3/coins/{necessary_name[if_one_ticker]}/history?date={date}&localization=False',
                headers=headers).json()
            if 'status' in result.keys():
                print(f'resting for {self.sleep_time}')
                sleep(self.sleep_time)
            else:
                if 'market_data' in result.keys():
                    success = result['market_data']['current_price']['usd']
                    print(f'Found {token} on {date}: {success}')
                    return success
                else:
                    if len(necessary_name) - 1 <= if_one_ticker:
                        print(f"Couldn't find the price of {token} on {date}")
                        return 'NO_PRICE_FOUND*'
                    else:
                        if_one_ticker += 1

    def get_a_list_of_gecko_coins(self):
        while True:
            list_of_coins_gecko = requests.get('https://api.coingecko.com/api/v3/coins/list').json()
            if isinstance(list_of_coins_gecko, list):
                return list_of_coins_gecko
            if list_of_coins_gecko['status']['error_code'] == 429:
                print(f'sleeping for {self.sleep_time}')
                sleep(self.sleep_time)
            else:
                print('Smth went wrong with the list of coins*')
                break


def main():
    g = Gecko()
    print(g.get_price('CVX', '09-10-2022'))


if __name__ == '__main__':
    main()

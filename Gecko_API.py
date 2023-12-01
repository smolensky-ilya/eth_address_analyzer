import requests
import pandas as pd
from time import sleep
from sqlalchemy import create_engine
from streamlit import secrets
from datetime import date, datetime, timedelta
import logging
from config import configure_logging, conf_day_shift_hours, conf_gecko_coin_exceptions
configure_logging()


class Gecko:
    def __init__(self, sleep_time=30, save_frequency=10, no_coin_message='NO_SUCH_COIN*',
                 no_price_message='NO_PRICE_FOUND*'):
        self.format_df = {'timeStamp': [], 'tokenSymbol': [], 'hist_price': []}
        self.engine = create_engine(secrets['db_con_string'])
        self.table_name = secrets['ticker_prices_table_name']
        self.query_to_read = f'select * from {self.table_name}'
        self.save_frequency = save_frequency
        self.collected_until_save = 0
        self.new_entries_to_save = pd.DataFrame(self.format_df)
        self.message_if_no_coin = no_coin_message
        self.message_if_no_price = no_price_message
        self.sleep_time = sleep_time
        self.dataframe = self.open_existing()
        self.list_of_coins_gecko = self.get_a_list_of_gecko_coins()
        self.exceptions = conf_gecko_coin_exceptions
        self.day_shift_hours = conf_day_shift_hours

    def open_existing(self):
        logging.debug('Price parser: connected to the DB.')
        return pd.read_sql(self.query_to_read, self.engine)

    def save_data(self):
        self.new_entries_to_save.to_sql(self.table_name, self.engine, if_exists='append', index=False)
        logging.debug(f'{len(self.new_entries_to_save)} new ticker prices were added to the DB.')
        self.collected_until_save = 0
        self.new_entries_to_save = pd.DataFrame(self.format_df)

    def update_data(self, token, date_, price):
        temp_df = pd.DataFrame({'timeStamp': [date_], 'tokenSymbol': [token], 'hist_price': [price]})
        self.dataframe = pd.concat([self.dataframe, temp_df])
        self.new_entries_to_save = pd.concat([self.new_entries_to_save, temp_df])
        self.collected_until_save += 1
        if self.collected_until_save == self.save_frequency:
            self.save_data()

    def get_price(self, token, date_):
        # If too little time has passed since the start of the day, prices on CoinGecko may not have been formed yet
        # - shifting day to yesterday
        if int(datetime.now().hour) < self.day_shift_hours and date_ == datetime.now().today().strftime('%d-%m-%Y'):
            logging.info("It's too early to parse today's price - taking yesterday's.")
            transformed_date = [int(x) for x in date_.split('-')]
            date_ = (datetime(day=transformed_date[0], month=transformed_date[1], year=transformed_date[2]) -
                     timedelta(days=1)).strftime('%d-%m-%Y')
        # Continuing to search in saved or parse
        res = self.check_if_exists(token, date_)
        if res is None:
            price_parsed = self.parse_gecko_api(token, date_)
            if price_parsed != self.message_if_no_coin:
                self.update_data(token=token, date_=date_, price=price_parsed)
            return price_parsed
        else:
            logging.debug(f'Found saved: {token}: {res} on {date_}')
            return res

    def check_if_exists(self, token, date_):
        try:
            res = self.dataframe[(self.dataframe['tokenSymbol'] ==
                                  token) & (self.dataframe['timeStamp'] == date_)].\
                                  reset_index()['hist_price'][0]
            return res
        except KeyError:
            return None

    def parse_gecko_api(self, token, date_):
        headers = {'Accept': 'application/json'}
        if_one_ticker = 0
        while True:
            necessary_name = [x['id'] for x in self.list_of_coins_gecko if x['symbol'] == token.lower()]
            if len(necessary_name) == 0:
                logging.debug(f'No such coin was found: {token}')
                return self.message_if_no_coin
            sleep(3)
            name = self.exceptions[token] if token in self.exceptions.keys() \
                else necessary_name[if_one_ticker]
            result = requests.get(f'https://api.coingecko.com/api/v3/coins/'
                                  f'{name}/history?date={date_}&localization=False',
                                  headers=headers).json()
            if 'status' in result.keys():
                logging.debug(f'resting for {self.sleep_time}')
                sleep(self.sleep_time)
            else:
                if 'market_data' in result.keys():
                    success = result['market_data']['current_price']['usd']
                    logging.debug(f'Found {token} on {date_}: {success}')
                    return success
                else:
                    if len(necessary_name) - 1 <= if_one_ticker:
                        logging.debug(f"Couldn't find the price of {token} on {date_}")
                        return self.message_if_no_price
                    else:
                        if_one_ticker += 1

    def get_a_list_of_gecko_coins(self):
        # CHECKING THE DATE OF EXISTING
        existing = pd.read_sql(f'select * from {secrets["ticker_table_name"]}', self.engine)
        if date.today() == existing['date_'][0]:
            logging.debug('No need to load a new list!')
            return existing[['id', 'symbol', 'name']].to_dict(orient='records')

        while True:
            list_of_coins_gecko = requests.get('https://api.coingecko.com/api/v3/coins/list').json()
            if isinstance(list_of_coins_gecko, list):
                # SAVING A NEW ONE
                logging.debug('Loading a new list!')
                to_save = pd.DataFrame(list_of_coins_gecko)
                to_save['date_'] = [date.today() for _ in range(len(to_save))]
                to_save.to_sql('gecko_list', self.engine, if_exists='replace', index=False)
                return list_of_coins_gecko
            if list_of_coins_gecko['status']['error_code'] == 429:
                logging.debug(f'sleeping for {self.sleep_time}')
                sleep(self.sleep_time)
            else:
                logging.error('Smth went wrong with the list of coins*')
                break


def main():
    g = Gecko()
    print(g.get_price('ETH', '01-12-2023'))


if __name__ == '__main__':
    main()

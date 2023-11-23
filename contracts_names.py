import requests
import pandas as pd
from bs4 import BeautifulSoup
from time import sleep
from stqdm import stqdm
from sqlalchemy import create_engine
from streamlit import secrets
from datetime import date
import logging
from config import configure_logging
configure_logging()


class ContractDb:
    def __init__(self, sleep_time=3, untagged_name='Untagged*', bar=False, threshold_to_save=5):
        self.format_df = {'date_': [], 'address': [], 'nametag': []}
        self.dataframe = pd.DataFrame(self.format_df)
        self.new_df_to_save = pd.DataFrame(self.format_df)
        self.engine = create_engine(secrets['db_con_string'])
        self.table_name = secrets['contracts_table_name']
        self.query_to_read = f'select * from {self.table_name}'
        self.threshold_to_save = threshold_to_save
        self.new_entries = 0
        self.sleep_time = sleep_time
        self.untagged_name = untagged_name
        self.bar = bar
        self.nametag_max_symbols = 25
        self.open_db()

    def open_db(self):
        self.dataframe = pd.read_sql(self.query_to_read, self.engine)
        logging.debug('Name Tags Parser: connected to the DB.')

    def check_name(self, address):
        address = address.lower()
        try:
            return self.dataframe[self.dataframe['address'] == address].copy().reset_index()['nametag'][0]
        except KeyError:
            sleep(self.sleep_time)
            get_it = self.parse_etherscan(address)
            temp_df = pd.DataFrame({'date_': [date.today()],
                                    'address': [address],
                                    'nametag': [get_it]})
            self.new_df_to_save = pd.concat([self.new_df_to_save, temp_df])
            self.dataframe = pd.concat([self.dataframe, temp_df])
            logging.debug(f'Parsed: {address} : {get_it}')
            self.new_entries += 1
            if self.threshold_to_save == self.new_entries:
                self.save_db()
            return get_it

    def save_db(self):
        self.new_df_to_save.to_sql(self.table_name, self.engine, if_exists='append', index=False)
        logging.debug(f'{len(self.new_df_to_save)} new entries were added to the DB.')
        self.new_entries = 0
        self.new_df_to_save = pd.DataFrame(self.format_df)

    def get_name(self, address):
        if isinstance(address, list):
            res_dict = {}
            if self.bar:
                for each in stqdm(address, desc=f"Parsing addresses' name tags from Etherscan"):
                    res_dict[each] = self.check_name(each)
            else:
                for each in address:
                    res_dict[each] = self.check_name(each)
            return res_dict
        elif isinstance(address, str):
            res = self.check_name(address)
            return res
        else:
            raise "The stuff you gave me is NEITHER a LIST NOR a STR. Fix that!"

    def parse_etherscan(self, address):
        headers = {"User-Agent": "Mozilla/5.0",
                   "Content-Type": "application/json; charset=UTF-8"}
        url = f"https://etherscan.io/address/{address}"
        html_raw = requests.get(url, headers=headers)
        soup = BeautifulSoup(html_raw.text, "lxml")
        res = [x.strip() for x in soup.title.string.split('|')][0]
        if 'address' in res.lower():
            try:
                res = soup.find("div", class_='d-flex align-items-center gap-1 mt-2').get_text(strip=True)
            except AttributeError:
                try:
                    res = soup.find("span", class_='hash-tag text-truncate').get_text()  # works with contract names
                except AttributeError:
                    try:
                        res = soup.find("div", class_='d-flex flex-wrap align-items-center gap-1') \
                            .find("div", class_='d-flex align-items-center gap-1').get_text(
                            strip=True)  # other name tags
                    except AttributeError:
                        return self.untagged_name
            if res[:7].lower() == address[:7].lower():  # to avoid returning shortened addresses
                return self.untagged_name
            else:
                if len(res) > self.nametag_max_symbols:  # in case it's too long
                    res = res[:self.nametag_max_symbols] + "..."
            return res
        else:
            return res


def main():  # testing
    db = ContractDb(threshold_to_save=300)
    print(db.get_name("0x8454178B380C115EdC9c8465f8DA0DceAe3DdFD0"))


if __name__ == "__main__":
    main()

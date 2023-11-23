import requests
import pandas as pd
from bs4 import BeautifulSoup
from time import sleep
from stqdm import stqdm


class ContractDb:
    def __init__(self, sleep_time=3, untagged_name='Nope*', bar=False):
        self.db_filename = 'contracts.csv'
        self.dataframe = pd.DataFrame({'address': [],
                                       'nametag': []})
        self.need_to_save = False  # the flag is True when a new nametag was parsed
        self.sleep_time = sleep_time
        self.untagged_name = untagged_name
        self.bar = bar

    def create_db(self):
        self.dataframe.to_csv(self.db_filename, index=False)
        print(f'{self.db_filename} was created')

    def open_db(self):
        try:
            self.dataframe = pd.read_csv(self.db_filename)
            return self.dataframe
        except FileNotFoundError:
            self.create_db()
            self.dataframe = pd.read_csv(self.db_filename)
            return self.dataframe

    def check_name(self, address):
        try:
            return self.dataframe[self.dataframe['address'] == address].copy().reset_index()['nametag'][0]
        except KeyError:
            sleep(self.sleep_time)
            get_it = self.parse_etherscan(address)
            self.dataframe = pd.concat([self.dataframe, pd.DataFrame({'address': [address], 'nametag': [get_it]})])
            print(f'Parsed: {address} : {get_it}')
            self.need_to_save = True
            return get_it

    def save_db(self):
        self.dataframe.to_csv(self.db_filename, index=False)
        print(f'{self.db_filename} was updated')
        self.need_to_save = False

    def get_name(self, address):
        self.open_db()
        if isinstance(address, list):
            res_dict = {}
            if self.bar:
                for each in stqdm(address, desc=f"Parsing addresses' name tags from Etherscan"):
                    res_dict[each] = self.check_name(each)
            else:
                for each in address:
                    res_dict[each] = self.check_name(each)
            if self.need_to_save:
                self.save_db()
            return res_dict
        elif isinstance(address, str):
            res = self.check_name(address)
            if self.need_to_save:
                self.save_db()
            return res
        else:
            raise "The stuff you gave me is NEITHER a LIST NOR a STR. Fix that!"

    def parse_etherscan(self, address):
        headers = {"User-Agent": "Mozilla/5.0",
                   "Content-Type": "application/json; charset=UTF-8"}
        url = f"https://etherscan.io/address/{address}"
        html_raw = requests.get(url, headers=headers)
        soup = BeautifulSoup(html_raw.text, "lxml")
        try:
            res = soup.find("span", class_='hash-tag text-truncate').get_text()
            if res[:7] == address[:7]:  # AVOIDING GIVING US SHORT ADDRESS
                return self.untagged_name
            else:
                return res
        except AttributeError:
            return self.untagged_name


def main():
    db = ContractDb()
    print(db.get_name(['0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe',
                       '0xd780A24eEA789C922B04C6a2c532796b089F0E5F',
                       '0x9F3748c873385E85B174d6E6F5242a89D380e7EA',
                       '0xD322A49006FC828F9B5B37Ab215F99B4E5caB19C',
                       '0x8454178B380C115EdC9c8465f8DA0DceAe3DdFD0',
                       '0x99FD1378ca799ED6772Fe7bCDC9B30B389518962']))


if __name__ == "__main__":
    main()

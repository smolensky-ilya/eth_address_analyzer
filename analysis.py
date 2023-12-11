import requests
import pandas as pd
import numpy as np
from time import sleep
import plotly.graph_objects as go
import plotly.express as px
from config import *
from contracts_names import ContractDb
from Gecko_API import Gecko
import logging
configure_logging()


class Analysis:
    def __init__(self, address, number_of_dest, start_date, end_date, if_cont_names,
                 outlier_value_threshold, outlier_volume_threshold, exclude_outlying, if_exclude_phishing,
                 if_all_contracts, use_real_prices, if_int, if_gpt,
                 if_gas_tick, if_time_needed, chosen_top):
        # ANALYSIS SETTINGS
        self.address = address.lower()
        self.address_nametag = self.address
        self.if_int = if_int
        self.if_gpt = if_gpt
        self.if_gas = if_gas_tick
        self.if_time = if_time_needed
        self.if_all_contracts = if_all_contracts
        self.if_contracts_names = if_cont_names
        self.if_exclude_phishing = if_exclude_phishing
        self.if_use_real_prices = use_real_prices
        self.start_date = start_date
        self.end_date = end_date
        self.chosen_top = chosen_top
        self.number_of_dest = number_of_dest
        self.outlier_value_threshold = outlier_value_threshold if exclude_outlying else None
        self.outlier_volume_threshold = outlier_volume_threshold if exclude_outlying else None
        # CONFIG SETTINGS
        self.etherscan_api_key = conf_etherscan_api_key
        self.not_found_message = conf_not_found_message
        self.untagged_contracts_name = conf_untagged_contracts_name
        self.etherscan_sleep_time = conf_etherscan_sleep_time
        self.etherscan_save_frequency = conf_etherscan_save_frequency
        self.stabl_coins = conf_stabl_coins
        self.stable_coins_price = conf_stable_coins_price
        self.prices_save_frequency = conf_prices_save_frequency
        self.gecko_error_sleep_time = conf_gecko_error_sleep_time
        # INITIALIZING EMPTY GRAPHS AND DATAFRAMES
        self.phishing = pd.DataFrame()
        self.no_transactions = pd.DataFrame()
        self.empty_plot = go.Figure().add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="No Data Available",
                                                     showarrow=False, font=dict(size=20, color="gray")).update_layout(
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False), plot_bgcolor='white')
        # PARSING ENGINES INITIALIZATION
        with st.spinner('Loading parsing engines...'):
            self.name_tags_engine = ContractDb(bar=True, untagged_name=self.untagged_contracts_name,
                                               sleep_time=self.etherscan_sleep_time,
                                               threshold_to_save=self.etherscan_save_frequency)
            self.price_engine = Gecko(save_frequency=self.prices_save_frequency,
                                      sleep_time=self.gecko_error_sleep_time)
        # GETTING TRANSACTIONS FROM ETHERSCAN
        with st.spinner('Getting stuff from Etherscan'):
            self.raw_df = self.get_etherscan()
            self.internal_df = self.get_etherscan_df_internal() if self.if_int else self.no_transactions
            self.normal_df = self.get_etherscan(which='normal')
        # ADJUSTING THE DATASET (TIME, VALUES, etc.)
        with st.spinner('Making stuff look decent...'):
            self.adjusted = self.adjusting()
        if len(self.adjusted) != 0:  # IF THE ADDRESS'S GOT TRANSACTIONS TO ANALYZE:
            with st.spinner('Filtering out some shit...'):
                self.top_contracts = self.filtering_destinations(self.adjusted)  # FILTERING DESTINATIONS
                self.necessary_cols = self.top_contracts[['timeStamp', 'from', 'contractAddress', 'to', 'value',
                                                          'tokenName', 'tokenSymbol', 'gasPrice', 'gasUsed']]
                # CALCULATING METRICS
                self.over_tokens = len(self.adjusted['tokenSymbol'].copy().value_counts())
                self.overall_contracts = len(self.adjusted['contractAddress'].copy().value_counts())
                self.overall_destinations = len(np.unique(self.adjusted[['to', 'from']].values))
                self.analyzed_destinations = len(np.unique(self.top_contracts[['to', 'from']].values))
            # ADDING NAME TAGS FROM ETHERSCAN (IF OPTED FOR)
            with st.spinner('Stealing name tags from Etherscan...'):
                self.top_w_names = self.finding_contract_names(self.necessary_cols) if self.if_contracts_names \
                    else self.necessary_cols
            # ADDING TOKEN PRICES FROM CoinGecko
            with st.spinner('Borrowing ticker prices from CoinGecko...'):
                self.top_w_prices, self.no_price, self.shit_coins = self.finding_prices(self.top_w_names)
            # FILTERING OUTLIERS AND SCAM
            with st.spinner('Almost done...'):
                self.without_outliers_tier1, self.scam_coins = self.filtering_outliers()
                self.without_outliers_tier2, self.outliers_tier2 = self.finding_outliers_tier2()
                self.combined_outliers, self.percentage_of_outliers = self.combining_all_outliers()
            # DEALING WITH GAS AND GPT
            if self.if_gas:
                self.gas_df = self.gas_prep()
            if self.if_gpt:
                self.gpt = self.gpt_conclusions()
        else:  # IF NO TRANSACTIONS TO ANALYZE = SHOWING EMPTY RESULTS
            self.top_contracts = self.overall_contracts = self.necessary_cols = self.top_w_names = \
                self.top_w_prices = self.no_price = self.shit_coins = self.without_outliers_tier1 = self.scam_coins = \
                self.without_outliers_tier2 = self.outliers_tier2 = self.combined_outliers = self.gas_df =\
                self.no_transactions
            self.over_tokens = self.overall_contracts = self.percentage_of_outliers = 0
            self.gpt = 'Nothing to say: no transactions.'
            self.gas_df = self.no_transactions

    def get_etherscan(self, which='erc20'):
        def etherscan_api(start_block=1):
            which_trans = "tokentx" if which == "erc20" else "txlistinternal" if which == "internal" else "txlist"
            headers = {'Accept': 'application/json'}
            link = f'https://api.etherscan.io/api?module=account&action={which_trans}&address=' \
                   f'{self.address}&startblock={start_block}&endblock=98299157&apikey=' \
                   f'{self.etherscan_api_key}'
            logging.debug(f'Obtaining {which} {link}')
            etherscan = requests.get(link, headers=headers)
            logging.debug(f'Obtained {which}')
            if len(etherscan.json()['result']) == 0:
                return None
            return pd.DataFrame(etherscan.json()['result'])
        sleep(3)
        data = etherscan_api()
        logging.debug(f'Length of {which} : {len(data) if data is not None else ""}')
        if data is None:
            logging.debug(f'The data of {which} IS NONE')
            return self.no_transactions
        else:
            if len(data) != 10000:
                logging.debug(f'The length of {which} IS NOT 10000 - returning')
                return data
            else:
                logging.debug(f'The length of {which} IS 10000 - sending to interate over')
                while True:
                    sleep(3)
                    logging.debug(f'{which}: iteration')
                    last_block = data.tail(1)['blockNumber'].values[0]
                    data = data[data['blockNumber'] != last_block]
                    new_data = etherscan_api(start_block=last_block)
                    if last_block == new_data.tail(1)['blockNumber'].values[0]:
                        return data
                    data = pd.concat([data, new_data])
                    if len(new_data) < 10000:
                        return data

    def get_etherscan_df_internal(self):
        res = self.get_etherscan(which='internal')
        if len(res) != 0:
            res['value'] = res.apply(lambda row: int(row['value']) / 10 ** 18, axis=1)
            res['timeStamp'] = pd.to_datetime(res['timeStamp'].astype(int), unit='s')
            res = res[(res['timeStamp'].dt.date >= self.start_date) & (res['timeStamp'].dt.date <= self.end_date)]
            res['tokenSymbol'] = "ETH"
            with_price = self.finding_prices(res, which='internal')[0]
            if self.if_contracts_names:  # ADDING TAGS
                with_price = self.finding_contract_names(with_price)
            with_price = with_price.loc[:, ~with_price.columns.isin(['contractAddress', 'input',  # EXCLUDING COLUMNS
                                                                     'type', 'gasUsed', 'traceId',
                                                                     'isError', 'errCode', 'tokenSymbol', 'hash'])]
            with_price = self.filtering_destinations(with_price)  # FILTERING
            logging.debug('the internal df was obtained!')
            return with_price.sort_values(by='timeStamp', ascending=False).reset_index(drop=True)
        else:
            return self.no_transactions

    def filtering_destinations(self, df):
        logging.debug(f'Length of the DF to filter: {len(df)}')
        if not self.if_all_contracts:
            from_list_top = df.copy()['from'].value_counts().reset_index()['from'][:self.number_of_dest]
            to_list_top = df.copy()['to'].value_counts().reset_index()['to'][:self.number_of_dest]
            res = df[(df['from'].isin(from_list_top)) & (df['to'].isin(to_list_top))].copy().reset_index(drop=True)
            logging.debug(f'Finished filtering. Rows left: {len(res)}')
            return res
        else:
            logging.debug('No need to filter. Continuing.')
            return df

    def adjusting(self):
        adjusted = self.raw_df.copy()
        normal = self.normal_df  # ADDING NORMAL TRANS
        if len(adjusted) != 0:
            adjusted['tokenDecimal'] = adjusted['tokenDecimal'].astype(int)  # Solves that console bytes error
        if len(normal) != 0:
            normal['contractAddress'], normal['tokenName'], normal['tokenSymbol'], normal['tokenDecimal'] =\
                'ETH', 'ETH', 'ETH', 18
            normal = normal[['blockNumber', 'timeStamp', 'hash', 'nonce', 'blockHash', 'from', 'contractAddress', 'to',
                             'value', 'tokenName', 'tokenSymbol', 'tokenDecimal', 'transactionIndex', 'gas', 'gasPrice',
                             'gasUsed', 'cumulativeGasUsed', 'input', 'confirmations']]
        if len(adjusted) != 0 or len(normal) != 0:
            adjusted = pd.concat([adjusted, normal]).sort_values(by='timeStamp')
            adjusted['value'] = adjusted.apply(lambda row: int(row['value']) / 10 ** int(row['tokenDecimal']), axis=1)
            adjusted['timeStamp'] = pd.to_datetime(adjusted['timeStamp'].astype(int), unit='s')
            adjusted = adjusted[(adjusted['timeStamp'].dt.date >= self.start_date) &
                                (adjusted['timeStamp'].dt.date <= self.end_date)]
            logging.debug(f'the df was adjusted!')
            return adjusted
        else:
            logging.debug('The df is empty!')
            return self.no_transactions

    # @st.cache_data  # for development and testing
    def finding_contract_names(_self, df):
        def get_contract_name(address, exl_self=True):
            if exl_self:
                if address.lower() == _self.address.lower():
                    return _self.address
            if address in res_dict.keys():
                res = res_dict[address]
                if res == _self.untagged_contracts_name:
                    return address
                else:
                    return res
            else:
                return address
        addresses_unique = np.unique(df[['from', 'contractAddress', 'to']].values)
        logging.debug(f"Length of unique addresses: {len(addresses_unique)}")
        res_dict = _self.name_tags_engine.get_name(list(addresses_unique))
        _self.address_nametag = get_contract_name(_self.address, exl_self=False)  # ADDING THE TAG TO SELF IF EXISTS
        temp_df = df.copy()
        temp_df['from'] = temp_df['from'].apply(lambda x: get_contract_name(x))
        temp_df['contractAddress'] = temp_df['contractAddress'].apply(lambda x: get_contract_name(x))
        temp_df['to'] = temp_df['to'].apply(lambda x: get_contract_name(x))
        if _self.if_exclude_phishing:
            condition = (temp_df['from'].str.contains('Phishing', case=False)) | \
                        (temp_df['contractAddress'].str.contains('Phishing', case=False)) | \
                        (temp_df['to'].str.contains('Phishing', case=False))
            _self.phishing = temp_df[condition].copy()
            temp_df = temp_df[~condition]
        return temp_df

    # @st.cache_data  # for development and testing
    def finding_prices(_self, df, which='erc-20', gas=False):
        def get_prices(date, token):
            if token.lower() in _self.stabl_coins:
                return 1.00
            else:
                return gecko_prices.query('timeStamp == @date & tokenSymbol == @token'). \
                    copy().reset_index()['hist_price'][0]
        type_ = "ERC-20 tokens'" if which == 'erc-20' else "internal transactions'"  # Initializing the bar
        stqdm.pandas(desc=f"Parsing {type_} prices from CoinGecko")  # Initializing the bar
        gecko_prices = df[['timeStamp', 'tokenSymbol']].copy()
        gecko_prices['timeStamp'] = gecko_prices['timeStamp'].dt.strftime('%d-%m-%Y')
        gecko_prices = gecko_prices.drop_duplicates(ignore_index=True)
        attempts = 10
        init = 0
        while True:
            try:
                if _self.if_use_real_prices:
                    gecko_prices['hist_price'] = gecko_prices.progress_apply(
                        lambda row: _self.price_engine.get_price(row['tokenSymbol'], row['timeStamp']) if
                        row['tokenSymbol'].lower() not
                        in _self.stabl_coins else
                        _self.stable_coins_price, axis=1)
                else:
                    gecko_prices['hist_price'] = gecko_prices.progress_apply(lambda row:
                                                                             _self.price_engine.
                                                                             get_price(row['tokenSymbol'],
                                                                                       date.today()
                                                                                       .strftime('%d-%m-%Y')) if
                                                                             row['tokenSymbol'].lower()
                                                                             not in _self.stabl_coins else
                                                                             _self.stable_coins_price, axis=1)
            except Exception as e:
                logging.debug(f"Gecko Error *****************************************************: {e}")
                if attempts == init:
                    break
                else:
                    init += 1
            else:
                logging.debug("Success!")
                break
        try:
            gecko_prices['timeStamp'] = pd.to_datetime(gecko_prices['timeStamp'], format="%d-%m-%Y")
        except KeyError:
            raise KeyError("There was an error on CoinGecko servers. "
                           "Please launch it again, the progress WON'T be lost.")
        temp_df = df.copy()
        if len(temp_df) != 0:
            temp_df['token_price'] = temp_df.apply(lambda row: get_prices(row['timeStamp'].strftime('%Y-%m-%d'),
                                                                          row['tokenSymbol']), axis=1).copy()
            shit_coins = temp_df.query('token_price == "NO_SUCH_COIN*"').copy()
            no_price = temp_df.query('token_price == "NO_PRICE_FOUND*"').copy()
            with_price = temp_df.query('token_price != "NO_PRICE_FOUND*" & token_price != "NO_SUCH_COIN*"').copy()
            if not gas:  # adding transaction volume
                with_price['token_price'] = with_price['token_price'].astype(float)
                with_price['trans_value_US'] = with_price['value'] * with_price['token_price']

        else:
            with_price, no_price, shit_coins = temp_df, temp_df, temp_df
        return with_price, no_price, shit_coins

    def filtering_outliers(self):
        logging.debug(f'Entered the tier 1 of filtering: {len(self.top_w_prices)}')
        if len(self.top_w_prices) != 0 and self.outlier_value_threshold is not None:
            logging.debug(f'Started the tier 1 filtering.')
            scam = self.top_w_prices['value'].describe()['75%'] + (self.top_w_prices['value'].describe()['75%'] *
                                                                   self.outlier_value_threshold)
            if scam > 1000:  # HELPS IF AN ADDRESS HAS TOO MANY 0 OR LOW VALUE TRANSACTIONS
                scam_coins = self.top_w_prices.query('value > @scam').copy()
                clean = self.top_w_prices.query('value < @scam').copy()
            else:
                clean, scam_coins = self.top_w_prices, self.no_transactions
        else:
            clean, scam_coins = self.top_w_prices, self.no_transactions
        return clean, scam_coins

    def finding_outliers_tier2(self):
        logging.debug(f'Entered the tier 2 of filtering: {len(self.without_outliers_tier1)}')
        if len(self.without_outliers_tier1) != 0 and self.outlier_volume_threshold is not None:
            mean_val = self.without_outliers_tier1['trans_value_US'].mean()
            slash = mean_val + (mean_val * self.outlier_volume_threshold)
            outliers = self.without_outliers_tier1[self.without_outliers_tier1['trans_value_US'] > slash].copy()
            clean = self.without_outliers_tier1[~(self.without_outliers_tier1['trans_value_US'] > slash)]
        else:
            clean, outliers = self.without_outliers_tier1, self.no_transactions
        return clean.sort_values(by='timeStamp', ascending=False).reset_index(drop=True), outliers

    def combining_all_outliers(self):
        self.no_price['token_price'] = self.no_price['token_price'].astype(str)
        self.shit_coins['token_price'] = self.shit_coins['token_price'].astype(str)
        combined_outliers = pd.concat([self.no_price, self.shit_coins, self.scam_coins,
                                       self.outliers_tier2, self.phishing]).reset_index(drop=True)
        percentage_of_outliers = str(round((len(combined_outliers) / len(self.top_contracts)) * 100, 1)) + " %"

        return combined_outliers, percentage_of_outliers

    def check_if_self(self, addr):
        return True if self.address[:8].lower() == addr[:8].lower() \
                       and self.address[-8:].lower() == addr[-8:].lower() else False

    def gas_prep(self):
        logging.debug('Started GAS calculation')
        data = self.without_outliers_tier2[self.without_outliers_tier2['from']
                                           .apply(lambda x: self.check_if_self(x))].copy()
        if len(data) != 0:
            data = data.reset_index(drop=True)[['timeStamp', 'contractAddress', 'to', 'tokenSymbol', 'gasUsed',
                                                'gasPrice', 'trans_value_US']]
            data = data.drop_duplicates('timeStamp')  # removing duplicates
            data['gasPrice_ETH'] = data['gasPrice'].astype(np.int64) / 10 ** 18
            data['txnCost_ETH'] = data['gasUsed'].astype(int) * data['gasPrice_ETH']

            data = data.rename(columns={'tokenSymbol': 'tokenSymbol_'})
            data['tokenSymbol'] = "ETH"
            data = self.finding_prices(data, gas=True)[0]  # the other 2 aren't used
            data['txnCost_US'] = data['txnCost_ETH'] * data['token_price'].astype(float)
            return data
        else:
            return self.no_transactions

    def gas_consideration(self, choice=10, by='tokens', gpt=False):
        if len(self.gas_df) != 0:
            by_tokens = True if by == 'tokens' else False
            data = self.gas_df.groupby('tokenSymbol_' if by_tokens else 'contractAddress')['txnCost_US'].\
                sum().reset_index()
            data = data.sort_values(by='txnCost_US').reset_index(drop=True)
            first_10 = data[-choice:]
            others = data[:-choice]['txnCost_US'].sum()
            temp_df = pd.DataFrame({'tokenSymbol_' if by_tokens else 'contractAddress': ['Other'],
                                    'txnCost_US': [others]})
            data = pd.concat([temp_df, first_10]).reset_index(drop=True)
            data['percentage'] = round(data['txnCost_US'], 2).astype(str) + "$ / " + round((data['txnCost_US']
                                                                                           / data['txnCost_US'].sum()) *
                                                                                           100, 1).astype(str) + " %"
            if gpt:
                return data
            fig = go.Figure(go.Bar(x=data['txnCost_US'], y=data['tokenSymbol_' if by_tokens else 'contractAddress'],
                                   orientation='h', text=data['percentage']))
            fig.update_layout(xaxis_title='USD spent on transactions',
                              xaxis_title_font_size=20,
                              yaxis_title='Tokens' if by_tokens else 'Contracts', yaxis_title_font_size=20,
                              xaxis=dict(showgrid=True),
                              title=f'Gas expenses by {"Tokens" if by_tokens else "Contracts"}',
                              title_font_size=17)

            return fig
        else:
            return self.empty_plot if not gpt else self.no_transactions

    def gpt_conclusions(self):
        introduction = f' ---- RE-RUNNING the script may help to improve it ---- \n\n'
        warning = f'\n\n ---- The info above MAY NOT be entirely accurate. ----'
        from gpt import GptConclusions
        gpt = GptConclusions(start_date=self.start_date, end_date=self.end_date,
                             top_10_tokens_trans=self.top_10_tokens_plotting(self.chosen_top, by='number', gpt=True),
                             top_10_tokens_vol=self.top_10_tokens_plotting(self.chosen_top, by='volume', gpt=True),
                             top_10_dest_to_quantity=self.top_destinations(self.chosen_top, by='quantity',
                                                                           from_or_to='to'),
                             top_10_dest_to_vol=self.top_destinations(self.chosen_top, by='volume', from_or_to='to'),
                             top_10_dest_from_quantity=self.top_destinations(self.chosen_top, by='quantity',
                                                                             from_or_to='from'),
                             top_10_dest_from_vol=self.top_destinations(self.chosen_top, by='volume',
                                                                        from_or_to='from'),
                             top_10_internal_trans_dest_quantity=self.plotting_internal_destinations(by='quantity',
                                                                                                     choice=self.
                                                                                                     chosen_top,
                                                                                                     gpt=True)
                             if self.if_int else None,
                             top_10_internal_trans_dest_vol=self.plotting_internal_destinations(by='volume',
                                                                                                choice=self.chosen_top,
                                                                                                gpt=True)
                             if self.if_int else None,
                             time_data=self.time_consideration(gpt=True) if self.if_time else None,
                             time_data_days=self.time_consideration_days(gpt=True) if self.if_time else None,
                             gas_data_tokens=self.gas_consideration(by='tokens', gpt=True) if self.if_gas else None,
                             gas_data_contracts=self.gas_consideration(by='contracts', gpt=True)
                             if self.if_gas else None,
                             overall_destinations=self.overall_destinations)
        with st.spinner('GPT is thinking...'):
            gpt_resp = gpt.ask_gpt()
        return introduction + gpt_resp + warning

    # PLOTTING
    def top_destinations(self, choice, by, from_or_to):
        if len(self.without_outliers_tier2) != 0:
            needed_column = 'from' if from_or_to == 'from' else 'to'
            excluding_the_address = self.without_outliers_tier2[self.without_outliers_tier2[needed_column].
                                                                apply(lambda x: not self.check_if_self(x))]
            if by == 'quantity':
                data_raw = excluding_the_address[needed_column].copy().value_counts().reset_index().sort_values(
                    by='count', ascending=False)
            else:
                data_raw = excluding_the_address.groupby(needed_column)['trans_value_US'].sum().reset_index(). \
                    sort_values(by='trans_value_US', ascending=False).reset_index(drop=True)
                data_raw['trans_value_US'] = round(data_raw['trans_value_US'], 2)
            first_10 = data_raw[:choice]
            others = data_raw[choice:]['count' if by == 'quantity' else 'trans_value_US'].sum()
            temp_df = pd.DataFrame({needed_column: ['Other'],
                                    'count' if by == 'quantity' else 'trans_value_US': [others]})
            data = pd.concat([first_10, temp_df]).reset_index(drop=True)
            if by == 'quantity':
                data['percentage'] = round((data['count'] / data['count'].sum()) * 100, 1).astype(str) + " %"
                return data
            else:
                data['percentage'] = round((data['trans_value_US'] / data['trans_value_US'].sum()) * 100, 1).astype(
                    str) + " %"
                return data
        else:
            return self.no_transactions

    def plotting_trans(self, by):
        by_dest = True if by == 'Destinations' else False
        if len(self.without_outliers_tier2) != 0:
            plotly_df = self.without_outliers_tier2.copy()
            plotly_df['timeStamp'] = plotly_df['timeStamp'].dt.strftime('%Y-%m-%d')
            plotly_df['trans_value_US'] = plotly_df.apply(lambda row: row['trans_value_US']
                                                          if self.check_if_self(row['to']) else
                                                          row['trans_value_US'] * (-1), axis=1)
            if by_dest:
                plotly_df['Destination'] = plotly_df.apply(lambda row: row['to'] if row['trans_value_US'] <= 0
                                                           else row['from'], axis=1)
            fig = go.Figure()
            destinations = np.unique(plotly_df['Destination' if by_dest else 'tokenName'])
            for each in destinations:
                fig.add_trace(
                    go.Bar(x=plotly_df.query('Destination == @each' if by_dest else 'tokenName == @each')['timeStamp'],
                           y=plotly_df.query('Destination == @each' if by_dest else 'tokenName == @each')[
                               'trans_value_US'],
                           name=each))
            fig.update_layout(barmode='relative', legend_title_text='Destinations' if by_dest else 'Tokens',
                              legend_title_font_size=15, height=500,
                              xaxis_title='Date', xaxis_title_font_size=20,
                              yaxis_title='Transactions in USD', yaxis_title_font_size=20,
                              title=f'ERC-20 + ETH Transactions chart (by {"Destination" if by_dest else "Tokens"})',
                              title_font_size=17)
            return fig
        else:
            return self.empty_plot

    def top_10_tokens_plotting(self, choice, by, gpt=False):
        by_volume = True if by == 'volume' else False
        if len(self.without_outliers_tier2) != 0:
            data_raw = self.without_outliers_tier2.groupby('tokenSymbol')['trans_value_US'].sum().reset_index(). \
                sort_values(by='trans_value_US').reset_index(drop=True) if by_volume \
                else self.without_outliers_tier2['tokenSymbol'].copy().value_counts().reset_index() \
                .sort_values(by='count')
            first_10 = data_raw[-choice:]
            others = data_raw[:-choice]['trans_value_US' if by_volume else 'count'].sum()
            temp_df = pd.DataFrame({'tokenSymbol': ['Other'],
                                    'trans_value_US' if by_volume else 'count': [others]})
            data = pd.concat([temp_df, first_10]).reset_index(drop=True)
            if by_volume:
                data['percentage'] = round((data['trans_value_US'] / data['trans_value_US'].sum()) * 100, 1).astype(
                    str) + " %"
            else:
                data['count_percentage'] = data['count'].astype(str) + " / " + round(
                    (data['count'] / data['count'].sum()) * 100, 1).astype(str) + " %"
            if gpt:
                return data
            fig = go.Figure(go.Bar(x=data['trans_value_US' if by_volume else 'count'],
                                   y=data['tokenSymbol'], orientation='h',
                                   text=data['percentage' if by_volume else 'count_percentage']))
            fig.update_layout(xaxis_title='Transaction Volume in USD' if by_volume else 'Number of Transactions',
                              xaxis_title_font_size=20,
                              yaxis_title='Token', yaxis_title_font_size=20, xaxis=dict(showgrid=True),
                              title=f'TOP {choice} Tokens by'
                                    f' {"Volume of Transactions" if by_volume else "Quantity of Transactions"}',
                              title_font_size=17)
            return fig
        else:
            return self.empty_plot if not gpt else self.no_transactions

    def plotting_internal_destinations(self, by, choice, gpt=False):
        if len(self.internal_df) != 0:
            df = self.internal_df.copy()
            needed_column = 'count' if by == 'quantity' else 'trans_value_US'
            data_raw = df['from'].value_counts().sort_values().reset_index() if by == 'quantity' else \
                df.groupby('from')['trans_value_US'].sum().sort_values().reset_index()
            others = data_raw[:-choice][needed_column].sum()
            data = pd.concat([pd.DataFrame({'from': 'others',
                                            needed_column: [others]}), data_raw[-choice:]]).reset_index(drop=True)
            data['percentage'] = (data['count'].astype(str) + ' / ' if by == 'quantity' else "") + \
                round((data[needed_column] / data[needed_column].sum()) * 100, 1).astype(str) + " %"
            if gpt:
                return data
            fig = go.Figure(go.Bar(x=data[needed_column], y=data['from'], orientation='h', text=data['percentage']))
            fig.update_layout(xaxis_title='Number of Transactions' if by == 'quantity' else 'Volume of Transactions ',
                              xaxis_title_font_size=20, yaxis_title='Contract name',
                              yaxis_title_font_size=20, xaxis=dict(showgrid=True),
                              title=f'TOP {choice} Contracts by Number of Transactions' if by == 'quantity' else
                              f'TOP {choice} Contracts by Volume of Transactions', title_font_size=17)
            return fig
        else:
            if gpt:
                return self.no_transactions
            else:
                return self.empty_plot

    def plotting_internal_flows(self):
        if len(self.internal_df) != 0:
            df = self.internal_df.copy()
            df['timeStamp'] = df['timeStamp'].dt.date
            destinations = np.unique(df['from'])
            fig = go.Figure()
            for each in destinations:
                fig.add_trace(go.Bar(x=df[df['from'] == each]['timeStamp'],
                                     y=df[df['from'] == each]['trans_value_US'], name=each))
            fig.update_layout(barmode='relative', legend_title_text='From', legend_title_font_size=15,
                              height=500, xaxis_title='Date', xaxis_title_font_size=20,
                              yaxis_title='Transactions in USD', yaxis_title_font_size=20,
                              title=f'Internal Transactions chart', title_font_size=17)
            return fig
        else:
            return self.empty_plot

    def time_consideration(self, gpt=False):
        if len(self.adjusted) != 0:
            data = self.adjusted.reset_index(drop=True)[['blockNumber', 'timeStamp', 'from', 'contractAddress', 'to',
                                                         'value', 'tokenName']]
            data = data[data['from'].apply(lambda x: self.check_if_self(x))]
            data = data.drop_duplicates('timeStamp')  # removing duplicates
            data['hour'] = data['timeStamp'].dt.hour
            data['month_year'] = data['timeStamp'].dt.strftime('%B-%Y')
            data = data[['month_year', 'hour']]
            average = data.groupby('month_year')['hour'].mean().reset_index() \
                .rename(columns={'hour': 'average'})
            percentile_50 = data.groupby('month_year')['hour'].quantile(0.50).reset_index() \
                .rename(columns={'hour': 'median'})
            data = pd.merge(data, average, on='month_year', how='left')
            data = pd.merge(data, percentile_50, on='month_year', how='left')
            if gpt:
                data = data[['month_year', 'average', 'median']].drop_duplicates()
                return data
            fig = px.scatter(data, x='month_year', y='hour')
            fig.add_trace(go.Scatter(x=data['month_year'], y=data['average'], mode='lines', name='Mean',
                                     line=dict(color='red')))
            fig.add_trace(go.Scatter(x=data['month_year'], y=data['median'], mode='lines', name='Median',
                                     line=dict(color='blue')))
            fig.update_layout(xaxis_title='Months', xaxis_title_font_size=20, yaxis_title='Time of transactions (UTC)',
                              yaxis_title_font_size=20, xaxis=dict(showgrid=True),
                              title=f'Distribution of transactions time', title_font_size=17)
            return fig
        else:
            return self.empty_plot

    def time_consideration_days(self, gpt=False):
        if len(self.adjusted) != 0:
            data = self.adjusted.reset_index(drop=True)[['timeStamp']].copy()
            data = data.drop_duplicates('timeStamp')  # removing duplicates
            data['weekday'] = data['timeStamp'].dt.day_name()
            data['hour'] = data['timeStamp'].dt.hour
            count = data.copy()['weekday'].value_counts()
            cats = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            data = data.groupby('weekday')['hour'].mean().round(1).reindex(cats).reset_index()
            data = data.merge(count, how='inner', on='weekday').rename(columns={'count': 'Transactions',
                                                                                'hour': 'average_hour'})
            data['percentage'] = round((data['Transactions'] / data['Transactions'].sum()) * 100, 1).astype(str) + " %"
            if gpt:
                return data
            fig = go.Figure()
            fig.add_trace(go.Bar(x=data['weekday'], y=data['Transactions'], name='Transactions', yaxis='y',
                                 text=data['percentage']))
            fig.add_trace(go.Scatter(x=data['weekday'], y=data['average_hour'], name='Mean Time', yaxis='y2',
                                     text=data['average_hour'], textposition='top center', mode="lines+markers+text",
                                     textfont=dict(size=14, color="red")))
            fig.update_layout(xaxis_title='Days of the Week', xaxis_title_font_size=16,
                              yaxis=dict(title='Number of Transactions', titlefont_size=16, tickfont_size=14,
                                         showgrid=False), yaxis2=dict(title='Average Tnx Hour (UTC)',
                                                                      titlefont_size=16, tickfont_size=14,
                                                                      overlaying='y', side='right', showgrid=False),
                              title=f'Transactions by Days of the Week', title_font_size=17)
            return fig
        else:
            return self.empty_plot

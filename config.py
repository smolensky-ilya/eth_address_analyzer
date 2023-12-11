from datetime import date
import logging
import streamlit as st
from stqdm import stqdm
from threading import RLock

stqdm.set_lock(RLock())


def configure_logging():
    """
    Configure the logging for the app.
    - Set the root logger to ERROR level to capture only error messages and above.
    - Set all other loggers to ERROR level to minimize noise from third-party libraries.
    """
    # Configure the basic settings for the root logger
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
    # Explicitly set the root logger level (use INFO for general use, DEBUG for detailed logging)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Adjust this as needed (INFO or DEBUG)
    # Set all other loggers to ERROR level
    for logger_name, logger_obj in logging.root.manager.loggerDict.items():
        if isinstance(logger_obj, logging.Logger):  # Check if it's an actual Logger instance
            logger_obj.setLevel(logging.ERROR)


# CSS
css = r'''
    <style>
        [data-testid="stForm"] {
            border: 0px;
            width: 105%;
        }
    </style>
'''

# MAIN PAGE VALUES
def_val = dict(address_given=None,
               if_include_all_dest=False,
               if_use_real_prices=False,
               num_of_dest=100,
               chosen_top=10,
               chosen_start_date=date(year=2023, month=1, day=1),
               chosen_end_date=date.today(),
               if_internal=True,
               if_time=True,
               if_contracts_names=True,
               if_excl_phishing=True,
               if_excl_outliers=True,
               volume_threshold=100,
               value_threshold=[400, 4000],
               if_gpt_conclusions=True,
               if_gas=True
               )
# ANALYSIS SETTINGS
conf_etherscan_api_key = st.secrets['etherscan_api_key']
conf_not_found_message = "Address wasn't found :("
conf_untagged_contracts_name = 'Untagged*'
conf_etherscan_sleep_time = 3
conf_etherscan_save_frequency = 1  #TEMPORARY
conf_stabl_coins = ['usdt', 'usdc', 'dai', 'mim']
conf_stable_coins_price = 1.00
conf_prices_save_frequency = 1  # TEMPORARY
conf_gecko_error_sleep_time = 30  # OPTIMAL
conf_day_shift_hours = 6  # Hours after the beginning of the day when parsing today's price is okay
conf_gecko_coin_exceptions = {'ETH': 'staked-ether'}  # if there are more labels ETH on Gecko, pointing at the right one
# NOTICES
addr_notice = 'Insert a valid ETH address to perform the analysis.'
all_dest_notice = 'ILL-ADVISED if analyzing an address with a vast number of unique destinations. IF OUTED OUT, ' \
                  'only the N most frequent ones chosen above are taken into the analysis.'
real_prices_notice = 'EXTREMELY TIME-CONSUMING. What it does is parce the price of each token on the transaction day ' \
                     'from CoinGecko API. OTHERWISE, the transaction volumes are calculated based on token prices' \
                     ' as of today.'
gpt_conclusions_notice = 'THERE MAY NOT BE ACCURATE. If opted for, a GPT model is given the analyzed data and asked ' \
                         'to make conclusions.'
num_of_dest_notice = 'This limits the analysis to only top N most frequent destinations by the number of ' \
                     'transactions. If the address has interacted with fewer than N, all interacted contracts are' \
                     ' included. Useful when analysing addresses with a large number of diverse operations.'
chosen_top_notice = "How many tokens/contracts/etc. are shown in graphs. Other ones are included in 'Other'."
start_date_notice = 'Transactions of the address beginning on the chosen date are included in the analysis.'
end_date_notice = 'The last date of transactions to analyse.'
trans_time_notice = 'If ticked, the time of transactions is analysed and shown in graphs.'
tag_names_notice = "TAKES A BIT OF TIME. It parses addresses' tag names from Etherscan. IF OPTED OUT OF, the GPT" \
                   "conclusions don't work properly."
phishing_trans_notice = "Transactions marked as 'PHISHING' on Etherscan are excluded from the analysis. "
outlying_trans_notice = 'Transactions with ridiculously high token value or volume in USD are excluded from' \
                        'the analysis.'
volume_thr_notice = 'The average volume of all transactions included in the analysis is calculated and all' \
                    'transaction volumes that are N-times bigger than the average are excluded from the analysis.'
value_thr_notice = 'Token values that are N-times bigger than than 75% of the entire analysed data are excluded' \
                   'from the analysis.'
gas_analysis_notice = "If ticked, the result will contain information on what tokens and contracts burnt the most ' \
                      'GAS in total IN USD. IT'S RECOMMENDED to tick REAL PRICES above to be able to see the " \
                      "address's REAL GAS EXPENSES."
gas_expenses_warning = "The ETH price is taken AS OF TODAY. If you require the address's REAL GAS EXPENSES, " \
                       "please tick REAL PRICES on the left."
prices_warning = "Please keep in mind that token prices in the entire report (and hence the transaction volumes) " \
                 "are calculated AS OF TODAY. Tick REAL PRICES on the left to see historical data, if need be."
inter_cont_notice = 'The number of unique contacts the address has interacted with over the chosen time period.'
inter_tokens_notice = 'The number of unique tokens the address has interacted with over the chosen time period.'
destinations_notice = 'The destinations included in the analysis (CAN BE ADJUSTED ON THE LEFT) / the total number of ' \
                      'unique destinations the address has interacted with over the chosen period.'
outliers_notice = 'Outliers or Scam transactions either marked as "Phishing" by etherscan or following the parameters' \
                  ' chosen on the left.'
int_trans_question = 'What are :blue[INTERNAL TRANSACTIONS]?'
int_trans_explanation = 'Internal Transactions are unique events that occur as a result of smart contract executions,' \
                        ' rather than direct actions by users. Unlike standard blockchain transactions, they do ' \
                        'not exist independently on the blockchain but are the outcomes of contracts transferring ' \
                        'Ether or tokens internally. This distinction is crucial, as internal transactions, ' \
                        'being a byproduct of smart contract interactions, are not recorded as standard ' \
                        'transactions and thus require specialized tracking and interpretation.'
internal_trans_notice = 'Parse internal transactions of the address from Etherscan and include them in the analysis.'\
    + int_trans_explanation
search_notice = '* Select the dataframe and use CTRL + F to search'
graphs_notice = '* Double-click on items in the legend to filter the graph based on select elements. ' \
                'Double-click on the graph to restore it to the default view.'

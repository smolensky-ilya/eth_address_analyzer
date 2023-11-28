from time import sleep
import g4f
import logging
from config import configure_logging
configure_logging()


class GptConclusions:
    def __init__(self, start_date, end_date, top_10_tokens_trans,
                 top_10_tokens_vol, top_10_dest_to_quantity, top_10_dest_to_vol, top_10_dest_from_quantity,
                 top_10_dest_from_vol, top_10_internal_trans_dest_quantity, top_10_internal_trans_dest_vol, time_data,
                 time_data_days, gas_data_tokens, gas_data_contracts, overall_destinations):
        self.safe_slicing = 15
        self.error_message = 'The GPT model is currently unavailable, our apologies for that :('
        self.prompt_init = f"Can you write several conclusion paragraphs on the strategy of this ETH " \
                           f"address based on the " \
                           f"following data gathered from {start_date} until {end_date}:\n" \
                           f"The total number of unique destinations FROM and TO the address:\n" \
                           f"{overall_destinations}\n" \
                           f"Top interacted tokens by the number of transactions:\n" \
                           f"{top_10_tokens_trans.to_string()},\n" \
                           f"Top interacted tokens by the volume of transactions in USD:\n" \
                           f"{top_10_tokens_vol[:self.safe_slicing].to_string()},\n" \
                           f"Top destinations that tokens were sent to by quantity:\n" \
                           f"{top_10_dest_to_quantity[:self.safe_slicing].to_string()},\n" \
                           f"Top destinations that tokens were sent to by volume in USD:\n" \
                           f"{top_10_dest_to_vol[:self.safe_slicing].to_string()},\n" \
                           f"Top destinations that tokens were sent from by quantity:\n" \
                           f"{top_10_dest_from_quantity[:self.safe_slicing].to_string()},\n" \
                           f"Top destinations that tokens were sent from by volume in USD:\n" \
                           f"{top_10_dest_from_vol[:self.safe_slicing].to_string()},\n"
        self.prompt_if_internal = f"Top internal transactions destinations by quantity:\n" \
                                  f"{top_10_internal_trans_dest_quantity[:self.safe_slicing].to_string()},\n" \
                                  f"Top internal transactions destinations by volume in USD:\n" \
                                  f"{top_10_internal_trans_dest_vol[:self.safe_slicing].to_string()},\n" if \
            top_10_internal_trans_dest_quantity is not None else ""
        self.prompt_if_gas = f"The amount of GAS paid for transactions with particular tokens in USD and %:\n" \
                             f"{gas_data_tokens[:self.safe_slicing].to_string()},\n" \
                             f"The amount of GAS paid for transactions with particular contracts in USD and %:\n" \
                             f"{gas_data_contracts[:self.safe_slicing].to_string()}.\n" if \
            gas_data_contracts is not None else ""
        self.prompt_if_time = f"Also, please assume the possible country the address might be operating from " \
                              f"based on average transactions time and median (50 percentile) by months (UTC time):\n" \
                              f"{time_data[:self.safe_slicing].to_string()}.\n Based on this information, please" \
                              f" assume a continent (or several possible countries) the address owner likely " \
                              f"operates from.\n Also, here is the information on transactions by days of the week:\n" \
                              f"{time_data_days[:self.safe_slicing].to_string()} \nAre there any valuable insights?" if\
            time_data is not None else ""
        self.prompt_comb = self.prompt_init + self.prompt_if_internal + self.prompt_if_gas + self.prompt_if_time
        logging.debug(self.prompt_comb)

    def ask_gpt(self):
        try:
            attempts = 5  # temporary measure = this will be changed once a reliable model is found.
            current_attempt = 0
            while attempts != current_attempt:
                response = g4f.ChatCompletion.create(
                    model="llama2-7b", messages=[{"role": "user", "content": f"{self.prompt_comb}"}])
                if len(response) != 0:
                    return response
                sleep(3)
                current_attempt += 1
            return self.error_message
        except:
            return self.error_message


def main():
    pass


if __name__ == "__main__":
    main()

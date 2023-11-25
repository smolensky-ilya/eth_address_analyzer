from datetime import datetime
from analysis import Analysis
from config import *
import logging
configure_logging()

st.set_page_config(layout="wide", page_title='ETH analyser | SMK', page_icon="favicon.png",
                   menu_items={'Report a bug': "mailto:ilya@s1q.ru",
                               'About': "Author: Ilya Smolenskiy"})
# LINK PARAMS
params = st.experimental_get_query_params()
run_it_params = params['r'] if 'r' in params else False  # if in the params
# SIDEBAR
address_given = st.sidebar.text_input('Address', value=params['a'][0] if 'a' in params else def_val['address_given'],
                                      help=addr_notice, max_chars=42, )
if_include_all_dest = st.sidebar.checkbox("All destinations", value=params['iac'][0]
                                               if 'iac' in params else def_val['if_include_all_dest'],
                                          help=all_dest_notice)
if_use_real_prices = st.sidebar.checkbox("Real prices", value=params['urp'][0]
                                         if 'urp' in params else def_val['if_use_real_prices'], help=real_prices_notice)
if_gpt_conclusions = st.sidebar.checkbox("GPT conclusions", help=gpt_conclusions_notice,
                                         value=params['gpt'][0] if 'gpt' in params else def_val['if_gpt_conclusions'])
num_of_dest = st.sidebar.number_input('TOP destinations to analyze', help=num_of_dest_notice,
                                      value=int(params['nc'][0]) if 'nc' in params
                                      else def_val['num_of_dest'],
                                      disabled=if_include_all_dest, min_value=1)
chosen_top = st.sidebar.number_input('MAX items shown in graphs and tables', help=chosen_top_notice, min_value=1,
                                     value=int(params['ct'][0]) if 'ct' in params else def_val['chosen_top'])
chosen_start_date = st.sidebar.date_input('Starting date', help=start_date_notice,
                                          value=datetime.strptime(params['sd'][0], "%Y-%m-%d")
                                          if 'sd' in params else def_val['chosen_start_date'])
chosen_end_date = st.sidebar.date_input('Ending date', help=end_date_notice,
                                        value=datetime.strptime(params['ed'][0], "%Y-%m-%d")
                                        if 'ed' in params else def_val['chosen_end_date'], max_value=date.today())
if_internal = st.sidebar.checkbox('Internal transactions', help=internal_trans_notice,
                                  value=params['ii'][0] if 'ii' in params else def_val['if_internal'])
if_gas = st.sidebar.checkbox('Analyze GAS', help=gas_analysis_notice,
                             value=params['ig'][0] if 'ig' in params else def_val['if_gas'])
if_time = st.sidebar.checkbox('Transactions time', help=trans_time_notice,
                              value=params['it'][0] if 'it' in params else def_val['if_time'])
if_contracts_names = st.sidebar.checkbox("Addresses' tag names", help=tag_names_notice,
                                         value=params['icn'][0] if 'icn' in params else def_val['if_contracts_names'])
if_excl_phishing = st.sidebar.checkbox("Exclude phishing transactions", help=phishing_trans_notice,
                                       value=params['iep'][0] if 'iep' in params else def_val['if_excl_phishing'] if
                                       if_contracts_names else False,
                                       disabled=False if if_contracts_names else True)
if_excl_outliers = st.sidebar.checkbox("Exclude outliers", help=outlying_trans_notice,
                                       value=params['eo'][0] if 'eo' in params else def_val['if_excl_outliers'])
volume_threshold = st.sidebar.number_input("Exclude if volume is N-times bigger than mean",
                                           value=int(params['ovot'][0]) if 'ovot' in params else
                                           def_val['volume_threshold'], disabled=False if if_excl_outliers else True,
                                           help=volume_thr_notice, min_value=1)
value_threshold = st.sidebar.number_input("Exclude if value is N-times bigger than Q3", help=value_thr_notice,
                                          value=int(params['ovt'][0]) if 'ovt' in params
                                          else def_val['value_threshold'][0] if if_include_all_dest else
                                          def_val['value_threshold'][1], disabled=False if if_excl_outliers else True,
                                          min_value=1)
run_it = st.sidebar.button('Do the magic')
# MAIN FIELD
if run_it or run_it_params:
    # SET LINK PARAMS
    params = dict(a=address_given if address_given != def_val['address_given'] else None,
                  nc=num_of_dest if num_of_dest != def_val['num_of_dest'] else None,
                  iac=if_include_all_dest if if_include_all_dest != def_val['if_include_all_dest']
                  else None,
                  sd=chosen_start_date if chosen_start_date != def_val['chosen_start_date'] else None,
                  ed=chosen_end_date if chosen_end_date != def_val['chosen_end_date'] else None,
                  icn=if_contracts_names if if_contracts_names != def_val['if_contracts_names'] else None,
                  iep=if_excl_phishing if if_excl_phishing != def_val['if_excl_phishing'] else None,
                  ovt=value_threshold if value_threshold not in def_val['value_threshold'] else None,
                  ovot=volume_threshold if volume_threshold != def_val['volume_threshold'] else None,
                  eo=if_excl_outliers if if_excl_outliers != def_val['if_excl_outliers'] else None,
                  urp=if_use_real_prices if if_use_real_prices != def_val['if_use_real_prices'] else None,
                  it=if_time if if_time != def_val['if_time'] else None,
                  ii=if_internal if if_internal != def_val['if_internal'] else None,
                  ct=chosen_top if chosen_top != def_val['chosen_top'] else None,
                  gpt=if_gpt_conclusions if if_gpt_conclusions != def_val['if_gpt_conclusions'] else None,
                  ig=if_gas if if_gas != def_val['if_gas'] else None,
                  #r=True
                  )
    st.experimental_set_query_params(**{key: value for key, value in params.items() if value is not None})
    logging.info(f'Analysing {address_given}')
    if address_given is not None and address_given != "" and len(address_given) == 42:
        with st.spinner('Putting out fires...'):
            instance = Analysis(address_given if address_given is not None else None, number_of_dest=num_of_dest,
                                if_all_contracts=if_include_all_dest, start_date=chosen_start_date,
                                end_date=chosen_end_date, if_cont_names=if_contracts_names, if_gas_tick=if_gas,
                                if_exclude_phishing=if_excl_phishing, outlier_value_threshold=value_threshold,
                                outlier_volume_threshold=volume_threshold, exclude_outlying=if_excl_outliers,
                                use_real_prices=if_use_real_prices, if_int=if_internal, if_gpt=if_gpt_conclusions,
                                if_time_needed=if_time, chosen_top=chosen_top)
        st.header(f':heavy_check_mark: _{address_given}_ has revealed its secrets :sunglasses:', divider='rainbow')
        # SHOWING METRICS
        col1, col2, col3, col4 = st.columns([4, 4, 4, 4])
        col1.metric("Interacted contracts", instance.overall_contracts, help=inter_cont_notice)
        col2.metric("Interacted tokens", instance.over_tokens, help=inter_tokens_notice)
        col3.metric("Analyzed/overall destinations", str(instance.analyzed_destinations) + " / " +
                    str(instance.overall_destinations), help=destinations_notice)
        col4.metric("Excluded transactions", instance.percentage_of_outliers, help=outliers_notice)
        # NON-REAL PRICES WARNING
        if not if_use_real_prices:
            st.warning(prices_warning, icon='⚠️')
        # GPT ANALYSIS
        if if_gpt_conclusions:
            st.info(instance.gpt, icon='🤖')
        # PLOTTING TOP TOKENS
        col1, col2, col3 = st.columns([4, 1, 4])
        col1.plotly_chart(instance.top_10_tokens_plotting(chosen_top, by='number'), use_container_width=True,
                          config={'staticPlot': True})
        col3.plotly_chart(instance.top_10_tokens_plotting(chosen_top, by='volume'), use_container_width=True,
                          config={'staticPlot': True})
        # PLOTTING TOP DESTINATIONS
        with st.expander('Destinations analysis'):
            col1, col3 = st.columns([4, 4])
            col1.markdown(f"<h4 style='text-align: left;'>TOP {chosen_top} Destinations FROM by quantity</h4>",
                          unsafe_allow_html=True)
            col1.write(instance.top_destinations(chosen_top, by='quantity', from_or_to='from'))
            col1.markdown(f"<h4 style='text-align: left;'>TOP {chosen_top} Destinations FROM by volume in $US</h4>",
                          unsafe_allow_html=True)
            col1.write(instance.top_destinations(chosen_top, by='volume', from_or_to='from'))
            col3.markdown(f"<h4 style='text-align: left;'>TOP {chosen_top} Destinations TO by quantity</h4>",
                          unsafe_allow_html=True)
            col3.write(instance.top_destinations(chosen_top, by='quantity', from_or_to='to'))
            col3.markdown(f"<h4 style='text-align: left;'>TOP {chosen_top} Destinations TO by volume in $US</h4>",
                          unsafe_allow_html=True)
            col3.write(instance.top_destinations(chosen_top, by='volume', from_or_to='to'))
        # PLOTTING TRANSACTION FLOWS
        with st.expander('Transactions flow'):
            with st.spinner('Plotting...'):
                st.plotly_chart(instance.plotting_trans(by='tokens'), use_container_width=True)
            with st.spinner('Plotting...'):
                st.plotly_chart(instance.plotting_trans(by='Destinations'), use_container_width=True)
        # GAS CONSIDERATION
        if if_gas:
            with st.expander('View gas distribution'):
                if not if_use_real_prices:
                    st.warning(gas_expenses_warning, icon="⚠️")
                col1, col3 = st.columns([4, 4])
                col1.plotly_chart(instance.gas_consideration(chosen_top, by='tokens'), use_container_width=True,
                                  config={'staticPlot': True})
                col3.plotly_chart(instance.gas_consideration(chosen_top, by='contracts'), use_container_width=True,
                                  config={'staticPlot': True})
        # VIEW ERC-20 DATASET
        with st.expander('View the ERC-20 + ETH analysed dataset'):
            st.markdown(f"<h4 style='text-align: left;'>ERC-20 AND ETH transactions involving TOP "
                        f"{num_of_dest if not if_include_all_dest else instance.overall_contracts}"
                        f" contracts</h3>", unsafe_allow_html=True)
            st.write(instance.without_outliers_tier2)
        # INTERNAL TRANSACTIONS
        if if_internal:
            with st.expander('View Internal Transactions Flow'):
                st.plotly_chart(instance.plotting_internal_flows(), use_container_width=True)
            with st.expander('View TOP Internal destinations (contracts)'):
                col1, col2 = st.columns([1, 1])
                col1.plotly_chart(instance.plotting_internal_destinations(by='quantity', choice=chosen_top),
                                  use_container_width=True, config={'staticPlot': True})
                col2.plotly_chart(instance.plotting_internal_destinations(by='volume', choice=chosen_top),
                                  use_container_width=True, config={'staticPlot': True})
            with st.expander('View the Internal Transactions analysed dataset'):
                st.write(instance.internal_df)
            if if_time:
                with st.expander('Transactions time  analysis'):
                    st.plotly_chart(instance.time_consideration(), use_container_width=True)
                    st.plotly_chart(instance.time_consideration_days(), use_container_width=True,
                                    config={'staticPlot': True})
        # OUTLIERS
        st.markdown("""---""")
        with st.expander(f"Transactions excluded from the analysis"):
            st.markdown(f"<h4 style='text-align: left;'>Outliers (missing prices, extortionately high transaction "
                        f"volume, etc.)</h4>",
                        unsafe_allow_html=True)
            st.write(instance.combined_outliers)
    else:
        st.write('<--- Insert a valid address!')
else:
    with open('README.md', 'r') as file:
        st.markdown(file.read())

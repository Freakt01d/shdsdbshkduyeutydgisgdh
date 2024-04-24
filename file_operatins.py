import pandas as pd
from openpyxl import load_workbook
import numpy as np

def file_operations(csv_file_path, workbook_path, output_dir):
    try:
        data = pd.read_csv(csv_file_path, header=0, low_memory=False)
        data2 = data.copy()

        data1 = pd.read_excel(workbook_path)

        filtered_data = data[data['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data = filtered_data[filtered_data['SALERID'].isnull()]
        filtered_data = filtered_data[filtered_data['CUSTOMERTYPE'] == 'noncustomer']
        filtered_data['Counterparties Type'] = np.where(filtered_data['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']), '9 Large Banks without Sales id', 'Exchange_Broker')

        filtered_data2 = data[data['TOPECO'].isin(['0_Portfolio', '_Party'])]

        filtered_data_1 = data2[data2['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data_1 = filtered_data_1[filtered_data_1['CUSTOMERTYPE'] == 'customer']
        filtered_data_1['Counterparties Type'] = np.where(filtered_data_1['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']), '9 Large Banks without Sales id', 'Exchange_Broker')

        filtered_csv = f"{output_dir}/{csv_file_path.split('/')[-1].replace('.csv', '_filtered.csv')}"
        filtered_data.to_csv(filtered_csv, index=False)
        print(f"Filtered data saved to {filtered_csv}")
        print(filtered_data.head())

        filtered_csv1 = f"{output_dir}/{csv_file_path.split('/')[-1].replace('.csv', 'cus_filtered.csv')}"
        filtered_data_1.to_csv(filtered_csv1, index=False)
        print(f"Filtered data saved to {filtered_csv1}")
        print(filtered_data_1.head())

        filtered_data2 = data[data['TOPECO'].isin(['0_Party', '_Party'])]

        pivot_table = pd.pivot_table(filtered_data2, 
                                     values=['COUNTERP_TRADEPARTYID', 'ABS_EXCHANGEDAMOUNT_USD'],  
                                     index='INSTRUMENT_TYPE',  
                                     columns='CUSTOMERTYPE',  
                                     aggfunc={'COUNTERP_TRADEPARTYID': 'count', 'ABS_EXCHANGEDAMOUNT_USD': 'sum'},  
                                     fill_value=0)

        pivot_table['Total_trades'] = pivot_table[('COUNTERP_TRADEPARTYID', 'customer')] + pivot_table[('COUNTERP_TRADEPARTYID', 'noncustomer')]
        pivot_table['Total_amount'] = pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'customer')] + pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'noncustomer')]

        vm7_data = pd.DataFrame({'count': (pivot_table[('COUNTERP_TRADEPARTYID', 'customer')] / pivot_table['Total_trades']) * 1,
                                 'value': (pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'customer')] / pivot_table['Total_amount']) * 1})

        total_trades_cus = pivot_table[('COUNTERP_TRADEPARTYID', 'customer')].sum()
        total_trades = pivot_table['Total_trades'].sum()
        total_amount_cus = pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'customer')].sum()
        total_amount = pivot_table['Total_amount'].sum()

        vm7_data.loc['Grand Total'] = {'count': (total_trades_cus / total_trades) * 1, 'value': (total_amount_cus / total_amount) * 1}

        pivot_table.loc['Grand Total'] = pivot_table.sum()

        pivot_table.columns = [f'{col[0]}_{col[1]}' for col in pivot_table.columns]

        filtered_noncustomer = data[data['TOPECO'].isin(['0_Party', '_Party'])]
        filtered_noncustomer = filtered_noncustomer[(filtered_noncustomer['CUSTOMERTYPE'] == 'noncustomer') & (~filtered_noncustomer['INSTRUMENT_TYPE'].isin(['Cash_Securities']))]

        # Create pivot table 1
        pivot_table1 = pd.pivot_table(filtered_data,
                                      index=['INSTRUMENT_TYPE', 'PRODUCT_STRUCTURE_TYPE'],
                                      values=['ABS_EXCHANGEDAMOUNT_USD', 'COUNTERP_TRADEPARTYID'],
                                      aggfunc={'ABS_EXCHANGEDAMOUNT_USD': 'sum', 'COUNTERP_TRADEPARTYID': 'count'},
                                      fill_value=0,
                                      margins=True,
                                      margins_name='Grand Total')

        pivot_table1.reset_index(inplace=True)
        pivot_table1.sort_values(by=['INSTRUMENT_TYPE', 'PRODUCT_STRUCTURE_TYPE'], inplace=True)

        instrument_types = filtered_noncustomer['INSTRUMENT_TYPE'].unique()
        dropdown_list = []

        for instrument_type in instrument_types:
            filtered_data_1 = filtered_noncustomer[filtered_noncustomer['INSTRUMENT_TYPE'] == instrument_type]
            sub_products = filtered_data_1['PRODUCT_STRUCTURE_TYPE'].astype(str).unique()  # Convert to string    
            dropdown_list.append(instrument_type)
            dropdown_list.extend(['  ' + sub_product for sub_product in sub_products])

        with pd.ExcelWriter(output_dir + '/output_pivot_table.xlsx') as writer:
            pivot_table.to_excel(writer, sheet_name='Pivot Table')
            workbook = writer.book
            worksheet = writer.sheets['Pivot Table']
            vm7_start_col = len(pivot_table.columns) + 2
                    for idx, value in enumerate(vm7_data.index):
            worksheet.write_string(idx + 1, vm7_start_col, value)
            worksheet.write_number(idx + 1, vm7_start_col + 1, vm7_data.loc[value, 'count'])
            worksheet.write_number(idx + 1, vm7_start_col + 2, vm7_data.loc[value, 'value'])

        # Writing dropdown list in the same sheet
        worksheet.write_column(len(pivot_table) + 5, 0, dropdown_list)
        pivot_table1.to_excel(writer, sheet_name='Pivot Table 1')

except Exception as e:
    print(f"Error: {e}")
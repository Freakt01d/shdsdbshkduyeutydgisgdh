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
        filtered_data['Counterparties Type'] = np.where(filtered_data['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']),
                                                        '9 Large Banks without Sales id', 'Exchange_Broker')

        filtered_data1 = data2[data2['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data1 = filtered_data1[filtered_data1['CUSTOMERTYPE'] == 'customer']
        filtered_data1['Counterparties Type'] = np.where(filtered_data1['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']),
                                                         '9 Large Banks without Sales id', 'Exchange_Broker')

        pivot_table = pd.pivot_table(data, 
                                     values=['COUNTERP_TRADEPARTYID', 'ABS_EXCHANGEDAMOUNT_USD'],  
                                     index='INSTRUMENT_TYPE',  
                                     columns='CUSTOMERTYPE',  
                                     aggfunc={'COUNTERP_TRADEPARTYID': 'count', 'ABS_EXCHANGEDAMOUNT_USD': 'sum'},  
                                     fill_value=0)

        pivot_table['Total_trades'] = pivot_table[('COUNTERP_TRADEPARTYID', 'customer')] + pivot_table[('COUNTERP_TRADEPARTYID', 'noncustomer')]
        pivot_table['Total_amount'] = pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'customer')] + pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'noncustomer')]

        vm7_data = pd.DataFrame({
            'count': pivot_table[('COUNTERP_TRADEPARTYID', 'customer')] / pivot_table['Total_trades'],
            'value': pivot_table[('ABS_EXCHANGEDAMOUNT_USD', 'customer')] / pivot_table['Total_amount']
        })

        with pd.ExcelWriter(output_dir + '/output_pivot_table.xlsx', engine='xlsxwriter') as writer:
            pivot_table.to_excel(writer, sheet_name='Pivot Table')
            workbook = writer.book
            worksheet = writer.sheets['Pivot Table']
            vm7_start_col = len(pivot_table.columns) + 2  # Adjust for space

            vm7_data.to_excel(writer, sheet_name='Pivot Table', startrow=2, startcol=vm7_start_col, header=False, index=True)
            
            # Merge cells for vm7 label
            worksheet.merge_range(0, vm7_start_col, 0, vm7_start_col + 1, 'vm7', workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#ADD8E6'}))
            # Set headers for 'count' and 'value'
            worksheet.write(1, vm7_start_col, 'count', workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'}))
            worksheet.write(1, vm7_start_col + 1, 'value', workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'}))

            for col_num, value in enumerate(pivot_table.columns.values):
                worksheet.write(0, col_num, value, workbook.add_format({'bold': True, 'bg_color': '#ADD8E6', 'border': 1}))
                worksheet.set_column(col_num, col_num, 18)  # Adjust column width as needed

            for i in range(1, len(pivot_table.columns) + 1):
                worksheet.write(len(pivot_table) + 2, i, pivot_table.iloc[-1, i - 1], workbook.add_format({'bold': True, 'num_format': '#,##0', 'bg_color': '#ADD8E6'}))

    except Exception as e:
        print(f"Error processing the CSV file: {e}")
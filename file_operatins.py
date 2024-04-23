import pandas as pd
import numpy as np

def file_operations(csv_file_path, workbook_path, output_dir):
    try:
        # Load the CSV file
        data = pd.read_csv(csv_file_path, header=0, low_memory=False)

        # Load the Excel workbook
        data1 = pd.read_excel(workbook_path)

        # Filter data based on specific conditions
        filtered_data = data[data['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data = filtered_data[filtered_data['SALERID'].isnull()]
        filtered_data = filtered_data[filtered_data['CUSTOMERTYPE'] == 'noncustomer']
        filtered_data['Counterparties Type'] = np.where(
            filtered_data['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']),
            '9 Large Banks without Sales id',
            'Exchange_Broker'
        )

        # Save the filtered data to a new CSV file
        filtered_csv = f"{output_dir}/{csv_file_path.split('/')[-1].replace('.csv', '_filtered.csv')}"
        filtered_data.to_csv(filtered_csv, index=False)
        print(f"Filtered data saved to {filtered_csv}")
        print(filtered_data.head())

        # Process and filter another subset of the data
        filtered_data_1 = data[data['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data_1 = filtered_data_1[filtered_data_1['CUSTOMERTYPE'] == 'customer']
        filtered_data_1['Counterparties Type'] = np.where(
            filtered_data_1['COUNTERP_TRADEPARTYID'].isin(data1['COUNTERP_TRADEPARTYID']),
            '9 Large Banks without Sales id',
            'Exchange_Broker'
        )

        # Save this other subset to a new CSV file
        filtered_csv1 = f"{output_dir}/{csv_file_path.split('/')[-1].replace('.csv', 'cus_filtered.csv')}"
        filtered_data_1.to_csv(filtered_csv1, index=False)
        print(f"Filtered data saved to {filtered_csv1}")
        print(filtered_data_1.head())

        # Create a pivot table from a specific subset of data
        filtered_data2 = data[data['TOPECO'].isin(['0_Party', '_Party'])]
        pivot_table = pd.pivot_table(
            filtered_data2,
            values=['COUNTERP_TRADEPARTYID', 'ABS_EXCHANGEDAMOUNT_USD'],
            index='INSTRUMENT_TYPE',
            columns='CUSTOMERTYPE',
            aggfunc={'COUNTERP_TRADEPARTYID': 'count', 'ABS_EXCHANGEDAMOUNT_USD': 'sum'},
            fill_value=0
        )
        
        # Rename the columns of the pivot table to be more descriptive
        pivot_table.columns = [f'{col[0]}_{col[1]}' for col in pivot_table.columns]

        # Save the pivot table to an Excel file
        pivot_output_path = output_dir + '/output_pivot_table.xlsx'
        with pd.ExcelWriter(pivot_output_path) as writer:
            pivot_table.to_excel(writer, sheet_name='Pivot Table')
        print(f"Pivot table saved to {pivot_output_path}")

    except Exception as e:
        print(f"Error processing the CSV file: {e}")
        
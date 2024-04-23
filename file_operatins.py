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
        filtered_data_1['Counterparties Type​⬤
        
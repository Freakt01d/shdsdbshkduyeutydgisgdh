import pandas as pd
from openpyxl import load_workbook

def file_operations(csv_file_path, workbook_path, output_dir):
    try:
        # Load CSV data
        data = pd.read_csv(csv_file_path, header=0)
        
        # Load workbook and get active worksheet
        wb = load_workbook(workbook_path)
        ws = wb.active
        
        # Create a dictionary for faster lookups
        lookup_dict = {row[0].value: row[2].value for row in ws.iter_rows(min_row=2)}
        lookup_dict = {k: v for k, v in lookup_dict.items() if k is not None}

        # Define a vlookup function using the dictionary
        def vlookup_func(value, lookup_dict):
            return lookup_dict.get(value, "Exchange_Broker")

        # Filter the DataFrame based on conditions
        filtered_data = data[data['TOPECO'].isin(['1_Portfolio', '1_Party'])]
        filtered_data['Counterparties Type'] = filtered_data['E'].apply(lambda x: vlookup_func(x, lookup_dict))
        filtered_data = filtered_data[filtered_data['SALERID'].isnull()]
        filtered_data = filtered_data[filtered_data['CUSTOMERTYPE'] == 'noncustomer']

        # Define the output CSV file path within the specified output directory
        filtered_csv = f"{output_dir}/{csv_file_path.split('/')[-1].replace('.csv', '_filtered.csv')}"
        filtered_data.to_csv(filtered_csv, index=False)
        print(f"Filtered data saved to {filtered_csv}")
        print(filtered_data.head())
        
    except Exception as e:
        print(f"Error processing the csv file: {e}")

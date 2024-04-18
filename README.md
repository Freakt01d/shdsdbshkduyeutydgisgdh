# shdsdbshkduyeutydgisgdh
# data_operations.py
import pandas as pd
from openpyxl import load_workbook

def perform_operations(csv_file_path):
    try:
        # Load CSV file with the first row as headers
        data = pd.read_csv(csv_file_path, header=0)

        # Load Excel file containing lookup data
        wb = load_workbook('9 large banks_List.xlsx')
        ws = wb.active  # Assuming we only use the active sheet

        # Define a function to perform the lookup
        def vlookup_func(value, lookup_ws, col_key=0, col_value=2):
            for row in lookup_ws.iter_rows(min_row=2):  # Adjust if headers are not in the first row
                if row[col_key].value == value:
                    return row[col_value].value
            return "not part of 9 large banks"

        # Find the column with header 'TOPECO'
        column_name = 'AM'  # Adjust this if 'AM' is not the direct column name but an identifier
        for name in data.columns:
            if data.at[0, name] == 'TOPECO':
                column_name = name
                break

        # Apply filters
        filtered_data = data[data[column_name].isin(['1_Portfolio', '1_Party'])]
        filtered_data = filtered_data.iloc[1:]  # Drop first row if it contains 'TOPECO'

        # Add a new column "Counterparties Type"
        filtered_data['Counterparties Type'] = filtered_data.apply(lambda row: vlookup_func(row['E'], ws), axis=1)

        # Filter "SALERID" and "CUSTOMERTYPE"
        filtered_data = filtered_data[filtered_data['SALERID'].isnull() & (filtered_data['CUSTOMERTYPE'] == 'noncustomer')]

        # Save the filtered data
        filtered_csv_path = csv_file_path.replace('.csv', '_filtered.csv')
        filtered_data.to_csv(filtered_csv_path, index=False)

        print(f"Filtered data saved to: {filtered_csv_path}")
    except Exception as e:
        print(f"Error processing the CSV file: {e}")


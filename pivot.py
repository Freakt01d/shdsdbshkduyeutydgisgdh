import pandas as pd
from tkinter import Tk, Button, filedialog, simpledialog

def load_data():
    # Open a dialog to select multiple files
    file_paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
    
    if file_paths:
        dfs = []  # List to hold dataframes
        
        # Loop through all selected files
        for file_path in file_paths:
            # Read each CSV file and append to the list
            df = pd.read_csv(file_path)
            dfs.append(df)
        
        # Concatenate all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Ask user for file name to save the combined DataFrame
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if save_path:
            # Save the DataFrame to a CSV file
            combined_df.to_csv(save_path, index=False)
            print(f"Data saved to {save_path}.")
        else:
            print("Save cancelled.")
    else:
        print("No files selected.")

# Set up the main application window
root = Tk()
root.title("File Loader")

# Button to load data
load_button = Button(root, text="Select Files and Load Data", command=load_data)
load_button.pack(pady=20)

# Run the GUI event loop
root.mainloop()

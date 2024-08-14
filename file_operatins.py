import pandas as pd

# Step 1: Read the CSV file to get the original column order
original_df = pd.read_csv('your_file.csv')
original_columns = list(original_df.columns)

# Assume `concatenated_df` is your DataFrame after concatenation and adding new columns
# concatenated_df = ... (your DataFrame after all operations)

# Step 2: Identify extra columns not in the original order
extra_columns = [col for col in concatenated_df.columns if col not in original_columns]

# Step 3: Reorder the columns: original columns first, then extra columns
ordered_columns = original_columns + extra_columns
reordered_df = concatenated_df[ordered_columns]

# Step 4: Save the reordered DataFrame (optional)
reordered_df.to_csv('your_reordered_file.csv', index=False)
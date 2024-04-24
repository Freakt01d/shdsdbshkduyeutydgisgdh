pivot_table = pd.pivot_table(
    merged_df,
    values=['amount', 'COUNTERP_TRADEPARTYID'],
    index=['bank_name'],
    aggfunc={
        'amount': np.sum,
        'COUNTERP_TRADEPARTYID': 'count'
    },
    margins=True,
    margins_name='Grand Total'
)

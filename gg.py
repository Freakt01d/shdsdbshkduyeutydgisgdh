pivot_table = pd.pivot_table(
    filtered_data,
    values=['asb_exchange_amount', 'COUNTERP_TRADEPARTYID'],
    index=['Counterparties Type'],
    aggfunc={
        'asb_exchange_amount': np.sum,
        'COUNTERP_TRADEPARTYID': 'count'
    },
    margins=True,
    margins_name='Grand Total'
)

print(pivot_table)

import pandas as pd
import matplotlib.pyplot as plt
import os
import json
import numpy as np
import seaborn as sns
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
from matplotlib.ticker import LogLocator
import networkx as nx
import itertools
from matplotlib.backends.backend_pdf import PdfPages


# =================================================================================
# Load files
# =================================================================================
trades_preprocessed_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/polymarket_OrderFilled_preprocessed.csv"))
trades_preprocessed_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/polymarket_OrderFilled_preprocessed_mint_and_merge.csv"))

trades_labeled_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/trades_labeled.csv"))
trades_labeled_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/trades_labeled_mint_and_merge.csv"))
trades_labeled_all = pd.concat([trades_labeled_normal,trades_labeled_mint_merge])
trades_labeled_all = trades_labeled_all.reset_index()

wash_trades_labeled_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/wash_trades_labeled.csv"))
wash_trades_labeled_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/wash_trades_labeled_mint_and_merge.csv"))
# wash_trades_labeled_all = pd.concat([wash_trades_labeled_normal,wash_trades_labeled_mint_merge])
# wash_trades_labeled_all = wash_trades_labeled_all.reset_index()
self_trades_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/self_trades.csv"))
self_trades_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/self_trades_mint_and_merge.csv"))
self_trades_normal['is_wash_trade'] = True
self_trades_normal['token_buyer_id'] = '9999999999'
self_trades_normal['token_seller_id'] = '9999999999'
self_trades_mint_merge['is_wash_trade'] = True
self_trades_mint_merge['token_buyer_id'] = '9999999999'
self_trades_mint_merge['token_seller_id'] = '9999999999'
wash_trades_labeled_all = pd.concat([wash_trades_labeled_normal, wash_trades_labeled_mint_merge, self_trades_mint_merge, self_trades_normal])
wash_trades_labeled_all = wash_trades_labeled_all.reset_index()


scc_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/scc.csv"))
scc_mapping_normal = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/scc_mapping.csv"))

scc_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/scc_mint_and_merge.csv"))
scc_mapping_mint_merge = pd.read_csv(os.path.join(os.path.dirname(__file__),"./output/scc_mapping_mint_and_merge.csv"))

trades_labeled_all['usdc_amount'] = trades_labeled_all['usdc_amount'].astype(int) / 1000000
# wash_trades_labeled_all['usdc_amount'] = wash_trades_labeled_all['usdc_amount'].astype(int) / 1000000

# =================================================================================
# Distribution of trade volumes by market 
# =================================================================================
trade_volumes_by_market = trades_labeled_all.groupby(['question']).agg(total_usdc_amount=('usdc_amount', 'sum')).reset_index()
# trade_volumes_by_market.to_csv(os.path.join(os.path.dirname(__file__),"./output/volumes_by_market.csv"), index=False)
top_vol_market = trade_volumes_by_market.nlargest(10, 'total_usdc_amount')

top_vol_market.plot(kind='bar', stacked=True, figsize=(50, 36), colormap='tab20',legend=False)
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(top_vol_market['question'], top_vol_market['total_usdc_amount'])
ax.set_xticks(top_vol_market['question'])
ax.set_xticklabels(top_vol_market['question'], rotation=45, ha='right')
ax.set_xlabel('Market')
ax.set_ylabel('USDC Volume')
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/volumes_by_market.pdf"))

# =================================================================================
# Share of wash trades with respect to total trades by market, ordered by the number of wash trades
# =================================================================================
amounts_by_market = trades_labeled_all.groupby('question').agg(
                        total_usdc_amount=('usdc_amount', 'sum'),
                        wash_usdc_amount=('usdc_amount', lambda x: x[trades_labeled_all['is_wash_trade'] == True].sum())).reset_index()
amounts_by_market['wash_percentage'] = (amounts_by_market['wash_usdc_amount'] / amounts_by_market['total_usdc_amount']) * 100
amounts_by_market = amounts_by_market.sort_values(by='wash_usdc_amount', ascending=False)
# amounts_by_market.to_csv(os.path.join(os.path.dirname(__file__),"./output/wash_percentage.csv"), index=False)

# plotting
amounts_by_market = amounts_by_market.head(10)
fig, ax = plt.subplots(figsize=(12, 6))
x_indices = amounts_by_market['question']
bar_width = 0.6
ax.bar(
    x_indices, 
    amounts_by_market['total_usdc_amount'], 
    color='blue', 
    label='Total USDC Volume', 
    width=bar_width
)
ax.bar(
    x_indices, 
    amounts_by_market['wash_usdc_amount'], 
    color='orange', 
    label='Wash Trading Volume', 
    width=bar_width
)
ax.set_xticks(x_indices)
ax.set_xticklabels(amounts_by_market['question'], rotation=45, ha='right')
ax.set_ylabel('USDC Volume')
ax.set_xlabel('Market')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/wash_percentage_by_market.pdf"))

# =================================================================================
# SCC occurences CDF
# =================================================================================
occurrence = np.sort(scc_normal['occurrence'])
# occurence_ccdf = 1.0 - np.arange(1, len(occurrence) + 1) / len(occurrence)
occurence_cdf = np.arange(1, len(occurrence) + 1) / len(occurrence)

plt.figure(figsize=(12, 6))
plt.plot(occurrence, occurence_cdf, marker='o', linestyle='-')
plt.xlim(0, 100)
plt.xlabel('Occurrences (X)')
plt.ylabel('Fraction of SCCs occurring at most X times')
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/scc_normal_cdf.pdf"))

# #----------------------------------------------------------------------------------

occurrence = np.sort(scc_mint_merge['occurrence'])
# occurence_ccdf = 1.0 - np.arange(1, len(occurrence) + 1) / len(occurrence)
occurence_cdf = np.arange(1, len(occurrence) + 1) / len(occurrence)

plt.figure(figsize=(12, 6))
plt.plot(occurrence, occurence_cdf, marker='o', linestyle='-')
plt.xlim(0, 100)
plt.xlabel('Occurrences (X)')
plt.ylabel('Fraction of SCCs occurring at most X times')
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/scc_mint_and_merge_cdf.pdf"))

# =================================================================================
# Wash trading in market timeline
# =================================================================================
wash_timeframe = pd.concat([trades_labeled_all, self_trades_normal, self_trades_mint_merge],ignore_index=True)
def normalize_timestamp(x):
    return (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0

wash_timeframe['timeframe'] = wash_timeframe.groupby(["question","is_wash_trade"])["block_timestamp_unix"].transform(normalize_timestamp)
wash_median = (wash_timeframe.loc[wash_timeframe["is_wash_trade"] == True]
                                  .groupby("question")["timeframe"]
                                  .median()
                                  .reset_index(name="time"))
wash_median["time"] = wash_median["time"].fillna(0)

wash_timeframe_filtered = wash_timeframe.loc[wash_timeframe["is_wash_trade"] == True]
sns.set_theme(style="whitegrid")
plt.figure(figsize=(10, 6))
g = sns.histplot(
    data=wash_timeframe_filtered, 
    x="timeframe", 
    element="step", 
    fill=False, 
    bins=np.arange(0, 1.1, 0.1), 
    common_norm=False,
    stat="count"
)

# g = sns.histplot(
#     data=wash_median, 
#     x="time", 
#     element="step", 
#     fill=False, 
#     bins=np.arange(0, 1.1, 0.1), 
#     common_norm=False,
#     stat="count"
# )
g.set_xticks(np.arange(0, 1.1, 0.1))
g.set_xticklabels([f'{int(x * 100)}%' for x in g.get_xticks()])
g.set_xlabel("Progress in a market's trading timeline")
g.set_ylabel("Number of wash trades")
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/wash_timeline.pdf"))
    
# =================================================================================
# Wash trading CCDF
# =================================================================================
def compute_wash_share(group):
    total_volume = group['usdc_amount'].sum()
    wash_volume = group.loc[group['is_wash_trade'] == True, 'usdc_amount'].sum()
    share = wash_volume / total_volume if total_volume != 0 else 0
    return pd.Series({'share': share})

wash_share = trades_labeled_all.copy()
wash_share = (wash_share.groupby('question', as_index=False).apply(compute_wash_share))
plt.figure(figsize=(6,4))
sns.ecdfplot(
    data=wash_share,
    x='share',
    complementary=True,
)
plt.yscale('log')
plt.xlim(0, 1)
plt.xticks([i/10 for i in range(11)], [f"{i*10}%" for i in range(11)])
ax = plt.gca()
ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=2))
plt.ylabel("Share of markets")
plt.xlabel("Share of wash trade volume in each market")
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/wash_trade_ccdf.pdf"))

# =================================================================================
# Wash trading shapes (normal trades)
# =================================================================================
def match_color(attrs1, attrs2):
    return attrs1['color'] == attrs2['color']

def add_or_increment_graph(g, result_list):
    for i, (existing_g, count) in enumerate(result_list):
        # Check isomorphism
        if nx.is_isomorphic(existing_g, g,node_match=match_color):
            result_list[i] = (existing_g, count+1)
            return 
    # no match, add a new entry
    if g.number_of_nodes() > 0:
        result_list.append((g, 1))

scc_hashes = scc_normal.loc[scc_normal['occurrence'] >= 2, 'scc_hash']
result = []

for scc_hash in scc_hashes:
    scc_trader_ids = scc_mapping_normal.loc[scc_mapping_normal['hash'] == scc_hash, 'trader_id']
    scc_wash_trades = wash_trades_labeled_normal[
            (wash_trades_labeled_normal['token_seller_id'].isin(scc_trader_ids)) &
            (wash_trades_labeled_normal['token_buyer_id'].isin(scc_trader_ids)) & 
            (wash_trades_labeled_normal['is_wash_trade'] == True)
            ][['token_seller_id', 'token_buyer_id', 'question']]

    for question, group in scc_wash_trades.groupby('question'):
        new_g = nx.DiGraph()
        for _, row in group.iterrows():
            seller = row['token_seller_id']
            buyer  = row['token_buyer_id']
            new_g.add_node(seller,color='tab:blue')
            new_g.add_node(buyer,color='tab:blue')
            new_g.add_edge(seller, buyer)
        if new_g.number_of_nodes() > 0 and nx.is_strongly_connected(new_g):
            add_or_increment_graph(new_g, result)

result = sorted(result,key=lambda tup: (tup[0].number_of_nodes(), tup[0].number_of_edges()))

with PdfPages(os.path.join(os.path.dirname(__file__), "./output/plots/wash_trade_shapes_normal.pdf")) as pdf:
    for i, (g, count) in enumerate(result):
        fig, ax = plt.subplots(figsize=(10, 10))
        pos = nx.circular_layout(g)
        nx.draw_networkx_nodes(g, pos, node_size=500, ax=ax)
        nx.draw_networkx_edges(g, pos, arrowstyle='->', arrowsize=20, width=2, ax=ax, connectionstyle='arc3,rad=0.2')
        # nx.draw_networkx_labels(g, pos, ax=ax)  # or omit for no labels
        graph_label = f"count: {count}"
        plt.title(graph_label, fontsize=16)
        plt.axis('off')
        pdf.savefig(fig)
        plt.close(fig)

# =================================================================================
# Wash trading shapes (mint and merges)
# =================================================================================
scc_hashes = scc_mint_merge.loc[scc_mint_merge['occurrence'] >= 3, 'scc_hash']
result = []

for scc_hash in scc_hashes:
    scc_trader_ids = scc_mapping_mint_merge.loc[scc_mapping_mint_merge['hash'] == scc_hash, 'trader_id']
    # only look at scc's not made against exchange
    if "0" not in [str(id) for id in scc_trader_ids.tolist()]:
        scc_wash_trades = wash_trades_labeled_mint_merge[
                (wash_trades_labeled_mint_merge['token_seller_id'].isin(scc_trader_ids)) &
                (wash_trades_labeled_mint_merge['token_buyer_id'].isin(scc_trader_ids)) & 
                (wash_trades_labeled_mint_merge['is_wash_trade'] == True)
                ][['token_seller_id', 'token_buyer_id', 'question', 'orderHash', 'transactionHash']]
        cond_1 = wash_trades_labeled_mint_merge["transactionHash"].isin(scc_wash_trades["transactionHash"]) & ~(wash_trades_labeled_mint_merge["orderHash"].isin(scc_wash_trades["orderHash"]))
        cond_2 = wash_trades_labeled_mint_merge["transactionHash"].isin(scc_wash_trades["transactionHash"]) & ~(wash_trades_labeled_mint_merge["orderHash"].isin(scc_wash_trades["orderHash"]))
        other_trades_in_wash = wash_trades_labeled_mint_merge[(cond_1|cond_2)][['token_seller_id', 'token_buyer_id', 'question', 'orderHash', 'transactionHash']]
        all_trades_in_scc = pd.concat([scc_wash_trades,other_trades_in_wash])

        for question, group in all_trades_in_scc.groupby('question'):
            new_g = nx.DiGraph()
            for _, row in group.iterrows():
                seller = row['token_seller_id']
                buyer  = row['token_buyer_id']
                new_g.add_node(seller, color='red' if seller == 0 else 'tab:blue')
                new_g.add_node(buyer, color='red' if buyer == 0 else 'tab:blue')
                new_g.add_edge(seller, buyer)
            if new_g.number_of_nodes() > 0 and nx.is_strongly_connected(new_g) and any((data.get('color') == 'red') for _, data in new_g.nodes(data=True)):
                add_or_increment_graph(new_g, result)

result = sorted(result,key=lambda tup: (tup[0].number_of_nodes(), tup[0].number_of_edges()))

with PdfPages(os.path.join(os.path.dirname(__file__), "./output/plots/wash_trade_shapes_mint_and_merge.pdf")) as pdf:
    for i, (g, count) in enumerate(result):
        fig, ax = plt.subplots(figsize=(10, 10))
        pos = nx.circular_layout(g)
        node_colors = [g.nodes[node]['color'] for node in g.nodes]
        nx.draw_networkx_nodes(g, pos, node_color=node_colors, node_size=500, ax=ax)
        nx.draw_networkx_edges(g, pos, arrowstyle='->', arrowsize=20, width=2, ax=ax, connectionstyle='arc3,rad=0.2')
        # nx.draw_networkx_labels(g, pos, ax=ax)  # or omit for no labels
        graph_label = f"count: {count}"
        plt.title(graph_label, fontsize=16)
        plt.axis('off')
        pdf.savefig(fig)
        plt.close(fig)


# =================================================================================
# Preprocessed dataset summary
# =================================================================================
makers = trades_preprocessed_normal["maker"].tolist()
takers = trades_preprocessed_normal["taker"].tolist()

num_txn_normal = trades_preprocessed_normal["transactionHash"].nunique()
num_txn_mint_merge = trades_preprocessed_mint_merge["transactionHash"].nunique()
num_market_normal = trades_preprocessed_normal["question"].nunique()
num_market_mint_merge = trades_preprocessed_mint_merge["question"].nunique()
num_traders_normal = len(set(trades_preprocessed_normal["maker"].unique()).union(set(trades_preprocessed_normal["taker"].unique())))
num_traders_mint_merge = len(set(trades_preprocessed_mint_merge["maker"].unique()).union(set(trades_preprocessed_mint_merge["taker"].unique())))
print(num_txn_normal,num_txn_mint_merge,num_market_normal,num_market_mint_merge,num_traders_normal,num_traders_mint_merge)
# =================================================================================
# Summary metrics
# =================================================================================
self_trades_all = pd.concat([self_trades_normal,self_trades_mint_merge])
num_self_traders = len(set(self_trades_all["token_buyer"]).union(self_trades_all["token_seller"]))
print(num_self_traders)

total_amount = trades_labeled_all['usdc_amount'].astype(int).sum()
wash_amount = trades_labeled_all.loc[trades_labeled_all['is_wash_trade'] == True, 'usdc_amount'].astype(int).sum()
self_trade_amount = (self_trades_all['usdc_amount'].astype(int).sum()) / 1000000
print(total_amount, wash_amount, self_trade_amount)


num_market_washed = pd.concat([wash_trades_labeled_all["question"],self_trades_all['question']]).nunique()
print(num_market_washed)

num_wash_traders = len(set(wash_trades_labeled_all["token_buyer"].unique()).union(set(wash_trades_labeled_all["token_seller"].unique())))
print(num_wash_traders)

# =================================================================================
# Wash trading volume by month
# =================================================================================
wash_share = wash_trades_labeled_all.copy()
wash_share['usdc_amount'] = wash_share['usdc_amount'].astype(int) / 1000000
wash_share['date'] = pd.to_datetime(wash_share['block_timestamp_unix'], unit='s')
wash_share['month'] = wash_share['date'].dt.to_period('M').dt.to_timestamp()
monthly_wash_volume = (wash_share.groupby(["month"])["usdc_amount"].sum().reset_index(name='monthly_wash_volume'))
# print(monthly_wash_volume['month'])


fig, ax = plt.subplots(figsize=(8,4))


ax.bar(monthly_wash_volume['month'], monthly_wash_volume['monthly_wash_volume'],width=20)
ax.set_xlabel('Date')
ax.set_ylabel('USDC Volume')
ax.tick_params(axis='x', labelrotation=45)

plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/wash_vol_by_month.pdf"))

# =================================================================================
# Wash trading volume at time of the day
# =================================================================================
wash_copy = wash_trades_labeled_all.copy()
wash_copy['datetime'] = pd.to_datetime(wash_copy['block_timestamp_unix'], unit='s', utc=True)
wash_copy['hour'] = wash_copy['datetime'].dt.hour
hour_counts = wash_copy['hour'].value_counts().sort_index()
plt.figure(figsize=(10, 6))
hour_counts.plot(kind='bar')
plt.xlabel('Hour of the Day (UTC)')
plt.ylabel('Number of Wash Trades')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__),"./output/plots/wash_trades_during_day.pdf"))

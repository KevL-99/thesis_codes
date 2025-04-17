import warnings
warnings.simplefilter(action='ignore', category=Warning)
import pandas as pd
import networkx as nx
import os
import hashlib
import matplotlib.pyplot as plt
from tqdm import tqdm
import pulp

# global variables
global_usdc_id = "0" # TODO: change to "0" for real data
global_trader_hashes = pd.DataFrame(columns=["trader_address", "trader_id"], dtype=str)
global_scc_traders_map = {}

def restructure_trades(trades):
    global global_usdc_id
    trades = trades.drop(columns=["fee","event","logIndex","transactionIndex","address","blockHash","blockNumber","block_timestamp","msg_sender"])
    trades_buy_token_with_usdc = trades[trades["makerAssetId"] == global_usdc_id].rename(columns={"maker": "token_buyer", 
                                                                                                  "taker": "token_seller",
                                                                                                  "makerAssetId": "usdc_id",
                                                                                                  "takerAssetId": "token_id",
                                                                                                  "makerAmountFilled": "usdc_amount",
                                                                                                  "takerAmountFilled": "token_amount"})
    trades_sell_token_for_usdc = trades[trades["takerAssetId"] == global_usdc_id].rename(columns={"maker": "token_seller",
                                                                                                  "taker": "token_buyer",
                                                                                                  "makerAssetId": "token_id",
                                                                                                  "takerAssetId": "usdc_id",
                                                                                                  "makerAmountFilled": "token_amount",
                                                                                                  "takerAmountFilled": "usdc_amount"})
    trades = pd.concat([trades_buy_token_with_usdc, trades_sell_token_for_usdc], ignore_index=True)
    return trades

def filter_self_trades(trades, save = True):
    reg_trades = trades[trades["token_buyer"] != trades["token_seller"]]
    self_trades = trades[trades["token_buyer"] == trades["token_seller"]]
    if save:
        self_trades.to_csv(os.path.join(os.path.dirname(__file__),"./output/self_trades.csv"), index=False)
    return reg_trades, self_trades

def add_trader_hashes(trades, load_existing_hashes = False, save = True):
    global global_trader_hashes 

    if load_existing_hashes:
        global_trader_hashes = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/trader_hashes.csv"))
        global_trader_hashes = global_trader_hashes .astype({"trader_id": str})

    if (global_trader_hashes.shape[0] == 0):
        unique_addresses = sorted(pd.concat([trades["token_buyer"], trades["token_seller"]]).unique())
        global_trader_hashes["trader_address"] = unique_addresses
        global_trader_hashes["trader_id"] = [str(i) for i in range(1, len(unique_addresses) + 1)]
    else:
        unique_addresses = sorted(pd.concat([trades["token_buyer"], trades["token_seller"]]).unique())
        additional_traders = list(set(unique_addresses) - set(global_trader_hashes["trader_address"]))
        if (len(additional_traders) != 0):
            n_old = global_trader_hashes.shape[0]
            n_new = n_old + len(additional_traders)
            additional_trader_hashes = pd.DataFrame(columns=["trader_address", "trader_id"], dtype=str)
            additional_trader_hashes["trader_address"] =  additional_traders
            additional_trader_hashes["trader_id"] = [str(i) for i in range(n_old + 1, n_new + 1)]
            global_trader_hashes = pd.concat([global_trader_hashes, additional_trader_hashes], ignore_index=True)
    
    # merge with trades
    trades = trades.merge(global_trader_hashes.rename(columns={"trader_id": "token_buyer_id"}), 
                          how="left", 
                          left_on="token_buyer", 
                          right_on="trader_address").drop(columns=["trader_address"])
    
    trades = trades.merge(global_trader_hashes.rename(columns={"trader_id": "token_seller_id"}), 
                          how="left", 
                          left_on="token_seller", 
                          right_on="trader_address").drop(columns=["trader_address"])
    trades = trades.sort_values(by="block_timestamp_unix").reset_index(drop=True)
    if save:
        global_trader_hashes.to_csv(os.path.join(os.path.dirname(__file__),"./data/trader_hashes.csv"), index=False)
    return trades

def detect_scc_for_tokens(trades, save=True):
    global global_scc_traders_map
    tokens = trades["token_id"].unique()
    result = []

    for token_id in tqdm(tokens, desc="processing token scc"):
        token_trades = trades[trades["token_id"] == token_id]
        g = nx.MultiDiGraph()
        # g.add_edges_from(token_trades[["token_buyer_id", "token_seller_id"]].values)
        for _, row in token_trades.iterrows():
            g.add_edge(row["token_seller_id"], row["token_buyer_id"], weight=1)
        # nx.draw(g)
        # plt.show()
        # print(g.edges)

        # simplify the graph
        gs = nx.DiGraph()
        for u, v, data in g.edges(data=True):
            if gs.has_edge(u, v):
                gs[u][v]["weight"] += data["weight"]
            else:
                gs.add_edge(u, v, weight=data["weight"])
        # nx.draw(gs)
        # plt.show()
        
        # scc detection
        while gs.number_of_nodes() > 0:
            scc_larger_than_one = [c for c in nx.strongly_connected_components(gs) if len(c) > 1]
            # print(scc_larger_than_one)
            if len(scc_larger_than_one) == 0:
                break 

            for c in scc_larger_than_one:
                sorted_members = sorted(c)
                c_hash = hashlib.md5(",".join(sorted_members).encode()).hexdigest()
                global_scc_traders_map[c_hash] = sorted_members
                result.append(c_hash)

            # decrease weight and remove vertices
            for u, v in list(gs.edges):
                gs[u][v]["weight"] -= 1
                if gs[u][v]["weight"] == 0:
                    gs.remove_edge(u, v)
            gs.remove_nodes_from(list(nx.isolates(gs)))
    # print(result)
    scc_dt = pd.DataFrame({"scc_hash": result})
    scc_dt = scc_dt.groupby("scc_hash").size().reset_index(name="occurrence")
    scc_dt["num_traders"] = scc_dt["scc_hash"].apply(lambda x: len(global_scc_traders_map[x]))

    if save:
        scc_dt.to_csv(os.path.join(os.path.dirname(__file__),"./output/scc.csv"), index=False)
        scc_mapping = pd.DataFrame([
            {"hash": h, "trader_id": trader_id}
            for h, trader_ids in global_scc_traders_map.items()
            for trader_id in trader_ids
        ])
        scc_mapping.to_csv(os.path.join(os.path.dirname(__file__),"./output/scc_mapping.csv"), index=False)
    return scc_dt

def get_repeated_scc(scc_dt, threshold):
    repeated_scc = scc_dt[scc_dt["occurrence"] >= threshold]
    return repeated_scc

def detect_and_label_wash_trades_for_scc_with_multiple_time_windows(trades, repeated_scc, window_sizes_in_seconds, window_start, margin, use_ilp):
    global global_scc_traders_map
    
    wash_trades = {}
    trades["is_wash_trade"] = None
    if window_start is None:
        window_start = trades["block_timestamp_unix"].min()

    for window_size in window_sizes_in_seconds:  
        break_points = get_sequence(window_start, trades["block_timestamp_unix"].max(), window_size)
        # print(break_points)  
        for scc_id in tqdm(repeated_scc["scc_hash"], desc="scc volume matching"): # rows of scc_dt
            scc_traders = global_scc_traders_map[scc_id]
            # print(scc_traders)
            cond_1 = trades["token_buyer_id"].isin(scc_traders) & trades["token_seller_id"].isin(scc_traders) & trades["is_wash_trade"].isnull()
            cond_2 = trades["token_buyer_id"].isin(scc_traders) & trades["token_seller_id"].isin(scc_traders) & (trades["is_wash_trade"] == False)
            scc_trades = trades[cond_1 | cond_2]
            if scc_trades.shape[0] == 0:
                # print("no scc trades")
                if scc_id not in wash_trades.keys():
                    wash_trades[scc_id] = {}
                if str(window_size) not in wash_trades[scc_id].keys():
                    wash_trades[scc_id][str(window_size)] = []
                continue
            # print("has scc trades")
            trades.loc[trades["transactionHash"].isin(scc_trades["transactionHash"]), "is_wash_trade"] = False 
            # interval = [break_point, next_break_point)
            scc_trades["interval"] = pd.cut(scc_trades["block_timestamp_unix"],
                                            bins=break_points,
                                            right=False,           
                                            include_lowest=True)
            # print(scc_trades)
            scc_trades_grouped = scc_trades.groupby(["token_id", "interval"])
            scc_trades_per_token_and_time_window = {key: group for key, group in scc_trades_grouped}
            # scc_trades_per_token_and_time_window = scc_trades # placeholder
            
            for _, single_scc_trade in scc_trades_per_token_and_time_window.items():
                # print(single_scc_trade)
                if use_ilp:
                    scc_wash_trades = detect_and_label_wash_trades_using_ilp_volume_matching_dynamic_bound(single_scc_trade, margin)
                else:
                    scc_wash_trades = detect_and_label_wash_trades_using_volume_matching(single_scc_trade, margin)           
                # print(scc_wash_trades)
                if scc_id not in wash_trades.keys():
                    wash_trades[scc_id] = {}
                if str(window_size) not in wash_trades[scc_id].keys():
                    wash_trades[scc_id][str(window_size)] = []
                wash_trades[scc_id][str(window_size)].append(scc_wash_trades)

                # update label in trades
                trades.loc[trades["transactionHash"].isin(scc_wash_trades[scc_wash_trades["is_wash_trade"] == True]["transactionHash"]), "is_wash_trade"] = True
    return trades, wash_trades

def detect_and_label_wash_trades_for_scc_for_single_time_window(trades, repeated_scc, window_size_in_seconds, window_start, margin):
    global global_scc_traders_map
    
    trades["is_wash_trade"] = None
    if window_start is None:
        window_start = trades["block_timestamp_unix"].min()

    break_points = get_sequence(window_start, trades["block_timestamp_unix"].max(), window_size_in_seconds)
    # print(break_points)  
    for scc_id in tqdm(repeated_scc["scc_hash"], desc="scc volume matching"): # rows of scc_dt
        scc_traders = global_scc_traders_map[scc_id]
        # print("scc_traders")
        # print(scc_traders)
        cond_1 = trades["token_buyer_id"].isin(scc_traders) & trades["token_seller_id"].isin(scc_traders) & trades["is_wash_trade"].isnull()
        cond_2 = trades["token_buyer_id"].isin(scc_traders) & trades["token_seller_id"].isin(scc_traders) & (trades["is_wash_trade"] == False)
        scc_trades = trades[cond_1 | cond_2]
        # print("scc_trades")
        # print(scc_trades)
        if scc_trades.shape[0] == 0:
            continue
        trades.loc[trades["transactionHash"].isin(scc_trades["transactionHash"]), "is_wash_trade"] = False 
        # interval = [break_point, next_break_point)
        scc_trades["interval"] = pd.cut(scc_trades["block_timestamp_unix"],
                                        bins=break_points,
                                        right=False,           
                                        include_lowest=True)
        scc_trades_grouped = scc_trades.groupby(["token_id", "interval"])
        scc_trades_per_token_and_time_window = {key: group for key, group in scc_trades_grouped}
        # scc_trades_per_token_and_time_window = scc_trades # placeholder

        # print("number of scc trades per token and time window")  
        # print(len(scc_trades_per_token_and_time_window.items()))
        # print(scc_trades_per_token_and_time_window.items())
        for _, single_scc_trade in scc_trades_per_token_and_time_window.items():
            scc_wash_trades = detect_and_label_wash_trades_using_volume_matching(single_scc_trade, margin)
            # update label in trades
            trades.loc[trades["transactionHash"].isin(scc_wash_trades[scc_wash_trades["is_wash_trade"] == True]["transactionHash"]), "is_wash_trade"] = True
        # print(trades)

    return trades

def detect_and_label_wash_trades_using_ilp_volume_matching_dynamic_bound(trades, margin):
    trades = trades.reset_index()
    n = trades.shape[0]
    
    buyers  = trades["token_seller_id"].tolist()
    sellers = trades["token_buyer_id"].tolist()
    amounts = trades["usdc_amount"].tolist()
    traders = set(buyers).union(set(sellers))
    # traders = set(trades["token_seller_id"]).union(trades["token_buyer_id"])
    

    chosen_indices = []
    
    for K in range(n, 0, -1):
        # K * position(t) <= margin * sum{amount_i * x_i} for all t

        prob = pulp.LpProblem("vol_match", pulp.LpMinimize)
        x = pulp.LpVariable.dicts("x", range(n), cat=pulp.LpBinary) # decision variable x_i = 0 or 1
        prob.setObjective(pulp.lpSum(0.0 for i in range(n))) # dummy objective
        prob.addConstraint(pulp.lpSum(x[i] for i in range(n)) >= K)
        sum_of_amounts = pulp.lpSum(amounts[i]*x[i] for i in range(n))

        # position(t) = sum{amounts s.t. buyer = t} - sum{amounts s.t. seller = t} for all t
        for t in traders:
            pos_t = pulp.lpSum(amounts[i] * x[i] for i in range(n) if buyers[i] == t) \
                - pulp.lpSum(amounts[i] * x[i] for i in range(n) if sellers[i] == t)
            prob.addConstraint(K * pos_t <= margin * sum_of_amounts)
        

        prob.setSolver(pulp.PULP_CBC_CMD(msg=0))
        status = prob.solve()

        if pulp.LpStatus[status] == "Optimal":
            chosen_indices = [i for i in range(n) if pulp.value(x[i]) > 0.5]
            break 
    if len(chosen_indices) > 1:
        trades.loc[chosen_indices, "is_wash_trade"] = True
    return trades

def detect_and_label_wash_trades_using_volume_matching(trades, margin = 0.1):
    # TODO: double check index to avoid off by one error
    # TODO: check buyer vs seller: track flow of usdc position or token position?
    
    # print("start volume matching")

    # track usdc position
    buyers = trades["token_seller_id"].tolist()
    sellers = trades["token_buyer_id"].tolist()
    amounts = trades["usdc_amount"].tolist()

    # track token position
    # buyers = trades["token_buyer_id"].tolist()
    # sellers = trades["token_seller_id"].tolist()
    # amounts = trades["token_amount"].tolist()

    trader_position = {}

    for i in range(trades.shape[0]):
        trader_position[buyers[i]] = trader_position.get(buyers[i], 0) + amounts[i]
        trader_position[sellers[i]] = trader_position.get(sellers[i], 0) - amounts[i]
    
    # print(trader_balance)
    # print("start second loop")

    n = trades.shape[0] - 1
    while n >= 0:
        # print(n)
        # print(trades)
        position_list = [value for _, value in trader_position.items()]
        margin_mean_trade_volume = (sum(amounts[0:n+1]) / len(amounts[0:n+1])) * margin # update mean margin volume with last trade removed
        position_within_margin = [p <= margin_mean_trade_volume for p in position_list]
        if all(position_within_margin):
            trades["is_wash_trade"].iloc[range(0, n + 1)] = True
            # print(trades)
            return trades
       
        # update positions
        trader_position[buyers[n]] -= amounts[n]
        trader_position[sellers[n]] += amounts[n]

        n -= 1
    return trades

def get_wash_trades_summary(wash_trades, save=True):
    summary = pd.DataFrame(columns = ["scc_hash", "token_id", "window_size", "interval", "total_wash_trades", "total_wash_amount", "total_scc_trades", "total_trade_amount"], dtype=str)
    for scc_id, window_sizes in tqdm(wash_trades.items(), "generating summary"):
        for window_size, trades in window_sizes.items():  
            for trade in trades:  
                # print(trade)
                summary.loc[summary.shape[0]] = [scc_id, trade["token_id"].iloc[0],
                                                  window_size, trade["interval"].iloc[0], 
                                                  trade[trade["is_wash_trade"] == True].shape[0], 
                                                  trade[trade["is_wash_trade"] == True]["usdc_amount"].sum(),
                                                  trade.shape[0], trade["usdc_amount"].sum()]
                # summary["total_wash_amount"] = trade[trade["is_wash_trade"] == True]["token_amount"].sum()
                # print("end of inner most loop")
        summary_filtered = summary[summary["total_wash_trades"] > 0]
    if save:
        summary_filtered.to_csv(os.path.join(os.path.dirname(__file__),"./output/wash_trades_summary.csv"), index=False)

def get_sequence(start, stop, step):
    seq = list(range(start, stop+1, step))
    if seq[-1] != stop:
        seq.append(stop+1)
    return seq


# ------ run the algorithm ------
trades = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/split_1_preprocessed.csv"))
trades = restructure_trades(trades)

trades, self_trades = filter_self_trades(trades)

trades = add_trader_hashes(trades)
scc_dt = detect_scc_for_tokens(trades)
repeated_scc = get_repeated_scc(scc_dt, 2) # threshold = 2
# trades = detect_and_label_wash_trades_for_scc_for_single_time_window(trades, relevant_scc, 600, None, 0.1)
trades, wash_trades = detect_and_label_wash_trades_for_scc_with_multiple_time_windows(trades, repeated_scc, [600], None, 0.1, True)
get_wash_trades_summary(wash_trades)

# save to file
trades.to_csv(os.path.join(os.path.dirname(__file__), "./output/trades_labeled.csv"), index=False)
trades[trades["is_wash_trade"] == True].to_csv(os.path.join(os.path.dirname(__file__), "./output/wash_trades_labeled.csv"), index=False)
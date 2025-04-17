# import warnings
# warnings.simplefilter(action='ignore', category=Warning)
import pandas as pd
import json
import os

df = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/test.csv"))

# only keep mints and merge trades, exclude "normal" trades between traders
# this will also include the trade with against the exchange (taker = 0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E) in each txn
# amounts for the trade against the exchange will be adjusted to get rid of other orders that are not mints and merges
trades = []

for _, group in df.groupby("transactionHash"):
    exchange_is_taker = group["taker"] == "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
    order_against_exchange = group[exchange_is_taker]

    # only consider txns with 1 trade against the exchange
    if order_against_exchange.shape[0] == 1:
        maker_asset_id = order_against_exchange.iloc[0]["makerAssetId"]
        taker_asset_id = order_against_exchange.iloc[0]["takerAssetId"]

        maker_against_exchange = order_against_exchange.iloc[0]["maker"]
        asset_id_against_exchange = maker_asset_id if maker_asset_id != "0" else taker_asset_id
        maker_amount_against_exchange = order_against_exchange.iloc[0]["makerAmountFilled"]
        taker_amount_against_exchange = order_against_exchange.iloc[0]["takerAmountFilled"]

        normal_orders = group[
            (group["taker"] == maker_against_exchange) &
            ((group["makerAssetId"] == asset_id_against_exchange) | (group["takerAssetId"] == asset_id_against_exchange))
        ]

        # if there's only normal orders, skip this txn
        if (normal_orders.shape[0] != 0) and (normal_orders.shape[0] + order_against_exchange.shape[0] == group.shape[0]):
            continue
        # if there's no normal orders, check asset id and add entire txn
        elif (normal_orders.shape[0] == 0) and (group.shape[0] != 0):
            # other_orders = group[group["taker"] != "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"]
            # cond_1 = (other_orders["makerAssetId"]) != (asset_id_against_exchange & other_orders["makerAssetId"] != "0") & (other_orders["takerAssetId"] == "0")
            # cond_2 = (other_orders["takerAssetId"]) != (asset_id_against_exchange & other_orders["takerAssetId"] != "0") & (other_orders["makerAssetId"] == "0")
            # if other_orders.all(cond_1 and cond_2):
            #     trades.append(group)
            trades.append(group)
        # if there are normal order and mint/merge, adjust amount for mint/merge and add them to trades

        # ASSUMPTION: 
        # when there are both normal orders and mint/merge in a txn
        # all normal orders will have the same token id, and it will be 
        # different from the token id of the order against the exchange
        else:
            normal_maker_asset_id = normal_orders.iloc[0]["makerAssetId"]
            normal_taker_asset_id = normal_orders.iloc[0]["takerAssetId"]

            asset_id_normal_orders = normal_maker_asset_id if normal_maker_asset_id != "0" else normal_taker_asset_id
            normal_order_token_amount = 0
            normal_order_usdc_amount = 0
            for _, row in normal_orders.iterrows():
                if row["makerAssetId"] == "0":
                    normal_order_usdc_amount += row["makerAmountFilled"]
                    normal_order_token_amount += row["takerAmountFilled"]
                if row["takerAssetId"] == "0":
                    normal_order_token_amount += row["makerAmountFilled"]
                    normal_order_usdc_amount += row["takerAmountFilled"]
            
            if order_against_exchange.iloc[0]["makerAssetId"] != "0":
                group.loc[exchange_is_taker,"makerAmountFilled"] -= normal_order_token_amount
                group.loc[exchange_is_taker,"takerAmountFilled"] -= normal_order_usdc_amount
            else:
                group.loc[exchange_is_taker,"makerAmountFilled"] -= normal_order_usdc_amount
                group.loc[exchange_is_taker,"takerAmountFilled"] -= normal_order_token_amount
            
            if (group.loc[exchange_is_taker,"makerAmountFilled"].iloc[0] > 0) and (group.loc[exchange_is_taker,"takerAmountFilled"].iloc[0] > 0):
                trades.append(group.loc[~group.index.isin(normal_orders.index)])
            else:
                continue
res = pd.concat(trades, ignore_index=True)


# tag trades with additional market info
markets = os.path.join(os.path.dirname(__file__),"./data/markets.json")
with open(markets, "r") as f:
    market_data = json.load(f)

res["question"] = None
res["conditionId"] = None
for m in market_data:
    try:
        clob_token_ids = json.loads(m["clobTokenIds"])
        cond = res["makerAssetId"].isin(clob_token_ids) | res["takerAssetId"].isin(clob_token_ids)
        res.loc[cond,"question"] = m["question"]
        res.loc[cond,"conditionId"] = m["conditionId"]
    except KeyError as e:
        continue

res.to_csv(os.path.join(os.path.dirname(__file__), "./data/test_preprocessed_mint_and_merge.csv"), index=False)
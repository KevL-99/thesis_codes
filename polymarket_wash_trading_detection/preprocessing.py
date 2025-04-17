import pandas as pd
import json
import os

df = pd.read_csv(os.path.join(os.path.dirname(__file__),"./data/polymarket_OrderFilled.csv"))

# only keep "normal" trades, exclude mints and merges
# mints and merges should not affect the relative position a wash trader holds during a wash
trades = []

for _, group in df.groupby("transactionHash"):
    order_against_exchange = group[group["taker"] == "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"]

    if not order_against_exchange.empty:
        maker = order_against_exchange.iloc[0]["maker"]
        maker_asset_id = order_against_exchange.iloc[0]["makerAssetId"]
        taker_asset_id = order_against_exchange.iloc[0]["takerAssetId"]
        
        asset_id = maker_asset_id if maker_asset_id != "0" else taker_asset_id
        normal_orders = group[
            (group["taker"] == maker) &
            ((group["makerAssetId"] == asset_id) | (group["takerAssetId"] == asset_id))
        ]
        print(normal_orders.shape[0])
        trades.append(normal_orders)
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

res.to_csv(os.path.join(os.path.dirname(__file__), "./data/polymarket_OrderFilled_preprocessed.csv"), index=False)
This folder contains all scripts needed for Polymarket wash trading detection

### Folder Structure
- `data`: folder where the raw and preprocessed datasets are stored.
- `output`: folder where the detection results are stored.
  - `plots`: folder where the plots for quantification are stored.

### How to Run
1. place `polymarket_OrderFilled.csv` in `data`
2. run `get_market_info.py` to generate `markets.json` in `data`
3. run `preprocessing.py` and `preprocessing_mint_merge.py` to preprocess datasets, preprocessed datasets will be placed in `data`
4. run `wash_trading_detection.py` to detect wash trading for normal orders
5. run `wash_trading_detection_mint_merge.py` to detect wash trading for mints and merges
6. run `wash_trading_quantification.py` to generate plots and metrics.

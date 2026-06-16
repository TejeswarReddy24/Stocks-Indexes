import datetime
import os
import requests
import yfinance as yf
from jinja2 import Template

NSE_INDEXES = [
    {"label": "NIFTY 50", "api_name": "NIFTY 50"},
    {"label": "NIFTY NEXT 50", "api_name": "NIFTY NEXT 50"},
    {"label": "NIFTY MIDCAP 150", "api_name": "NIFTY MIDCAP 150"},
    {"label": "NIFTY SMALLCAP 100 (closest available)", "api_name": "NIFTY SMALLCAP 100"},
    {"label": "NIFTY BANK", "api_name": "NIFTY BANK"},
    {"label": "NIFTY IT", "api_name": "NIFTY IT"},
    {"label": "NIFTY 100", "api_name": "NIFTY 100"},
    {"label": "NIFTY FINANCIAL SERVICES", "api_name": "NIFTY FINANCIAL SERVICES"},
    {"label": "NIFTY SMALLCAP 250", "api_name": "NIFTY SMALLCAP 250"},
    {"label": "NIFTY MIDSMALLCAP 400", "api_name": "NIFTY MIDSMALLCAP 400"},
    {"label": "NIFTY COMMODITIES", "api_name": "NIFTY COMMODITIES"},
    {"label": "NIFTY FMCG", "api_name": "NIFTY FMCG"},
    {"label": "NIFTY PHARMA", "api_name": "NIFTY PHARMA"},
    {"label": "NIFTY AUTO", "api_name": "NIFTY AUTO"},
    {"label": "NIFTY METAL", "api_name": "NIFTY METAL"},
    {"label": "NIFTY ENERGY", "api_name": "NIFTY ENERGY"},
    {"label": "NIFTY INFRASTRUCTURE", "api_name": "NIFTY INFRASTRUCTURE"},
    {"label": "NIFTY REALTY", "api_name": "NIFTY REALTY"},
]

STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "NTPC.NS",
]

# ETFs we want to treat as stocks (show on stock table)
ETF_SYMBOLS = [
    "GOLDBEES.NS",   # Nippon India Gold BeES (ETF)
    "SILVERBEES.NS", # Nippon India Silver BeES (ETF)
]

# NIFTY 50 constituents (as of 2024)
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "HDFC.NS", "ITC.NS", "SBIN.NS", "WIPRO.NS", "MARUTI.NS",
    "LT.NS", "BAJAJ-AUTO.NS", "ASIANPAINT.NS", "TECHM.NS", "HCLTECH.NS",
    "SUNPHARMA.NS", "ULTRACEMCO.NS", "NTPC.NS", "POWERGRID.NS", "HEROMOTOCO.NS",
    "BHARTIARTL.NS", "DRREDDY.NS", "BAJAJFINSV.NS", "JSWSTEEL.NS", "ADANIPORTS.NS",
    "TATAMOTORS.NS", "BAJAJ-FSL.NS", "CIPLA.NS", "EICHERMOT.NS", "ADANIGREEN.NS",
    "GRASIM.NS", "SBILIFE.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDIGO.NS",
    "BEL.NS", "ONGC.NS", "COALINDIA.NS", "TATASTEEL.NS", "NESTLEIND.NS",
    "M&M.NS", "SHRIRAMFIN.NS", "LTIM.NS", "DLF.NS", "IDFCFIRSTB.NS",
    "STARTECH.NS", "LUPIN.NS", "AUROPHARMA.NS", "BANKBARODA.NS", "BPCL.NS",
]

# Thresholds for buy/sell signals (percentage from 52W low/high)
BUY_SIGNAL_THRESHOLD = 7.0    # Within 7% of 52W low = BUY signal
SELL_SIGNAL_THRESHOLD = 5.0   # Within 5% of 52W high = SELL signal

# Friendly display names for symbols that use BSE scheme codes or unclear names
SYMBOL_LABELS = {
    "GOLDBEES.NS": "Nippon India ETF - Gold BeES (ETF)",
    "SILVERBEES.NS": "Nippon India ETF - Silver BeES (ETF)",
    "NEXT50ETF.NS": "Kotak Next 50 (Index Fund - Growth)",
    "MID150.NS": "Kotak Midcap 150 (Index Fund - Growth)",
    "0P00005WL6.BO": "UTI Nifty 50 Index Fund (Growth)",
    "0P0001KR2S.BO": "Kotak Smallcap 250 (Growth)",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(BASE_DIR, "dashboard_template.html")
OUTPUT_DIR = os.path.join(BASE_DIR, "public")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_nse_index_data():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://www.nseindia.com", timeout=15)
    response = session.get("https://www.nseindia.com/api/allIndices", timeout=15)
    response.raise_for_status()
    return response.json().get("data", [])


def find_index_item(all_data, index_name):
    for item in all_data:
        if item.get("index") == index_name or item.get("indexSymbol") == index_name:
            return item
    return None


def safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def format_index_rows(raw_data):
    rows = []
    for config in NSE_INDEXES:
        item = find_index_item(raw_data, config["api_name"])
        if item is None:
            rows.append({
                "label": config["label"],
                "last": 0.0,
                "year_high": 0.0,
                "year_low": 0.0,
                "down_from_high": 0.0,
                "up_from_low": 0.0,
                "percent_change": 0.0,
            })
            continue

        last = safe_float(item.get("last"))
        year_high = safe_float(item.get("yearHigh"))
        year_low = safe_float(item.get("yearLow"))

        down_from_high = ((year_high - last) / year_high * 100.0) if year_high else 0.0
        up_from_low = ((last - year_low) / year_low * 100.0) if year_low else 0.0

        rows.append({
            "label": config["label"],
            "last": last,
            "year_high": year_high,
            "year_low": year_low,
            "down_from_high": down_from_high,
            "up_from_low": up_from_low,
            "percent_change": safe_float(item.get("percentChange")),
        })
    return rows


def fetch_stock_rows():
    rows = []
    # include ETFs in the stock table
    all_stock_symbols = STOCKS + ETF_SYMBOLS
    for symbol in all_stock_symbols:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        last = safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
        high_52w = safe_float(info.get("fiftyTwoWeekHigh"))
        low_52w = safe_float(info.get("fiftyTwoWeekLow"))

        down_from_high = ((high_52w - last) / high_52w * 100.0) if high_52w else 0.0
        up_from_low = ((last - low_52w) / low_52w * 100.0) if low_52w else 0.0

        # friendly name: prefer SYMBOL_LABELS, else use ticker info
        name = SYMBOL_LABELS.get(symbol) or info.get("shortName") or info.get("longName") or symbol

        rows.append({
            "symbol": symbol,
            "name": name,
            "last": last,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "down_from_high": down_from_high,
            "up_from_low": up_from_low,
        })
    return rows


def fetch_nifty50_signals():
    """Fetch NIFTY 50 stocks and identify buy/sell signals."""
    buy_signals = []
    sell_signals = []

    for symbol in NIFTY_50_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            last = safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
            high_52w = safe_float(info.get("fiftyTwoWeekHigh"))
            low_52w = safe_float(info.get("fiftyTwoWeekLow"))

            if last == 0 or high_52w == 0 or low_52w == 0:
                continue

            down_from_high = ((high_52w - last) / high_52w * 100.0) if high_52w else 0.0
            up_from_low = ((last - low_52w) / low_52w * 100.0) if low_52w else 0.0

            name = info.get("shortName") or info.get("longName") or symbol

            # Buy signal: stock is close to 52W low
            if up_from_low <= BUY_SIGNAL_THRESHOLD:
                buy_signals.append({
                    "symbol": symbol,
                    "name": name,
                    "type": "Stock",
                    "last": last,
                    "low_52w": low_52w,
                    "up_from_low": up_from_low,
                })

            # Sell signal: stock is close to 52W high
            if down_from_high <= SELL_SIGNAL_THRESHOLD:
                sell_signals.append({
                    "symbol": symbol,
                    "name": name,
                    "type": "Stock",
                    "last": last,
                    "high_52w": high_52w,
                    "down_from_high": down_from_high,
                })
        except Exception as e:
            # Skip if we can't fetch data for this symbol
            pass

    # Sort by how close to low/high
    buy_signals.sort(key=lambda x: x["up_from_low"])
    sell_signals.sort(key=lambda x: x["down_from_high"])

    return buy_signals, sell_signals


def fetch_etf_signals():
    """Fetch Gold/Silver ETF signals."""
    buy_signals = []
    sell_signals = []

    for symbol in ETF_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            last = safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
            high_52w = safe_float(info.get("fiftyTwoWeekHigh"))
            low_52w = safe_float(info.get("fiftyTwoWeekLow"))

            if last == 0 or high_52w == 0 or low_52w == 0:
                continue

            down_from_high = ((high_52w - last) / high_52w * 100.0) if high_52w else 0.0
            up_from_low = ((last - low_52w) / low_52w * 100.0) if low_52w else 0.0

            name = SYMBOL_LABELS.get(symbol) or info.get("shortName") or info.get("longName") or symbol

            # Buy signal: ETF is close to 52W low
            if up_from_low <= BUY_SIGNAL_THRESHOLD:
                buy_signals.append({
                    "symbol": symbol,
                    "name": name,
                    "type": "ETF",
                    "last": last,
                    "low_52w": low_52w,
                    "up_from_low": up_from_low,
                })

            # Sell signal: ETF is close to 52W high
            if down_from_high <= SELL_SIGNAL_THRESHOLD:
                sell_signals.append({
                    "symbol": symbol,
                    "name": name,
                    "type": "ETF",
                    "last": last,
                    "high_52w": high_52w,
                    "down_from_high": down_from_high,
                })
        except Exception as e:
            pass

    return buy_signals, sell_signals


def fetch_index_signals(raw_index_data):
    """Fetch Index signals from NSE data."""
    buy_signals = []
    sell_signals = []

    for config in NSE_INDEXES:
        item = find_index_item(raw_index_data, config["api_name"])
        if item is None:
            continue

        last = safe_float(item.get("last"))
        year_high = safe_float(item.get("yearHigh"))
        year_low = safe_float(item.get("yearLow"))

        if last == 0 or year_high == 0 or year_low == 0:
            continue

        down_from_high = ((year_high - last) / year_high * 100.0) if year_high else 0.0
        up_from_low = ((last - year_low) / year_low * 100.0) if year_low else 0.0

        # Buy signal: index is close to 52W low
        if up_from_low <= BUY_SIGNAL_THRESHOLD:
            buy_signals.append({
                "symbol": config["api_name"],
                "name": config["label"],
                "type": "Index",
                "last": last,
                "low_52w": year_low,
                "up_from_low": up_from_low,
            })

        # Sell signal: index is close to 52W high
        if down_from_high <= SELL_SIGNAL_THRESHOLD:
            sell_signals.append({
                "symbol": config["api_name"],
                "name": config["label"],
                "type": "Index",
                "last": last,
                "high_52w": year_high,
                "down_from_high": down_from_high,
            })

    return buy_signals, sell_signals


def render_html(indices, stocks, buy_signals, sell_signals):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as fd:
        template = Template(fd.read())

    return template.render(
        updated=datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        indices=indices,
        stocks=stocks,
        buy_signals=buy_signals,
        sell_signals=sell_signals,
    )


def main():
    raw_index_data = fetch_nse_index_data()
    index_rows = format_index_rows(raw_index_data)
    stock_rows = fetch_stock_rows()
    
    # Fetch all signals
    nifty50_buy, nifty50_sell = fetch_nifty50_signals()
    etf_buy, etf_sell = fetch_etf_signals()
    index_buy, index_sell = fetch_index_signals(raw_index_data)
    
    # Merge all signals
    all_buy_signals = nifty50_buy + etf_buy + index_buy
    all_sell_signals = nifty50_sell + etf_sell + index_sell
    
    # Sort by proximity
    all_buy_signals.sort(key=lambda x: x["up_from_low"])
    all_sell_signals.sort(key=lambda x: x["down_from_high"])
    
    html = render_html(index_rows, stock_rows, all_buy_signals, all_sell_signals)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fd:
        fd.write(html)

    print(f"Dashboard generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

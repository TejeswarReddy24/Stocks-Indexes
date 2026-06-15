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


def render_html(indices, stocks):
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as fd:
        template = Template(fd.read())

    return template.render(
        updated=datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        indices=indices,
        stocks=stocks,
    )


def main():
    raw_index_data = fetch_nse_index_data()
    index_rows = format_index_rows(raw_index_data)
    stock_rows = fetch_stock_rows()
    html = render_html(index_rows, stock_rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fd:
        fd.write(html)

    print(f"Dashboard generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

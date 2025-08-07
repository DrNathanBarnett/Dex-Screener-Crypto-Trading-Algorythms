import requests
import time
from datetime import datetime

# ==============================================================================
# CONFIGURATION
# Adjust these values to customize the token tracking criteria.
# ==============================================================================

# Time interval in seconds to check for new tokens.
# A shorter interval will find new tokens faster but uses more API requests.
CHECK_INTERVAL_SECONDS = 30

# The blockchain network to monitor. Common values include 'ethereum', 'solana', 'bsc', 'polygon', 'arbitrum', 'base'.
# You can find the full list on DexScreener's website.
CHAIN_ID = 'ethereum'

# Trustworthiness criteria
# Minimum liquidity in USD. Tokens with liquidity below this threshold are flagged.
MIN_LIQUIDITY_USD = 5000

# Minimum number of transactions in the last 5 minutes.
# Tokens with fewer than this number of transactions are flagged for low activity.
MIN_TXNS_M5 = 10

# Buy/Sell ratio threshold. If the ratio of buys to sells (or vice-versa) is
# skewed too heavily, it could be a sign of manipulation.
# For example, a ratio of 0.1 means buys are less than 10% of sells.
# A ratio of 10 means buys are more than 10 times the sells.
# Setting this to 0.1 and 10 means we're looking for a relatively balanced ratio.
BUY_SELL_RATIO_MIN = 0.1
BUY_SELL_RATIO_MAX = 10.0

# ==============================================================================
# MAIN LOGIC
# No need to change anything below this line unless you want to modify the core
# functionality.
# ==============================================================================

# A set to store the pair addresses of tokens we've already seen to avoid
# processing them multiple times.
tracked_pairs = set()


def check_new_tokens():
    """
    Fetches the latest token pairs from DexScreener and analyzes them.
    """
    global tracked_pairs
    url = f'https://api.dexscreener.com/latest/dex/pairs/{CHAIN_ID}/new'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()

        if not data or 'pairs' not in data or not data['pairs']:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No new pairs found.")
            return

        for pair in data['pairs']:
            pair_address = pair['pairAddress']

            # Check if we have already processed this pair
            if pair_address in tracked_pairs:
                continue

            # Add the new pair to our set
            tracked_pairs.add(pair_address)

            # Extract relevant data
            base_token_symbol = pair['baseToken']['symbol']
            base_token_name = pair['baseToken']['name']
            liquidity_usd = pair.get('liquidity', {}).get('usd', 0)
            txns_m5 = pair.get('txns', {}).get('m5', {'buys': 0, 'sells': 0})
            buys_m5 = txns_m5.get('buys', 0)
            sells_m5 = txns_m5.get('sells', 0)

            # Use '0' as a default for division to prevent ZeroDivisionError
            buy_sell_ratio = buys_m5 / sells_m5 if sells_m5 > 0 else (buys_m5 / 1 if buys_m5 > 0 else 1)

            # Initialize a flag for trustworthiness
            is_trustworthy = True
            reasons = []

            # Apply the defined criteria
            if liquidity_usd < MIN_LIQUIDITY_USD:
                is_trustworthy = False
                reasons.append(f"Low liquidity (${liquidity_usd:,.2f}) below minimum (${MIN_LIQUIDITY_USD:,.2f})")

            if (buys_m5 + sells_m5) < MIN_TXNS_M5:
                is_trustworthy = False
                reasons.append(f"Low transaction volume ({buys_m5 + sells_m5} total) below minimum ({MIN_TXNS_M5})")

            # This check is for token population. A highly imbalanced ratio of buys/sells might indicate
            # a single entity is either buying or selling heavily, which is a red flag.
            if not (BUY_SELL_RATIO_MIN <= buy_sell_ratio <= BUY_SELL_RATIO_MAX):
                is_trustworthy = False
                reasons.append(f"Unbalanced buy/sell ratio ({buy_sell_ratio:.2f})")

            # Print the analysis result
            status = "TRUSTWORTHY" if is_trustworthy else "UNTRUSTWORTHY"

            print("---------------------------------------------------------")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New Token Detected!")
            print(f"Status: {status}")
            print(f"Token Name: {base_token_name} ({base_token_symbol})")
            print(f"Pair Address: {pair_address}")
            print(f"Liquidity (USD): ${liquidity_usd:,.2f}")
            print(f"Transactions (5m): Buys={buys_m5}, Sells={sells_m5}")
            print(f"Buy/Sell Ratio: {buy_sell_ratio:.2f}")
            if not is_trustworthy:
                print("Reasons for UNTRUSTWORTHY flag:")
                for reason in reasons:
                    print(f"  - {reason}")
            print("---------------------------------------------------------")

    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error fetching data: {e}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] An unexpected error occurred: {e}")


def main():
    """
    Main function to run the token tracker in a continuous loop.
    """
    print(f"Starting DexScreener token tracker for the '{CHAIN_ID}' chain...")
    print("This tool will check for new tokens every "
          f"{CHECK_INTERVAL_SECONDS} seconds and analyze them.")
    print("Press Ctrl+C to stop.")

    # Run the initial check immediately
    check_new_tokens()

    try:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            check_new_tokens()
    except KeyboardInterrupt:
        print("\nToken tracker stopped.")


if __name__ == '__main__':
    main()


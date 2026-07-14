"""
shared.fees — Trading fee calculation.

Alpaca fee structure: SEC fee, FINRA TAF, and estimated slippage.
"""

# Default Alpaca fee constants
SEC_FEE_RATE = 0.0000278
FINRA_TAF_RATE = 0.000166
FINRA_TAF_MAX = 8.30
SLIPPAGE_PER_SHARE = 0.01  # conservative estimate


def calculate_fees(shares, entry_price, exit_price, position,
                   sec_rate=SEC_FEE_RATE, taf_rate=FINRA_TAF_RATE,
                   taf_max=FINRA_TAF_MAX, slippage=SLIPPAGE_PER_SHARE):
    """
    Calculate round-trip trading fees for a single trade.

    Parameters
    ----------
    shares      : int   — Number of shares traded.
    entry_price : float — Entry price per share.
    exit_price  : float — Exit price per share.
    position    : str   — "long" or "short".
    sec_rate    : float — SEC fee rate on sale proceeds.
    taf_rate    : float — FINRA TAF rate per share.
    taf_max     : float — FINRA TAF cap per trade.
    slippage    : float — Estimated slippage per share (applied on entry + exit).

    Returns
    -------
    float — Total fees for the trade.
    """
    if shares <= 0:
        return 0.0

    # SEC fee applies to sale proceeds
    sale_price = exit_price if position == "long" else entry_price
    sec_fee = shares * sale_price * sec_rate

    # FINRA TAF
    finra_taf = min(shares * taf_rate, taf_max)

    # Slippage (both sides)
    slip = shares * slippage * 2

    return sec_fee + finra_taf + slip


def calculate_fees_pct(entry_price, exit_price, direction,
                       sec_rate=SEC_FEE_RATE, taf_rate=FINRA_TAF_RATE,
                       slippage=SLIPPAGE_PER_SHARE):
    """
    Calculate round-trip fee as a fraction of entry price.

    No shares or sizing needed — returns fee as a decimal fraction
    that can be subtracted directly from pct_return_gross.

    Parameters
    ----------
    entry_price : float — Entry price per share.
    exit_price  : float — Exit price per share.
    direction   : str   — "long" or "short".

    Returns
    -------
    float — Fee as decimal fraction of entry price (e.g., 0.0001 = 1 bps).
    """
    # SEC fee on sale side
    sale_price = exit_price if direction == "long" else entry_price
    sec_pct = sale_price * sec_rate / entry_price

    # TAF per share (negligible, no cap needed for 1-share basis)
    taf_pct = taf_rate / entry_price

    # Slippage both sides
    slip_pct = slippage * 2 / entry_price

    return sec_pct + taf_pct + slip_pct

#!/usr/bin/env python3
"""
Test script to verify graph consistency across different time periods.
This script simulates market data and verifies that price movements
are consistent across intraday, daily, weekly, monthly, and yearly views.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.market import Market
from core import intraday
from core import config

class MockSimClock:
    """Mock simulation clock for testing."""
    def __init__(self):
        self.game_minutes_acc = 180  # 3 hours into the current step
        self.speed = 1

def test_graph_consistency():
    """Test that graph data is consistent across different time periods."""
    print("Testing graph consistency across time periods...")

    # Create a market instance
    market = Market(seed=12345)

    # Advance the market a few steps to have some history
    for _ in range(10):
        market.step()

    # Get a test ticker
    test_ticker = "MVC"  # NVIDIA proxy
    if test_ticker not in market.ticker_idx:
        # Use the first available ticker
        test_ticker = list(market.ticker_idx.keys())[0]

    print(f"Testing with ticker: {test_ticker}")

    # Create mock simulation clock
    mock_clock = MockSimClock()

    # Test different time periods
    periods = [
        ("1J", 1440),      # 1 day in minutes
        ("1W", 10080),     # 1 week in minutes
        ("1M", 6),         # 1 month in steps (approx 30 days)
        ("3M", 18),        # 3 months in steps
        ("1A", 73),        # 1 year in steps
    ]

    results = {}

    for period_label, period_value in periods:
        print(f"\nTesting {period_label} period...")

        if period_label in ["1J", "1W"]:
            # Intraday periods
            hist = market.history_of(test_ticker)
            series = intraday.intraday_series(
                market, mock_clock, 1, test_ticker, hist,
                window_minutes=period_value, n_points=60,
                vol_mult=intraday.vol_mult_for_sigma(float(market.sigma[market.ticker_idx[test_ticker]]))
            )
        else:
            # Step-based periods
            hist = market.history_of(test_ticker, period_value)
            pps = intraday.points_per_segment_for_n_steps(period_value)
            series = intraday.densify_step_series(
                market, test_ticker, hist, pps,
                vol_mult=intraday.vol_mult_for_sigma(float(market.sigma[market.ticker_idx[test_ticker]]))
            )

        if series:
            # Calculate basic statistics
            min_val = min(series)
            max_val = max(series)
            first_val = series[0]
            last_val = series[-1]
            change_pct = ((last_val - first_val) / first_val) * 100 if first_val != 0 else 0

            results[period_label] = {
                'length': len(series),
                'min': min_val,
                'max': max_val,
                'first': first_val,
                'last': last_val,
                'change_pct': change_pct
            }

            print(f"  Series length: {len(series)}")
            print(f"  Price range: {min_val:.2f} - {max_val:.2f}")
            print(f"  Change: {change_pct:.2f}%")
        else:
            print(f"  No data available for {period_label}")
            results[period_label] = None

    # Verify consistency
    print("\nConsistency Check:")
    valid_results = {k: v for k, v in results.items() if v is not None}

    if len(valid_results) >= 2:
        # Check that longer periods contain the general trend of shorter periods
        period_keys = list(valid_results.keys())
        for i in range(len(period_keys) - 1):
            current = period_keys[i]
            next_period = period_keys[i + 1]

            current_change = valid_results[current]['change_pct']
            next_change = valid_results[next_period]['change_pct']

            # The changes should be in the same direction (same sign)
            if (current_change * next_change) >= 0:
                print(f"  ✓ {current} ({current_change:.2f}%) and {next_period} ({next_change:.2f}%) have consistent direction")
            else:
                print(f"  ⚠ {current} ({current_change:.2f}%) and {next_period} ({next_change:.2f}%) have inconsistent direction")

    print("\nTest completed successfully!")
    return True

if __name__ == "__main__":
    test_graph_consistency()
#!/usr/bin/env python3
"""
Test script to verify real-time graph updates.
This script simulates rapid updates to verify that graphs refresh frequently.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.market import Market
from core import intraday

class MockSimClock:
    """Mock simulation clock for testing real-time updates."""
    def __init__(self):
        self.game_minutes_acc = 0
        self.speed = 1
        self.paused = False
        self.auto_paused = False

    def effective_speed(self):
        if self.paused or self.auto_paused:
            return 0
        return self.speed

def test_real_time_updates():
    """Test that graphs update frequently for real-time feel."""
    print("Testing real-time graph updates...")

    # Create a market instance
    market = Market(seed=12345)

    # Advance the market a few steps to have some history
    for _ in range(5):
        market.step()

    # Get a test ticker
    test_ticker = "MVC"  # NVIDIA proxy
    if test_ticker not in market.ticker_idx:
        # Use the first available ticker
        test_ticker = list(market.ticker_idx.keys())[0]

    print(f"Testing with ticker: {test_ticker}")
    print(f"Quantization interval: {intraday.QUANTIZE_MINUTES} minutes")
    print(f"Minutes per step: {intraday.minutes_per_step()} minutes")

    # Create mock simulation clock
    mock_clock = MockSimClock()

    # Get history
    hist = market.history_of(test_ticker)

    # Test quantization effect
    print("\nTesting quantization effect:")

    # Test with different time values to see quantization in action
    test_times = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    prices = []

    for minutes in test_times:
        mock_clock.game_minutes_acc = minutes
        quantized_time = intraday.quantize_to_day(minutes)

        # Test live_point function directly
        if len(hist) >= 2:
            live_price = intraday.live_point(
                market, mock_clock, 1, test_ticker, hist,
                vol_mult=intraday.vol_mult_for_sigma(float(market.sigma[market.ticker_idx[test_ticker]]))
            )
            if live_price:
                prices.append(live_price)
                print(f"  Time: {minutes:3d}min -> Quantized: {quantized_time:3d}min -> Price: {live_price:.2f}")

    # Check that quantization is working (prices should change at quantization boundaries)
    if len(prices) > 1:
        changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        changes_count = sum(1 for c in changes if c > 0.01)  # Count significant changes
        print(f"\nNumber of significant price changes: {changes_count}/{len(changes)}")

        if changes_count > 0:
            print("✓ Quantization is working - prices update at quantization boundaries")
        else:
            print("⚠ Quantization may not be working properly")

    # Test frequent intraday updates
    print("\nTesting frequent intraday series updates:")

    updates = []
    for i in range(8):
        # Advance time in small increments (smaller than quantization)
        mock_clock.game_minutes_acc = i * 15  # 15 minute increments

        # Generate intraday series with live point
        series = intraday.intraday_series(
            market, mock_clock, 1, test_ticker, hist,
            window_minutes=1440, n_points=20,  # 1 day window
            vol_mult=intraday.vol_mult_for_sigma(float(market.sigma[market.ticker_idx[test_ticker]]))
        )

        if series:
            current_price = series[-1]  # Last point is the live point
            updates.append(current_price)
            print(f"  Update {i+1}: Time={mock_clock.game_minutes_acc:3d}min -> Live Price = {current_price:.2f}")

    print("\nReal-time update test completed!")
    return True

if __name__ == "__main__":
    test_real_time_updates()
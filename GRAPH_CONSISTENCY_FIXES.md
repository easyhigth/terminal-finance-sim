# Graph Consistency Improvements - Summary

## Problem Identified
The graphs were showing inconsistent price movements across different time periods:
- Intraday periods (1J, 1W) were generated independently from step-based periods (1M, 3M, 1A, etc.)
- This led to situations where short-term movements contradicted longer-term trends
- Users couldn't see how daily movements fit into weekly/monthly/yearly trends

## Solution Implemented

### 1. Core Changes to `core/intraday.py`

#### Modified `intraday_series()` function:
- Now uses a representative sample of recent step history to establish trends
- Ensures intraday movements align with recent trends while maintaining realistic volatility
- Uses at least 5 steps to establish a trend for better consistency
- Adjusts volatility based on trend alignment - reduces volatility when moving against the trend

#### Modified `densify_step_series()` function:
- Improved trend alignment between local movements and overall period trends
- Adjusts volatility based on whether local movements align with the overall period trend
- Maintains the exact step closing prices while adding realistic intermediate points

#### Modified `_NOISE_PCT` parameter:
- Reduced from 0.0045 to 0.0035 to ensure better consistency across time scales
- Maintains visual dynamism while preventing excessive volatility that breaks consistency

### 2. Changes to `scenes/scene_graph.py`

#### Modified `_series()` method:
- Ensures intraday periods use sufficient historical data to establish proper context
- Calculates appropriate number of steps needed for intraday windows
- Maintains consistency between data sources for all period types

### 3. Changes to `core/market_query.py`

#### Modified `history_of()` method:
- Ensures consistent data availability for both intraday and step-based visualization
- Extends history with earliest available point when needed to maintain consistency

## Results

After implementing these changes, the test shows consistent directional movements across all time periods:

- 1J: -17.77%
- 1W: -17.77%
- 1M: -17.77%
- 3M: -26.63%
- 1A: -26.63%

This ensures that users can now clearly see how intraday movements contribute to longer-term trends, making the graphs much more realistic and educational.

## Key Benefits

1. **Consistency**: All time periods now show movements in the same direction when looking at the same underlying data
2. **Realism**: Intraday movements respect longer-term trends while maintaining realistic volatility
3. **Educational Value**: Users can better understand how short-term fluctuations contribute to longer-term performance
4. **Visual Coherence**: Graphs across different time scales now tell a consistent story
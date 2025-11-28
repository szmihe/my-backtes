import pandas as pd
from strategies.example_strategy import Strategy


def make_sample_df():
    data = {
        'date': ['2020-01-01','2020-01-02','2020-01-03','2020-01-04','2020-01-05','2020-01-06'],
        'open': [10,11,12,11,12,13],
        'high': [10,11,12,11,12,14],
        'low': [9,10,11,10,11,12],
        'close': [10,11,12,11,12,13],
        'volume': [100,200,300,400,500,600],
        'amount': [1000,2200,3600,4400,6000,7800]
    }
    return pd.DataFrame(data)


def test_example_signals():
    df = make_sample_df()
    strat = Strategy(short_window=2, long_window=3)
    s = strat.generate_signals(df)
    assert len(s) == len(df)
    # 确保信号值只包含 -1, 0, 1
    assert set(s.unique()) <= {-1, 0, 1}

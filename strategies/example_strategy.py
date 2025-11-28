"""
示例策略：简单移动平均交叉策略
- Strategy 类：实现 `generate_signals(df)`，df 包含列 ['date','open','high','low','close','volume','amount']
- 返回一个名为 'signal' 的 Series：1 表示买入，-1 表示卖出，0 表示空仓/不操作
"""

import pandas as pd

class Strategy:
    def __init__(self, short_window=5, long_window=20):
        self.short = short_window
        self.long = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if 'close' not in df.columns:
            raise ValueError('数据缺少 close 列')
        s = df['close'].astype(float)
        short_ma = s.rolling(self.short, min_periods=1).mean()
        long_ma = s.rolling(self.long, min_periods=1).mean()
        signal = pd.Series(0, index=df.index)
        signal[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1
        signal[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1
        return signal

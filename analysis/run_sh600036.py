"""
回测脚本: 招商银行 (sh600036)
回测日期：2020-01-01 - 2025-09-30
买入条件：当月收盘较最近16月最低价反弹超过9%，在下一个交易日开盘以开盘价买入
卖出条件：当日收盘 < 买入后最高收盘价 * 0.94 或 当日收盘 < 买入价 * 0.94 （当任一条件满足即卖出，卖出价为当日收盘价）

输出：CSV 导出包含每笔交易明细及收益，汇总总收益（按复利计算）
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

"""
回测脚本: 招商银行 (sh600036)
回测日期：2020-01-01 - 2025-09-30
买入条件：当月收盘较最近16月最低价反弹超过9%，在下一个交易日以开盘价买入
卖出条件：当日收盘 < 买入后最高收盘价 * 94% 或 当日收盘 < 买入价 * 94% （满足任一条件即卖出，卖出价为当日收盘价）
卖出后重新以卖出月为起始重新计算最低价，直到再次满足月末反弹9%则买入

输出：CSV 导出包含每笔交易明细及收益，汇总总收益（按复利计算）以及交易次数和胜率
"""

import os
import pandas as pd
import numpy as np

# 配置
CSV_PATH = '/Users/mic/Downloads/20250930/sh600036.csv'
OUT_DIR = 'outputs'
OUT_FILE = os.path.join(OUT_DIR, 'sh600036_trades.csv')
START_DATE = '2020-01-01'
END_DATE = '2025-09-30'
MIN_MONTHS = 16  # 初始计算所需的历史月数
REBATE_PCT = 0.09  # 9% 反弹
TRAIL_PCT = 0.94  # 94% 止损阈值

os.makedirs(OUT_DIR, exist_ok=True)


def load_df(csv_path):
    df = pd.read_csv(csv_path, parse_dates=['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df = df[(df['date'] >= pd.to_datetime(START_DATE)) & (df['date'] <= pd.to_datetime(END_DATE))].copy()
    return df


def get_monthly_close(df):
    df['month'] = df['date'].dt.to_period('M')
    m = df.groupby('month').agg({'date': 'max', 'close': 'last'})
    m.index = m.index.to_timestamp('M')
    m = m.sort_index()
    return m


def run_backtest(df):
    """实现按月末判断买入，并在持仓期间按日扫描卖出的逻辑。
    卖出后，以卖出月为起始重新计算最低价，直到再次满足月末反弹9%则买入。
    返回 trades 列表，每项为 dict 包含买、卖信息与收益。"""

    trades = []
    monthly = get_monthly_close(df)
    month_ends = monthly['date'].tolist()
    month_closes = monthly['close'].tolist()

    # Helper: find first trading day (pos) after given date
    def next_trade_pos_after(date):
        # find first index where daily date > date
        mask = df['date'] > date
        if mask.any():
            label_idx = mask[mask].index[0]
            return df.index.get_loc(label_idx)
        return None

    # Prepare month periods for mapping
    month_periods = [pd.Period(d, freq='M') for d in month_ends]

    position = False
    min_start_idx = None  # None means initial phase where we need 16 months history

    i = 0
    while i < len(month_ends):
        current_close = month_closes[i]
        # pick start index for min calculation
        if min_start_idx is None:
            if i < MIN_MONTHS - 1:
                i += 1
                continue
            start_idx = i - (MIN_MONTHS - 1)
        else:
            start_idx = min_start_idx

        min_close = min(month_closes[start_idx: i + 1])

        # if not in position and buy condition satisfied, buy on next trading day
        if (not position) and (current_close > min_close * (1 + REBATE_PCT)):
            next_pos = next_trade_pos_after(month_ends[i])
            if next_pos is not None:
                buy_pos = next_pos
                buy_date = df.iloc[buy_pos]['date']
                buy_price = float(df.iloc[buy_pos]['open'])
                peak_close = float(df.iloc[buy_pos]['close'])

                trades.append({
                    'buy_date': buy_date,
                    'signal_month_end': month_ends[i],
                    'buy_price': round(buy_price, 2),
                    'buy_pos': buy_pos,
                    'sell_date': None,
                    'sell_price': None,
                    'peak_close': round(peak_close, 2),
                    'return_pct': None,
                    'duration_days': None,
                })
                position = True
                # after buying, scan forward daily to find a sell
                t = trades[-1]
                sell_pos = None
                for j in range(buy_pos + 1, len(df)):
                    c = float(df.iloc[j]['close'])
                    if c > peak_close:
                        peak_close = c
                    # condition: close < peak_close * 0.94 or close < buy_price * 0.94
                    if (c < peak_close * TRAIL_PCT) or (c < buy_price * TRAIL_PCT):
                        sell_pos = j
                        break
                if sell_pos is not None:
                    sell_date = df.iloc[sell_pos]['date']
                    sell_price = float(df.iloc[sell_pos]['close'])
                    t['sell_date'] = sell_date
                    t['sell_price'] = round(sell_price, 2)
                    t['peak_close'] = round(peak_close, 2)
                    t['return_pct'] = round((sell_price / buy_price - 1) * 100, 2)
                    t['duration_days'] = int((sell_date - buy_date).days)
                    position = False
                    # set new min start index as sell month
                    sell_month = pd.Period(sell_date, freq='M').to_timestamp('M')
                    # find index of sell_month in month_ends list
                    found_idx = None
                    for k, d in enumerate(month_ends):
                        if pd.Period(d, freq='M').to_timestamp('M') == sell_month:
                            found_idx = k
                            break
                    if found_idx is None:
                        found_idx = len(month_ends) - 1
                    min_start_idx = found_idx
                    # move pointer to the sell month to continue from there
                    i = found_idx
                    continue
                else:
                    # no sell until end; close at last day
                    sell_pos = len(df) - 1
                    sell_date = df.iloc[sell_pos]['date']
                    sell_price = float(df.iloc[sell_pos]['close'])
                    t['sell_date'] = sell_date
                    t['sell_price'] = round(sell_price, 2)
                    t['peak_close'] = round(peak_close, 2)
                    t['return_pct'] = round((sell_price / buy_price - 1) * 100, 2)
                    t['duration_days'] = int((sell_date - buy_date).days)
                    position = False
                    sell_month = pd.Period(sell_date, freq='M').to_timestamp('M')
                    found_idx = None
                    for k, d in enumerate(month_ends):
                        if pd.Period(d, freq='M').to_timestamp('M') == sell_month:
                            found_idx = k
                            break
                    if found_idx is None:
                        found_idx = len(month_ends) - 1
                    min_start_idx = found_idx
                    i = found_idx
                    continue
        i += 1

    # Ensure all trades closed (safety), otherwise close at last day
    for t in trades:
        if t['sell_date'] is None:
            sell_pos = len(df) - 1
            sell_date = df.iloc[sell_pos]['date']
            sell_price = float(df.iloc[sell_pos]['close'])
            buy_price = t['buy_price']
            peak_close = float(df.iloc[t['buy_pos']]['close'])
            for j in range(t['buy_pos'] + 1, len(df)):
                c = float(df.iloc[j]['close'])
                if c > peak_close:
                    peak_close = c
            t['sell_date'] = sell_date
            t['sell_price'] = round(sell_price, 2)
            t['peak_close'] = round(peak_close, 2)
            t['return_pct'] = round((sell_price / buy_price - 1) * 100, 2)
            t['duration_days'] = int((sell_date - t['buy_date']).days)

    return trades


if __name__ == '__main__':
    df = load_df(CSV_PATH)
    if df.empty:
        raise SystemExit('在指定日期区间内未找到数据，请确认CSV和日期范围')
    trades = run_backtest(df)

    if not trades:
        print('在回测日期范围内未触发任何买入信号。')
    else:
        out_df = pd.DataFrame(trades)
        # Remove internal buy_pos
        if 'buy_pos' in out_df.columns:
            out_df = out_df.drop(columns=['buy_pos'])

        # 计算总收益（复利）
        total_prod = 1.0
        for r in out_df['return_pct']:
            total_prod *= (1 + (r / 100.0))
        total_ret_pct = round((total_prod - 1) * 100, 2)

        out_df['buy_date'] = pd.to_datetime(out_df['buy_date']).dt.strftime('%Y-%m-%d')
        out_df['sell_date'] = pd.to_datetime(out_df['sell_date']).dt.strftime('%Y-%m-%d')
        if 'signal_month_end' in out_df.columns:
            out_df['signal_month_end'] = pd.to_datetime(out_df['signal_month_end']).dt.strftime('%Y-%m-%d')

        out_df['buy_price'] = out_df['buy_price'].map(lambda x: float(f"{x:.2f}"))
        out_df['sell_price'] = out_df['sell_price'].map(lambda x: float(f"{x:.2f}"))
        out_df['peak_close'] = out_df['peak_close'].map(lambda x: float(f"{x:.2f}"))
        out_df['return_pct'] = out_df['return_pct'].map(lambda x: float(f"{x:.2f}"))

        # 交易次数、胜率
        trades_count = len(out_df)
        win_count = (out_df['return_pct'] > 0).sum()
        win_rate = round(win_count / trades_count * 100, 2) if trades_count > 0 else 0.0

        out_df.to_csv(OUT_FILE, index=False)

        # 打印输出
        print('交易明细:')
        print(out_df.to_string(index=False))
        print('\n汇总:')
        print(f'总交易次数: {trades_count}')
        print(f'胜率: {win_rate}%')
        print(f'合计收益(复利): {total_ret_pct}%')
        print(f'输出文件: {OUT_FILE}')

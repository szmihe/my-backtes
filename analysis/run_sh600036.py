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

# 配置
CSV_PATH = '/Users/mic/Downloads/20250930/sh600036.csv'
OUT_DIR = 'outputs'
OUT_FILE = os.path.join(OUT_DIR, 'sh600036_trades.csv')
START_DATE = '2020-01-01'
END_DATE = '2025-09-30'
MIN_MONTHS = 16  # 计算16月最低价
REBATE_PCT = 0.09  # 9% 反弹
TRAIL_PCT = 0.94  # 94% 止损阈值

os.makedirs(OUT_DIR, exist_ok=True)


def load_df(csv_path):
    df = pd.read_csv(csv_path, parse_dates=['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df = df[(df['date'] >= pd.to_datetime(START_DATE)) & (df['date'] <= pd.to_datetime(END_DATE))].copy()
    return df


def get_monthly_close(df):
    # 月度收盘为每月最后一个交易日的close
    df['month'] = df['date'].dt.to_period('M')
    m = df.groupby('month').agg({'date': 'max', 'close': 'last'})
    m.index = m.index.to_timestamp('M')
    m = m.sort_index()
    return m


def run_backtest(df):
    trades = []
    monthly = get_monthly_close(df)
    months = monthly.index

    position = False
    buy_price = None
    buy_date = None
    peak_close = None

    # Map the monthly event date to the next trading day in daily df
    month_to_next_trading_day = {}
    for _, row in monthly.iterrows():
        month_end_date = row['date']
        # find first trading day after month_end_date
        mask = df['date'] > month_end_date
        if mask.any():
            next_trade_date = df.loc[mask.idxmax(), 'date']
            # But be careful with idxmax weirdness: find the first index where date > month_end_date
            first_idx = mask[mask].index[0]
            next_trade_date = df.loc[first_idx, 'date']
            month_to_next_trading_day[month_end_date] = next_trade_date

    # For each month, compute prior MIN_MONTHS minima of monthly close
    for i in range(len(months)):
        current_month = months[i]
        current_close = monthly.loc[current_month, 'close']
        # check we have at least MIN_MONTHS history including current
        start_idx = max(0, i - (MIN_MONTHS - 1))
        # only evaluate if we have exactly MIN_MONTHS previous months (inclusive), otherwise skip
        if i - start_idx + 1 < MIN_MONTHS:
            continue
        lookback = monthly.iloc[start_idx:i+1]['close']
        min_16 = lookback.min()
        if current_close > min_16 * (1 + REBATE_PCT):
            # buy signal on next trading day after month end
            month_end_date = monthly.loc[current_month, 'date']
            if month_end_date not in month_to_next_trading_day:
                continue
            buy_dt = month_to_next_trading_day[month_end_date]
            # ensure buy date exists in df and within our date range
            row_buy_idx = df.index[df['date'] == buy_dt].tolist()
            if not row_buy_idx:
                continue
            buy_idx_label = row_buy_idx[0]
            buy_pos = df.index.get_loc(buy_idx_label)
            if not position:
                buy_date = df.iloc[buy_pos]['date']
                buy_price = float(df.iloc[buy_pos]['open'])  # 全仓按开盘价买入
                position = True
                peak_close = float(df.iloc[buy_pos]['close'])
                # record entry
                trades.append({
                    'buy_date': buy_date,
                    'buy_price': round(buy_price, 2),
                    'buy_pos': buy_pos,
                    'sell_date': None,
                    'sell_price': None,
                    'peak_close': round(peak_close, 2),
                    'return_pct': None,
                    'duration_days': None
                })
            # else: if already in position, ignore this buy

        # After buy, we should check every trading day for sell conditions until we close
        if position:
            # start scanning from the buy_idx+1 (or buy_idx if same day) until we encounter sell
            # but we must scan the days after the last recorded buy; we can simply iterate daily from buy_date index
            # maintain pointer to the buy trade
            pass

    # A simpler approach: after we collect buy dates, walk forward to find sells
    # Extract all buy events from trades (with None sell_date)
    # now iterate trades list and find sell dates one by one, scanning df forward
    i = 0
    while i < len(trades):
        t = trades[i]
        if t['sell_date'] is not None:
            i += 1
            continue
        buy_dt = t['buy_date']
        buy_price = t['buy_price']
        buy_pos = t.get('buy_pos')
        if buy_pos is None:
            buy_idx_label = df.index[df['date'] == buy_dt].tolist()[0]
            buy_pos = df.index.get_loc(buy_idx_label)
        peak_close = float(df.iloc[buy_pos]['close'])
        sell_idx = None
        for j in range(buy_pos + 1, len(df)):
            c = float(df.iloc[j]['close'])
            if c > peak_close:
                peak_close = c
            # 条件1: close < peak_close * 0.94
            if c < peak_close * TRAIL_PCT:
                sell_idx = j
                break
            # 条件2: close < buy_price * 0.94
            if c < buy_price * TRAIL_PCT:
                sell_idx = j
                break
        if sell_idx is not None:
            sell_date = df.iloc[sell_idx]['date']
            sell_price = float(df.iloc[sell_idx]['close'])
            trades[i]['sell_date'] = sell_date
            trades[i]['sell_price'] = round(sell_price, 2)
            trades[i]['peak_close'] = round(peak_close, 2)
            trades[i]['return_pct'] = round((sell_price / buy_price - 1) * 100, 2)
            trades[i]['duration_days'] = int((sell_date - buy_dt).days)
        else:
            # 未找到卖出，在回测结束日对仓位进行清算（卖出价为最后交易日收盘）
            last_dt = df.iloc[-1]['date']
            last_close = float(df.iloc[-1]['close'])
            sell_date = last_dt
            sell_price = last_close
            trades[i]['sell_date'] = sell_date
            trades[i]['sell_price'] = round(sell_price, 2)
            trades[i]['peak_close'] = round(peak_close, 2)
            trades[i]['return_pct'] = round((sell_price / buy_price - 1) * 100, 2)
            trades[i]['duration_days'] = int((sell_date - buy_dt).days)
        i += 1

    return trades


if __name__ == '__main__':
    df = load_df(CSV_PATH)
    if df.empty:
        raise SystemExit('在指定日期区间内未找到数据，请确认CSV和日期范围')
    trades = run_backtest(df)
    if not trades:
        print('在回测日期范围内未触发任何买入信号。')
    else:
        # 写入输出CSV
        out_df = pd.DataFrame(trades)
        # 移除内部使用的 buy_pos 字段
        if 'buy_pos' in out_df.columns:
            out_df = out_df.drop(columns=['buy_pos'])
        # 计算总收益复利
        total_prod = 1.0
        for r in out_df['return_pct']:
            total_prod *= (1 + (r/100.0))
        total_ret_pct = round((total_prod - 1) * 100, 2)
        out_df['buy_date'] = out_df['buy_date'].dt.strftime('%Y-%m-%d')
        out_df['sell_date'] = out_df['sell_date'].dt.strftime('%Y-%m-%d')
        out_df['buy_price'] = out_df['buy_price'].map(lambda x: float(f"{x:.2f}"))
        out_df['sell_price'] = out_df['sell_price'].map(lambda x: float(f"{x:.2f}"))
        out_df['peak_close'] = out_df['peak_close'].map(lambda x: float(f"{x:.2f}"))
        out_df['return_pct'] = out_df['return_pct'].map(lambda x: f"{x:.2f}")
        out_df.to_csv(OUT_FILE, index=False)
        # 打印表格预览
        print('交易明细:')
        print(out_df.to_string(index=False))
        print('\n汇总:')
        print(f'总交易次数: {len(out_df)}')
        print(f'合计收益(复利): {total_ret_pct}%')
        print(f'输出文件: {OUT_FILE}')

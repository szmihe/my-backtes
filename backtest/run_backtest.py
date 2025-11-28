"""
简单回测运行器：
- 读取 `manifest.csv`（位于仓库根或给定目录）
- 对指定标的文件（CSV）加载数据并运行策略的 `generate_signals` 方法
- 将结果写入 `outputs/`，并做简单的盈亏计算（按close收盘价做买卖并忽略滑点/手续费）
"""

import os
import pandas as pd
import argparse
from importlib import import_module


def load_manifest(manifest_path='manifest.csv'):
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"未找到manifest: {manifest_path}")
    return pd.read_csv(manifest_path)


def run_on_file(csv_path, strategy):
    df = pd.read_csv(csv_path)
    signals = strategy.generate_signals(df)
    # 简单的盈亏计算：依次按照signal进行买卖（1 买开，-1 卖出或卖空），忽略资金管理
    df = df.reset_index(drop=True)
    positions = signals.fillna(0)
    returns = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        # 如果上一日持仓为1，当天涨跌的收益等于（close_t / close_t-1 - 1）
        ret = df.loc[i, 'close'] / df.loc[i-1, 'close'] - 1
        if positions.iloc[i-1] == 1:
            returns.iloc[i] = ret
        elif positions.iloc[i-1] == -1:
            returns.iloc[i] = -ret
    cumret = (1 + returns).cumprod() - 1
    return returns, cumret


def main():
    parser = argparse.ArgumentParser(description='运行回测示例')
    parser.add_argument('--manifest', default='manifest.csv', help='manifest 文件路径')
    parser.add_argument('--symbol', help='指定一个CSV文件名运行回测')
    parser.add_argument('--strategy', default='strategies.example_strategy', help='策略模块路径，例如 strategies.example_strategy')
    parser.add_argument('--outdir', default='outputs', help='输出目录')
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    os.makedirs(args.outdir, exist_ok=True)
    # 加载策略
    mod = import_module(args.strategy)
    StrategyClass = getattr(mod, 'Strategy', None)
    if StrategyClass is None:
        raise ImportError('策略模块必须提供 Strategy 类')
    strat = StrategyClass()

    targets = manifest['filename'].tolist()
    if args.symbol:
        targets = [args.symbol]

    for fname in targets:
        csv_path = fname if os.path.isabs(fname) else os.path.join(os.getcwd(), fname)
        if not os.path.exists(csv_path):
            # 尝试在 manifest 所在目录查找
            csv_path = os.path.join(os.path.dirname(args.manifest), fname)
        if not os.path.exists(csv_path):
            print(f"未找到文件: {fname}, 跳过")
            continue
        returns, cumret = run_on_file(csv_path, strat)
        out_df = pd.DataFrame({'date': pd.read_csv(csv_path)['date'], 'return': returns, 'cumret': cumret})
        outname = os.path.splitext(os.path.basename(fname))[0] + '.out.csv'
        out_df.to_csv(os.path.join(args.outdir, outname), index=False)
        print(f"已生成输出: {outname}")


if __name__ == '__main__':
    main()

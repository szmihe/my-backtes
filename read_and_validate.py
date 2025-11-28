# 批量校验与自动修复A股日线CSV数据
import os
import pandas as pd
import numpy as np
import argparse
import json

COLUMN_ALIASES = {
    'date': ['date', '日期'],
    'open': ['open', '开盘', '开盘价'],
    'high': ['high', '最高', '最高价'],
    'low': ['low', '最低', '最低价'],
    'close': ['close', '收盘', '收盘价'],
    'volume': ['volume', '成交量'],
    'amount': ['amount', '成交额'],
}

REQUIRED_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']


def map_columns(df):
    col_map = {}
    for std, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            for c in df.columns:
                if c.lower() == a.lower():
                    col_map[std] = c
    return col_map

def validate_file(fpath):
    result = {'file': fpath, 'problems': [], 'fixed': False}
    try:
        df = pd.read_csv(fpath)
    except Exception as e:
        result['problems'].append(f'无法读取: {e}')
        return result, None
    col_map = map_columns(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in col_map]
    if missing:
        result['problems'].append(f'缺少字段: {missing}')
    # 检查单调性、重复、类型
    if 'date' in col_map:
        if not df[col_map['date']].is_monotonic_increasing:
            result['problems'].append('日期非递增')
        if df.duplicated(subset=[col_map['date']]).any():
            result['problems'].append('日期有重复')
    # 检查数值类型
    for k in ['open', 'high', 'low', 'close', 'volume', 'amount']:
        if k in col_map:
            if not np.issubdtype(df[col_map[k]].dtype, np.number):
                result['problems'].append(f'{k} 非数值型')
    # 检查价格关系
    if all(x in col_map for x in ['open', 'high', 'low', 'close']):
        o, h, l, c = [df[col_map[x]] for x in ['open', 'high', 'low', 'close']]
        if not ((h >= o) & (h >= c) & (h >= l)).all():
            result['problems'].append('high小于open/close/low')
        if not ((l <= o) & (l <= c) & (l <= h)).all():
            result['problems'].append('low大于open/close/high')
    return result, df

def apply_auto_fix(df):
    # 列重命名
    col_map = map_columns(df)
    df = df.rename(columns={v: k for k, v in col_map.items()})
    # 日期排序、去重
    if 'date' in df.columns:
        df = df.drop_duplicates(subset=['date'])
        df = df.sort_values('date')
    # 成交量单位自动转换（如大于1e8，视为股，除以100）
    if 'volume' in df.columns and df['volume'].max() > 1e8:
        df['volume'] = df['volume'] / 100
    return df

def main():
    parser = argparse.ArgumentParser(description='批量校验与自动修复A股日线CSV')
    parser.add_argument('data_dir', help='数据目录')
    parser.add_argument('--auto-fix', action='store_true', help='自动修复并输出.fixed.csv')
    parser.add_argument('--overwrite', action='store_true', help='覆盖原始文件')
    parser.add_argument('--report', default='validation_report_autofix_all.json', help='报告输出文件')
    args = parser.parse_args()
    report = []
    for fname in os.listdir(args.data_dir):
        if fname.endswith('.csv'):
            fpath = os.path.join(args.data_dir, fname)
            result, df = validate_file(fpath)
            if args.auto_fix and df is not None:
                fixed = apply_auto_fix(df)
                outname = fname if args.overwrite else fname.replace('.csv', '.fixed.csv')
                fixed.to_csv(os.path.join(args.data_dir, outname), index=False)
                result['fixed'] = True
            report.append(result)
    with open(os.path.join(args.data_dir, args.report), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"校验与修复报告已生成: {args.report}")

if __name__ == '__main__':
    main()

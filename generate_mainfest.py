# 生成manifest脚本，自动索引A股日线CSV数据
import os
import pandas as pd
import argparse

def find_data_dir(path):
    # 自动检测常见数据目录
    if os.path.isdir(path):
        return path
    for sub in ["data", "dataset", "datasets"]:
        candidate = os.path.join(path, sub)
        if os.path.isdir(candidate):
            return candidate
    raise FileNotFoundError(f"未找到有效数据目录: {path}")

def generate_manifest(data_dir, output_file):
    records = []
    for fname in os.listdir(data_dir):
        if fname.endswith('.csv'):
            fpath = os.path.join(data_dir, fname)
            try:
                df = pd.read_csv(fpath, nrows=1)
                columns = ','.join(df.columns)
            except Exception as e:
                columns = f"读取失败: {e}"
            records.append({
                'filename': fname,
                'columns': columns,
                'size': os.path.getsize(fpath)
            })
    pd.DataFrame(records).to_csv(output_file, index=False)
    print(f"Manifest已生成: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='生成A股日线CSV数据manifest')
    parser.add_argument('data_dir', help='数据目录')
    parser.add_argument('--output', default='manifest.csv', help='manifest输出文件名')
    args = parser.parse_args()
    data_dir = find_data_dir(args.data_dir)
    generate_manifest(data_dir, args.output)

if __name__ == '__main__':
    main()

# A股日线数据清洗与回测数据准备流程

## 目录结构
- `generate_mainfest.py`：生成数据manifest索引
- `read_and_validate.py`：批量校验与自动修复CSV数据
- `manifest.csv`：数据文件清单
- `validation_report_autofix_all.json`：批量校验与修复报告
- `requirements.txt`：依赖包列表
- `README.md`：说明文档

## 使用说明

### 1. 生成manifest
```bash
python generate_mainfest.py /path/to/data_dir
```
- 自动扫描目录下所有CSV，生成manifest.csv

### 2. 校验与自动修复
```bash
python read_and_validate.py /path/to/data_dir --auto-fix
```
- 检查所有CSV格式、字段、单调性、重复、价格/成交量/金额一致性等
- 自动修复常见问题，生成`.fixed.csv`，不覆盖原始文件
- 输出详细JSON报告

### 3. 依赖安装
```bash
pip install -r requirements.txt
```

## 注意事项
- 原始CSV不会被覆盖，所有修复结果以`.fixed.csv`结尾
- manifest和校验报告建议随代码一同版本管理
- 如需自定义策略回测，可在数据清洗后添加策略脚本

## 依赖
- pandas
- numpy
- pyarrow
- pytest

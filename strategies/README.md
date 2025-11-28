# 策略目录说明

每个策略应包含：
- 一个策略实现文件，例如 `my_strategy.py`。
- 必须实现 `Strategy` 类，提供 `generate_signals(df)` 方法，接受 pandas.DataFrame 并返回包含信号的 DataFrame 或 Series。

示例策略代码请参考 `example_strategy.py`。

提交策略前建议：
- 在 `tests/` 添加单元测试，验证策略逻辑的正确性。
- 使用 `backtest/run_backtest.py` 在本地短期数据上运行回归测试（请先在 `manifest.csv` 中确认数据路径）。

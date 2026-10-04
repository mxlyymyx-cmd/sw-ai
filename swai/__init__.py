"""SWAI 参数化设计引擎。

法兰（flange）/ 离心叶轮（impeller）/ 轴流风机（axial）三大设计包：
设计计算 + 闭环验证（欧拉方程回代 / Stodola 滑移 / Lieblein 扩散因子 / DeHaller 数）
+ SolidWorks 建模宏生成。344 项离线单元测试守护，是整条产品线的引擎唯一正版。
"""

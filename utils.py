"""
utils.py - ETF分析工具函数
包含数据获取、计算、可视化和报告生成等功能
新增美股智能选股功能
"""
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import requests
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import streamlit as st
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
import time
import re

warnings.filterwarnings('ignore')

# 美股相关常量
US_INDICES = {
    "标普500": {"symbol": "^GSPC", "name": "S&P 500", "description": "美国500家大型上市公司"},
    "纳斯达克100": {"symbol": "^NDX", "name": "NASDAQ 100", "description": "纳斯达克100家最大非金融公司"},
    "道琼斯工业": {"symbol": "^DJI", "name": "Dow Jones Industrial", "description": "美国30家大型上市公司"},
    "罗素2000": {"symbol": "^RUT", "name": "Russell 2000", "description": "美国2000家小型公司"},
    "费城半导体": {"symbol": "^SOX", "name": "PHLX Semiconductor", "description": "半导体行业指数"}
}

US_SECTORS = {
    "科技": {"symbol": "XLK", "name": "Technology Select Sector", "description": "科技行业"},
    "医疗": {"symbol": "XLV", "name": "Health Care Select Sector", "description": "医疗保健行业"},
    "金融": {"symbol": "XLF", "name": "Financial Select Sector", "description": "金融行业"},
    "消费": {"symbol": "XLY", "name": "Consumer Discretionary", "description": "非必需消费品"},
    "工业": {"symbol": "XLI", "name": "Industrial Select Sector", "description": "工业行业"},
    "能源": {"symbol": "XLE", "name": "Energy Select Sector", "description": "能源行业"},
    "原材料": {"symbol": "XLB", "name": "Materials Select Sector", "description": "原材料行业"},
    "房地产": {"symbol": "XLRE", "name": "Real Estate Select Sector", "description": "房地产行业"},
    "公用事业": {"symbol": "XLU", "name": "Utilities Select Sector", "description": "公用事业行业"},
    "通信": {"symbol": "XLC", "name": "Communication Services", "description": "通信服务行业"}
}

POPULAR_US_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Communication Services"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway", "sector": "Financial Services"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial Services"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"}
]

# 简单缓存字典，用于存储数据和过期时间
_simple_cache = {}

def _make_hashable(obj):
    """将可能不可哈希的参数转换为可哈希形式"""
    if isinstance(obj, list):
        return tuple(_make_hashable(item) for item in obj)
    elif isinstance(obj, dict):
        return tuple(sorted((_make_hashable(k), _make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, set):
        return tuple(sorted(_make_hashable(item) for item in obj))
    # 添加其他需要处理的不可哈希类型
    else:
        return obj

def cache_data(ttl=3600):
    """缓存数据，减少重复请求 (最终修复版)"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 将参数转换为可哈希形式
            hashable_args = _make_hashable(args)
            hashable_kwargs = _make_hashable(kwargs)
            
            # 生成缓存键
            cache_key = f"{func.__name__}_{hashable_args}_{hashable_kwargs}"
            
            current_time = time.time()
            
            # 检查缓存是否存在且未过期
            if cache_key in _simple_cache:
                cached_data, timestamp = _simple_cache[cache_key]
                if current_time - timestamp < ttl:
                    return cached_data
            
            # 执行原函数获取数据
            result = func(*args, **kwargs)
            
            # 存储到缓存
            _simple_cache[cache_key] = (result, current_time)
            
            return result
        return wrapper
    return decorator

# ==============================================
# 美股智能选股相关函数
# ==============================================

@cache_data(ttl=1800)
def get_us_stock_info(ticker: str) -> Dict:
    """
    获取美股基本信息
    
    Args:
        ticker: 股票代码 (如: AAPL, MSFT)
    
    Returns:
        股票信息字典
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 基本信息
        basic_info = {
            "symbol": ticker,
            "name": info.get('longName', ticker),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "current_price": info.get('currentPrice', info.get('regularMarketPrice', 0)),
            "market_cap": info.get('marketCap', 0),
            "pe_ratio": info.get('trailingPE', 0),
            "pb_ratio": info.get('priceToBook', 0),
            "ps_ratio": info.get('priceToSalesTrailing12Months', 0),
            "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            "beta": info.get('beta', 1.0),
            "52w_high": info.get('fiftyTwoWeekHigh', 0),
            "52w_low": info.get('fiftyTwoWeekLow', 0),
            "volume": info.get('volume', 0),
            "avg_volume": info.get('averageVolume', 0)
        }
        
        # 财务指标
        financials = {
            "roe": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
            "roa": info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0,
            "gross_margin": info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0,
            "operating_margin": info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0,
            "profit_margin": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
            "revenue_growth": info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
            "earnings_growth": info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
            "debt_to_equity": info.get('debtToEquity', 0),
            "current_ratio": info.get('currentRatio', 0),
            "quick_ratio": info.get('quickRatio', 0)
        }
        
        return {
            "basic_info": basic_info,
            "financials": financials,
            "success": True
        }
    except Exception as e:
        return {
            "symbol": ticker,
            "success": False,
            "error": str(e)
        }

@cache_data(ttl=3600)
def get_us_stock_factors(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """
    计算美股多因子得分
    
    Args:
        tickers: 股票代码列表
        period: 历史数据周期
    
    Returns:
        包含因子得分的DataFrame
    """
    factors_data = []
    
    for ticker in tickers:
        try:
            stock_info = get_us_stock_info(ticker)
            if not stock_info["success"]:
                continue
                
            # 获取历史价格数据计算动量
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if len(hist) < 20:
                continue
            
            # 计算动量因子
            momentum_1m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-21] - 1) * 100 if len(hist) > 21 else 0
            momentum_3m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-63] - 1) * 100 if len(hist) > 63 else 0
            momentum_6m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-126] - 1) * 100 if len(hist) > 126 else 0
            
            # 计算波动率
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100
            
            # 获取财务数据
            basic_info = stock_info["basic_info"]
            financials = stock_info["financials"]
            
            # 计算价值因子得分 (越低估值得分越高)
            pe = basic_info["pe_ratio"]
            pb = basic_info["pb_ratio"]
            ps = basic_info["ps_ratio"]
            dividend_yield = basic_info["dividend_yield"]
            
            value_score = 0
            if 0 < pe < 50:
                value_score += (50 - pe) / 50  # PE越低得分越高
            if 0 < pb < 5:
                value_score += (5 - pb) / 5    # PB越低得分越高
            if dividend_yield > 0:
                value_score += min(dividend_yield / 5, 1)  # 股息率越高得分越高
            
            # 计算成长因子得分
            revenue_growth = financials["revenue_growth"]
            earnings_growth = financials["earnings_growth"]
            
            growth_score = 0
            if revenue_growth > 0:
                growth_score += min(revenue_growth / 30, 1)  # 营收增长
            if earnings_growth > 0:
                growth_score += min(earnings_growth / 30, 1)  # 利润增长
            
            # 计算质量因子得分
            roe = financials["roe"]
            profit_margin = financials["profit_margin"]
            debt_to_equity = financials["debt_to_equity"]
            
            quality_score = 0
            if roe > 0:
                quality_score += min(roe / 30, 1)  # ROE越高越好
            if profit_margin > 0:
                quality_score += min(profit_margin / 20, 1)  # 利润率越高越好
            if debt_to_equity < 1:
                quality_score += (1 - debt_to_equity)  # 负债率越低越好
            
            # 计算动量因子得分
            momentum_score = 0
            if momentum_3m > 0:
                momentum_score += min(momentum_3m / 30, 1)  # 动量越强得分越高
            
            # 计算风险调整得分 (波动率越低得分越高)
            risk_adjusted_score = 0
            if volatility > 0:
                risk_adjusted_score = min(30 / volatility, 2)  # 波动率越低得分越高
            
            # 综合得分 (加权平均)
            total_score = (
                value_score * 0.25 +
                growth_score * 0.25 +
                quality_score * 0.20 +
                momentum_score * 0.15 +
                risk_adjusted_score * 0.15
            )
            
            # 构建数据行
            factors_data.append({
                "股票代码": ticker,
                "公司名称": basic_info["name"],
                "行业": basic_info["sector"],
                "当前价格": round(basic_info["current_price"], 2),
                "市值(十亿)": round(basic_info["market_cap"] / 1e9, 2),
                "市盈率(PE)": round(pe, 2),
                "市净率(PB)": round(pb, 2),
                "股息率(%)": round(dividend_yield, 2),
                "ROE(%)": round(roe, 2),
                "营收增长(%)": round(revenue_growth, 2),
                "利润增长(%)": round(earnings_growth, 2),
                "1月动量(%)": round(momentum_1m, 2),
                "3月动量(%)": round(momentum_3m, 2),
                "6月动量(%)": round(momentum_6m, 2),
                "波动率(%)": round(volatility, 2),
                "价值得分": round(value_score, 3),
                "成长得分": round(growth_score, 3),
                "质量得分": round(quality_score, 3),
                "动量得分": round(momentum_score, 3),
                "风险得分": round(risk_adjusted_score, 3),
                "综合得分": round(total_score, 3)
            })
            
        except Exception as e:
            continue
    
    return pd.DataFrame(factors_data)

def calculate_weighted_score(df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    """
    计算加权综合得分
    
    Args:
        df: 包含因子得分的DataFrame
        weights: 因子权重字典
    
    Returns:
        添加加权得分列的DataFrame
    """
    df = df.copy()
    
    # 默认权重
    default_weights = {
        "value": 0.25,      # 价值
        "growth": 0.25,     # 成长
        "quality": 0.20,    # 质量
        "momentum": 0.15,   # 动量
        "risk": 0.15        # 风险
    }
    
    # 使用提供的权重或默认权重
    weights = weights or default_weights
    
    # 计算加权综合得分
    df["加权得分"] = (
        df["价值得分"] * weights["value"] +
        df["成长得分"] * weights["growth"] +
        df["质量得分"] * weights["quality"] +
        df["动量得分"] * weights["momentum"] +
        df["风险得分"] * weights["risk"]
    )
    
    # 归一化到0-1范围
    if df["加权得分"].max() > df["加权得分"].min():
        df["加权得分"] = (df["加权得分"] - df["加权得分"].min()) / (df["加权得分"].max() - df["加权得分"].min())
    
    return df

@cache_data(ttl=7200)
def get_sp500_components() -> List[str]:
    """
    获取标普500成分股列表 (简化版)
    
    Returns:
        股票代码列表
    """
    # 这里使用预设的热门股票作为示例
    # 实际应用中应该通过API获取完整列表
    sp500_stocks = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "TSLA", "BRK-B", "UNH", 
        "JNJ", "XOM", "JPM", "V", "PG", "NVDA", "HD", "MA", "CVX", "ABBV",
        "PFE", "LLY", "BAC", "KO", "PEP", "AVGO", "COST", "DIS", "CSCO",
        "WMT", "MRK", "MCD", "ABT", "ADBE", "TMO", "ACN", "NKE", "CRM",
        "VZ", "DHR", "NEE", "LIN", "PM", "TXN", "BMY", "HON", "AMD",
        "INTC", "QCOM", "T", "UPS", "IBM", "SBUX", "GS", "BA", "CAT"
    ]
    
    return sp500_stocks

@cache_data(ttl=7200)
def get_nasdaq100_components() -> List[str]:
    """
    获取纳斯达克100成分股列表 (简化版)
    
    Returns:
        股票代码列表
    """
    nasdaq100_stocks = [
        "AAPL", "MSFT", "AMZN", "TSLA", "GOOGL", "GOOG", "NVDA", "META",
        "AVGO", "PEP", "COST", "AMD", "ADBE", "CSCO", "INTC", "CMCSA",
        "NFLX", "QCOM", "AMGN", "TXN", "INTU", "HON", "PYPL", "SBUX",
        "BKNG", "ADI", "GILD", "MDLZ", "REGN", "ISRG", "VRTX", "FISV",
        "LRCX", "ATVI", "KDP", "KHC", "CHTR", "ADP", "MELI", "MNST",
        "SNPS", "CDNS", "MAR", "ASML", "ORLY", "PDD", "AZN", "EXC",
        "MRNA", "WDAY", "CTAS", "ROST", "DXCM", "IDXX", "FAST", "DLTR",
        "VRSK", "BIIB", "ALGN", "SIRI", "EBAY", "ZM", "JD", "LCID"
    ]
    
    return nasdaq100_stocks

def filter_stocks_by_criteria(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """
    根据筛选条件过滤股票
    
    Args:
        df: 股票数据DataFrame
        filters: 筛选条件字典
    
    Returns:
        过滤后的DataFrame
    """
    filtered_df = df.copy()
    
    # 如果过滤后为空，逐步放宽条件直到有股票入选
    original_filters = filters.copy()
    
    # 市值筛选
    if "min_market_cap" in filters and filters["min_market_cap"]:
        market_cap_vals = filtered_df["市值(十亿)"].dropna()
        if not market_cap_vals.empty:
            current_min = market_cap_vals.min()
            if current_min <= filters["min_market_cap"]:
                filtered_df = filtered_df[filtered_df["市值(十亿)"] >= filters["min_market_cap"]]
    
    # 市盈率筛选 - 注意处理负值（亏损公司）
    if "max_pe" in filters and filters["max_pe"]:
        pe_vals = filtered_df["市盈率(PE)"].dropna()
        if not pe_vals.empty:
            # 包含PE为正数且不超过max_pe，以及PE为负（亏损）的股票
            filtered_df = filtered_df[(filtered_df["市盈率(PE)"] <= filters["max_pe"]) | 
                                     (filtered_df["市盈率(PE)"] <= 0)]
    
    # ROE筛选
    if "min_roe" in filters and filters["min_roe"]:
        roe_vals = filtered_df["ROE(%)"].dropna()
        if not roe_vals.empty:
            current_min = roe_vals.min()
            if current_min <= filters["min_roe"]:
                filtered_df = filtered_df[filtered_df["ROE(%)"] >= filters["min_roe"]]
    
    # 波动率筛选
    if "max_volatility" in filters and filters["max_volatility"]:
        vol_vals = filtered_df["波动率(%)"].dropna()
        if not vol_vals.empty:
            current_max = vol_vals.max()
            if current_max >= filters["max_volatility"]:
                filtered_df = filtered_df[filtered_df["波动率(%)"] <= filters["max_volatility"]]
    
    # 行业筛选
    if "sectors" in filters and filters["sectors"]:
        if len(filtered_df) > 0:
            # 检查是否有符合行业的股票
            sector_stocks = filtered_df[filtered_df["行业"].isin(filters["sectors"])]
            if len(sector_stocks) > 0:
                filtered_df = sector_stocks
    
    # 股息率筛选
    if "min_dividend_yield" in filters and filters["min_dividend_yield"]:
        filtered_df = filtered_df[filtered_df["股息率(%)"] >= filters["min_dividend_yield"]]
    
    # 如果过滤后为空，尝试自动放宽条件
    if len(filtered_df) == 0 and len(df) > 0:
        return auto_relax_criteria(df, original_filters)
    
    return filtered_df

def auto_relax_criteria(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """
    自动放宽筛选条件
    
    Args:
        df: 原始股票数据DataFrame
        filters: 原始筛选条件
    
    Returns:
        放宽条件后的DataFrame
    """
    relaxed_df = df.copy()
    
    # 计算各指标的中位数作为默认值
    if "min_market_cap" in filters:
        market_cap_median = df["市值(十亿)"].median()
        if pd.notna(market_cap_median):
            relaxed_df = relaxed_df[relaxed_df["市值(十亿)"] >= market_cap_median * 0.5]
    
    if "max_pe" in filters:
        pe_median = df["市盈率(PE)"][df["市盈率(PE)"] > 0].median()
        if pd.notna(pe_median):
            relaxed_df = relaxed_df[(relaxed_df["市盈率(PE)"] <= pe_median * 2) | 
                                   (relaxed_df["市盈率(PE)"] <= 0)]
    
    if "min_roe" in filters:
        roe_median = df["ROE(%)"].median()
        if pd.notna(roe_median):
            relaxed_df = relaxed_df[relaxed_df["ROE(%)"] >= roe_median * 0.8]
    
    if "max_volatility" in filters:
        vol_median = df["波动率(%)"].median()
        if pd.notna(vol_median):
            relaxed_df = relaxed_df[relaxed_df["波动率(%)"] <= vol_median * 1.5]
    
    # 如果仍然为空，返回按综合得分排序的前N只股票
    if len(relaxed_df) == 0 and len(df) > 0:
        return df.sort_values("综合得分", ascending=False).head(20)
    
    return relaxed_df

def simulate_backtest(selected_stocks: List[str], weights: List[float], 
                     start_date: str, end_date: str) -> Dict:
    """
    模拟投资组合回测
    
    Args:
        selected_stocks: 选择的股票列表
        weights: 权重列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        回测结果字典
    """
    try:
        # 获取历史数据
        prices = []
        valid_stocks = []
        valid_weights = []
        
        for stock, weight in zip(selected_stocks, weights):
            try:
                hist = yf.download(stock, start=start_date, end=end_date, progress=False)
                if not hist.empty and len(hist) > 20:  # 确保有足够的数据点
                    prices.append(hist['Adj Close'])
                    valid_stocks.append(stock)
                    valid_weights.append(weight)
            except Exception as e:
                st.warning(f"无法获取股票 {stock} 的数据: {e}")
                continue
        
        if len(prices) < len(selected_stocks):
            # 如果部分股票数据缺失，调整权重
            st.info(f"部分股票数据缺失，实际获取{len(prices)}/{len(selected_stocks)}只股票数据")
            
        if len(prices) == 0:
            return {"error": "无法获取任何股票数据，请检查股票代码和日期范围"}
        
        # 创建价格DataFrame
        prices_df = pd.concat(prices, axis=1)
        prices_df.columns = valid_stocks
        
        # 重新归一化权重
        if sum(valid_weights) > 0:
            valid_weights = [w/sum(valid_weights) for w in valid_weights]
        else:
            # 如果权重总和为0，使用等权重
            valid_weights = [1/len(valid_stocks)] * len(valid_stocks)
        
        # 填充缺失值（使用前向填充）
        prices_df = prices_df.ffill().dropna()
        
        if len(prices_df) < 10:
            return {"error": f"数据点不足({len(prices_df)})，无法进行有效回测"}
        
        # 计算收益率
        returns_df = prices_df.pct_change().dropna()
        
        if len(returns_df) < 10:
            return {"error": f"有效收益率数据点不足({len(returns_df)})"}
        
        # 检查收益率序列是否全为0（避免除零错误）
        if returns_df.std().mean() == 0:
            # 添加微小噪声避免除零错误
            noise = np.random.normal(0, 1e-6, returns_df.shape)
            returns_df = returns_df + noise
        
        # 计算投资组合收益率
        portfolio_returns = (returns_df * valid_weights).sum(axis=1)
        
        # 检查投资组合收益率是否有变化
        if portfolio_returns.std() == 0:
            # 添加微小噪声
            portfolio_returns = portfolio_returns + np.random.normal(0, 1e-6, len(portfolio_returns))
        
        # 计算累计收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # 计算基准收益率 (标普500)
        try:
            benchmark = yf.download("^GSPC", start=start_date, end=end_date, progress=False)
            if not benchmark.empty and len(benchmark) > 10:
                benchmark_returns = benchmark['Adj Close'].pct_change().dropna()
                # 对齐日期
                common_dates = benchmark_returns.index.intersection(cumulative_returns.index)
                if len(common_dates) > 10:
                    benchmark_cumulative = (1 + benchmark_returns.loc[common_dates]).cumprod()
                    # 重新索引组合收益率以匹配基准
                    portfolio_cumulative_aligned = cumulative_returns.loc[common_dates]
                else:
                    benchmark_cumulative = pd.Series([1.0] * len(cumulative_returns), index=cumulative_returns.index)
                    portfolio_cumulative_aligned = cumulative_returns
            else:
                benchmark_cumulative = pd.Series([1.0] * len(cumulative_returns), index=cumulative_returns.index)
                portfolio_cumulative_aligned = cumulative_returns
        except:
            benchmark_cumulative = pd.Series([1.0] * len(cumulative_returns), index=cumulative_returns.index)
            portfolio_cumulative_aligned = cumulative_returns
        
        # 计算绩效指标
        annual_return = portfolio_returns.mean() * 252
        
        # 计算年化波动率，避免除零错误
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        if annual_volatility == 0:
            annual_volatility = 0.01  # 设置最小波动率
        
        # 计算夏普比率 (假设无风险利率为3%)
        sharpe_ratio = (annual_return - 0.03) / annual_volatility if annual_volatility > 0 else 0
        
        # 计算最大回撤
        running_max = portfolio_cumulative_aligned.expanding().max()
        
        # 避免除零错误
        if (running_max == 0).any():
            running_max = running_max.replace(0, 1e-10)
        
        drawdown = (portfolio_cumulative_aligned - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        # 计算累计收益率
        if len(portfolio_cumulative_aligned) > 0:
            cumulative_return_value = portfolio_cumulative_aligned.iloc[-1] - 1
        else:
            cumulative_return_value = 0
        
        return {
            "portfolio_cumulative": portfolio_cumulative_aligned,
            "benchmark_cumulative": benchmark_cumulative,
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "cumulative_return": cumulative_return_value,
            "weights": valid_weights,
            "stocks": valid_stocks,
            "prices_df": prices_df
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return {"error": f"回测模拟失败: {str(e)}\n详情: {error_detail}"}

def plot_us_stock_factors_radar(df: pd.DataFrame, top_n: int = 3) -> go.Figure:
    """
    绘制美股因子雷达图
    
    Args:
        df: 包含因子得分的DataFrame
        top_n: 显示前N只股票
    
    Returns:
        Plotly雷达图
    """
    if df.empty or top_n <= 0:
        return go.Figure()
    
    # 选择得分最高的股票
    top_stocks = df.nlargest(top_n, "加权得分")
    
    fig = go.Figure()
    
    for idx, row in top_stocks.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[
                row["价值得分"],
                row["成长得分"],
                row["质量得分"],
                row["动量得分"],
                row["风险得分"],
                row["价值得分"]  # 闭合图形
            ],
            theta=['价值', '成长', '质量', '动量', '风险', '价值'],
            name=row["股票代码"],
            fill='toself'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        title=f"Top {top_n} 股票因子雷达图",
        height=500
    )
    
    return fig

def plot_us_sector_distribution(df: pd.DataFrame) -> go.Figure:
    """
    绘制行业分布图
    
    Args:
        df: 包含行业信息的DataFrame
    
    Returns:
        Plotly饼图
    """
    if df.empty or '行业' not in df.columns:
        return go.Figure()
    
    sector_counts = df['行业'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=sector_counts.index,
        values=sector_counts.values,
        hole=0.3,
        textinfo='label+percent',
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(
        title="行业分布",
        height=400
    )
    
    return fig

def export_us_stock_report(df: pd.DataFrame, report_data: Dict) -> BytesIO:
    """
    导出美股选股报告
    
    Args:
        df: 选股结果DataFrame
        report_data: 报告数据
    
    Returns:
        BytesIO对象
    """
    buffer = BytesIO()
    
    # 创建Excel写入器
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # 写入选股结果
        df.to_excel(writer, sheet_name='选股结果', index=False)
        
        # 写入绩效数据
        performance_df = pd.DataFrame({
            '指标': ['年化收益率', '年化波动率', '夏普比率', '最大回撤', '股票数量'],
            '数值': [
                f"{report_data.get('annual_return', 0):.2%}",
                f"{report_data.get('annual_volatility', 0):.2%}",
                f"{report_data.get('sharpe_ratio', 0):.2f}",
                f"{report_data.get('max_drawdown', 0):.2%}",
                len(df)
            ]
        })
        performance_df.to_excel(writer, sheet_name='绩效摘要', index=False)
        
        # 写入因子权重
        weights_df = pd.DataFrame({
            '因子': ['价值', '成长', '质量', '动量', '风险'],
            '权重': [
                report_data.get('weights', {}).get('value', 0.25),
                report_data.get('weights', {}).get('growth', 0.25),
                report_data.get('weights', {}).get('quality', 0.20),
                report_data.get('weights', {}).get('momentum', 0.15),
                report_data.get('weights', {}).get('risk', 0.15)
            ]
        })
        weights_df.to_excel(writer, sheet_name='因子权重', index=False)
        
        # 获取工作簿和工作表
        workbook = writer.book
        worksheet = writer.sheets['选股结果']
        
        # 设置列宽
        worksheet.set_column('A:Z', 15)
        
        # 添加格式
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 应用标题格式
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    buffer.seek(0)
    return buffer

# ==============================================
# 原有函数保持不变，以下为原有代码
# ==============================================

@cache_data(ttl=3600)
def get_index_data(index_code: str, period: str = "1y") -> pd.DataFrame:
    """
    获取指数历史数据
    
    Args:
        index_code: 指数代码 (如: ^GSPC, ^HSI, 000300.SS)
        period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        DataFrame with historical data
    """
    try:
        # 添加后缀处理
        if index_code.startswith('^') or '.SS' in index_code or '.SZ' in index_code:
            ticker = index_code
        else:
            # 尝试常见指数格式
            if not index_code.startswith('^'):
                ticker = f'^{index_code}' if not index_code.startswith('00') else f'{index_code}.SS'
            else:
                ticker = index_code
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            # 尝试其他格式
            stock = yf.Ticker(index_code)
            hist = stock.history(period=period)
        
        return hist
    except Exception as e:
        st.error(f"获取指数数据失败: {e}")
        return pd.DataFrame()

@cache_data(ttl=300)
def get_etf_data(etf_code: str, period: str = "1mo") -> pd.DataFrame:
    """
    获取ETF历史数据
    
    Args:
        etf_code: ETF代码
        period: 时间周期
    
    Returns:
        DataFrame with ETF historical data
    """
    try:
        # 处理A股ETF
        if etf_code.endswith('.SS') or etf_code.endswith('.SZ'):
            ticker = etf_code
        elif etf_code.startswith('51') or etf_code.startswith('15'):
            ticker = f'{etf_code}.SS'  # 上海ETF
        elif etf_code.startswith('159'):
            ticker = f'{etf_code}.SZ'  # 深圳ETF
        else:
            ticker = etf_code  # 其他市场ETF
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        return hist
    except Exception as e:
        st.error(f"获取ETF数据失败: {e}")
        return pd.DataFrame()

@cache_data(ttl=60)
def get_realtime_price(etf_codes: List[str]) -> pd.DataFrame:
    """
    获取ETF实时价格
    
    Args:
        etf_codes: ETF代码列表
    
    Returns:
        DataFrame with realtime prices
    """
    data = []
    
    for code in etf_codes:
        try:
            # 处理代码格式
            if code.endswith('.SS') or code.endswith('.SZ'):
                ticker = code
            elif code.startswith('51') or code.startswith('15'):
                ticker = f'{code}.SS'
            elif code.startswith('159'):
                ticker = f'{code}.SZ'
            else:
                ticker = code
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 获取实时数据
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            previous_close = info.get('previousClose', 0)
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            data.append({
                'ETF代码': code,
                '名称': info.get('shortName', code),
                '当前价格': round(current_price, 3),
                '涨跌额': round(change, 3),
                '涨跌幅%': round(change_percent, 3),
                '昨收': round(previous_close, 3),
                '开盘': round(info.get('open', 0), 3),
                '最高': round(info.get('dayHigh', 0), 3),
                '最低': round(info.get('dayLow', 0), 3),
                '成交量': info.get('volume', 0)
            })
        except Exception as e:
            st.warning(f"无法获取 {code} 的实时数据: {e}")
            continue
    
    return pd.DataFrame(data)

def calculate_portfolio_metrics(prices_df: pd.DataFrame, weights: List[float]) -> Dict:
    """
    计算投资组合指标
    
    Args:
        prices_df: 各资产价格DataFrame
        weights: 权重列表
    
    Returns:
        组合指标字典
    """
    if prices_df.empty or len(weights) != len(prices_df.columns):
        return {}
    
    # 计算收益率
    returns = prices_df.pct_change().dropna()
    
    # 组合收益率
    portfolio_returns = (returns * weights).sum(axis=1)
    
    # 年化收益率
    annual_return = portfolio_returns.mean() * 252
    
    # 年化波动率
    annual_volatility = portfolio_returns.std() * np.sqrt(252)
    
    # 夏普比率 (假设无风险利率为2%)
    risk_free_rate = 0.02
    sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
    
    # 最大回撤
    cumulative_returns = (1 + portfolio_returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # 累计收益率
    cumulative_return = cumulative_returns.iloc[-1] - 1 if not cumulative_returns.empty else 0
    
    return {
        '年化收益率': annual_return,
        '年化波动率': annual_volatility,
        '夏普比率': sharpe_ratio,
        '最大回撤': max_drawdown,
        '累计收益率': cumulative_return,
        '组合收益率序列': portfolio_returns,
        '累计收益序列': cumulative_returns
    }

def markowitz_optimization(returns_df: pd.DataFrame, target_return: float = None) -> Dict:
    """
    Markowitz均值-方差优化
    
    Args:
        returns_df: 收益率DataFrame
        target_return: 目标收益率
    
    Returns:
        优化结果字典
    """
    from scipy.optimize import minimize
    
    n_assets = len(returns_df.columns)
    mean_returns = returns_df.mean() * 252
    cov_matrix = returns_df.cov() * 252
    
    def portfolio_stats(weights):
        port_return = np.sum(mean_returns * weights)
        port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = port_return / port_volatility
        return port_return, port_volatility, sharpe
    
    def negative_sharpe(weights):
        _, _, sharpe = portfolio_stats(weights)
        return -sharpe
    
    def check_sum(weights):
        return np.sum(weights) - 1
    
    # 约束条件
    constraints = [{'type': 'eq', 'fun': check_sum}]
    bounds = tuple((0, 1) for _ in range(n_assets))
    
    # 初始权重
    init_weights = n_assets * [1./n_assets]
    
    # 优化
    optimized = minimize(negative_sharpe, init_weights,
                        method='SLSQP', bounds=bounds,
                        constraints=constraints)
    
    if optimized.success:
        opt_weights = optimized.x
        opt_return, opt_volatility, opt_sharpe = portfolio_stats(opt_weights)
        
        return {
            'weights': opt_weights,
            'expected_return': opt_return,
            'volatility': opt_volatility,
            'sharpe_ratio': opt_sharpe
        }
    
    return {}

def risk_parity_optimization(returns_df: pd.DataFrame) -> Dict:
    """
    风险平价优化
    
    Args:
        returns_df: 收益率DataFrame
    
    Returns:
        优化结果字典
    """
    from scipy.optimize import minimize
    
    n_assets = len(returns_df.columns)
    cov_matrix = returns_df.cov() * 252
    
    def risk_contribution(weights):
        port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_risk = np.dot(cov_matrix, weights) / port_volatility
        risk_contributions = weights * marginal_risk
        return risk_contributions
    
    def risk_parity_objective(weights):
        risk_contributions = risk_contribution(weights)
        target_rc = np.ones(n_assets) / n_assets
        return np.sum((risk_contributions - target_rc) ** 2)
    
    def check_sum(weights):
        return np.sum(weights) - 1
    
    # 约束条件
    constraints = [{'type': 'eq', 'fun': check_sum}]
    bounds = tuple((0, 1) for _ in range(n_assets))
    
    # 初始权重
    init_weights = n_assets * [1./n_assets]
    
    # 优化
    optimized = minimize(risk_parity_objective, init_weights,
                        method='SLSQP', bounds=bounds,
                        constraints=constraints)
    
    if optimized.success:
        rp_weights = optimized.x
        rc = risk_contribution(rp_weights)
        
        return {
            'weights': rp_weights,
            'risk_contributions': rc
        }
    
    return {}

def plot_kline(data: pd.DataFrame, title: str = "K线图") -> go.Figure:
    """
    绘制K线图
    
    Args:
        data: 包含OHLC数据的DataFrame
        title: 图表标题
    
    Returns:
        Plotly Figure对象
    """
    if data.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=(title, "成交量")
    )
    
    # K线图
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="OHLC"
        ),
        row=1, col=1
    )
    
    # 添加移动平均线
    for window in [5, 20, 60]:
        if len(data) >= window:
            ma = data['Close'].rolling(window=window).mean()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=ma,
                    name=f'MA{window}',
                    line=dict(width=1)
                ),
                row=1, col=1
            )
    
    # 成交量
    colors_volume = ['red' if data['Close'].iloc[i] >= data['Open'].iloc[i] else 'green' 
                     for i in range(len(data))]
    
    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data['Volume'],
            name='成交量',
            marker_color=colors_volume
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=title,
        xaxis_title='日期',
        yaxis_title='价格',
        xaxis_rangeslider_visible=False,
        height=600,
        template='plotly_white'
    )
    
    return fig

def plot_portfolio_weights(weights: List[float], labels: List[str], title: str = "投资组合权重") -> Tuple[go.Figure, go.Figure]:
    """
    绘制投资组合权重图
    
    Args:
        weights: 权重列表
        labels: 资产标签
        title: 图表标题
    
    Returns:
        (饼图, 柱状图)
    """
    # 创建数据框
    df_weights = pd.DataFrame({
        '资产': labels,
        '权重': weights
    }).sort_values('权重', ascending=False)
    
    # 饼图
    fig_pie = px.pie(
        df_weights,
        values='权重',
        names='资产',
        title=f'{title} - 饼图',
        hole=0.3
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    
    # 柱状图
    fig_bar = px.bar(
        df_weights,
        x='资产',
        y='权重',
        title=f'{title} - 柱状图',
        text='权重',
        color='权重',
        color_continuous_scale='Viridis'
    )
    fig_bar.update_traces(texttemplate='%{text:.1%}', textposition='outside')
    fig_bar.update_layout(yaxis_tickformat=',.1%')
    
    return fig_pie, fig_bar

def plot_portfolio_performance(cumulative_returns: pd.Series, 
                              benchmark_returns: pd.Series = None,
                              title: str = "投资组合表现") -> go.Figure:
    """
    绘制投资组合表现图
    
    Args:
        cumulative_returns: 组合累计收益率序列
        benchmark_returns: 基准累计收益率序列
        title: 图表标题
    
    Returns:
        Plotly Figure对象
    """
    fig = go.Figure()
    
    # 组合累计收益
    fig.add_trace(go.Scatter(
        x=cumulative_returns.index,
        y=cumulative_returns.values,
        mode='lines',
        name='投资组合',
        line=dict(color='blue', width=2)
    ))
    
    # 基准累计收益（如果提供）
    if benchmark_returns is not None:
        fig.add_trace(go.Scatter(
            x=benchmark_returns.index,
            y=benchmark_returns.values,
            mode='lines',
            name='基准',
            line=dict(color='red', width=2, dash='dash')
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title='日期',
        yaxis_title='累计收益率',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    fig.update_yaxes(tickformat=',.0%')
    
    return fig

def generate_pdf_report(portfolio_data: Dict, output_path: str = "portfolio_report.pdf") -> BytesIO:
    """
    生成PDF报告
    
    Args:
        portfolio_data: 包含投资组合数据的字典
        output_path: 输出文件路径
    
    Returns:
        BytesIO对象（用于Streamlit下载）
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # 自定义样式
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    
    # 内容列表
    story = []
    
    # 标题
    story.append(Paragraph("投资组合分析报告", title_style))
    story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # 组合概要
    story.append(Paragraph("1. 组合概要", styles['Heading2']))
    
    if 'metrics' in portfolio_data:
        metrics = portfolio_data['metrics']
        data = [
            ['指标', '数值'],
            ['年化收益率', f"{metrics.get('年化收益率', 0):.2%}"],
            ['年化波动率', f"{metrics.get('年化波动率', 0):.2%}"],
            ['夏普比率', f"{metrics.get('夏普比率', 0):.2f}"],
            ['最大回撤', f"{metrics.get('最大回撤', 0):.2%}"],
            ['累计收益率', f"{metrics.get('累计收益率', 0):.2%}"]
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
    
    # 资产配置
    if 'weights' in portfolio_data and 'labels' in portfolio_data:
        story.append(Paragraph("2. 资产配置", styles['Heading2']))
        
        weights_data = []
        for label, weight in zip(portfolio_data['labels'], portfolio_data['weights']):
            weights_data.append([label, f"{weight:.1%}"])
        
        weights_table = Table([['资产', '权重']] + weights_data)
        weights_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER')
        ]))
        
        story.append(weights_table)
        story.append(Spacer(1, 20))
    
    # 风险提示
    story.append(Paragraph("3. 风险提示", styles['Heading2']))
    risk_text = """
    1. 历史表现不代表未来收益
    2. 投资有风险，入市需谨慎
    3. 本报告仅为分析工具，不构成投资建议
    4. 请根据自身风险承受能力进行投资决策
    """
    story.append(Paragraph(risk_text, styles['Normal']))
    
    # 构建PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer

def validate_etf_code(etf_code: str) -> bool:
    """
    验证ETF代码格式
    
    Args:
        etf_code: ETF代码
    
    Returns:
        是否有效
    """
    if not etf_code:
        return False
    
    # 移除空格
    code = etf_code.strip().upper()
    
    # 检查常见格式
    patterns = [
        r'^\d{6}\.(SS|SZ)$',  # A股ETF
        r'^\^[A-Z]+$',  # 指数
        r'^[A-Z]{1,5}$',  # 美股ETF
        r'^\d{6}$'  # 纯数字代码
    ]
    
    import re
    for pattern in patterns:
        if re.match(pattern, code):
            return True
    
    return False

def format_etf_code(etf_code: str) -> str:
    """
    格式化ETF代码
    
    Args:
        etf_code: 原始ETF代码
    
    Returns:
        格式化后的代码
    """
    if not etf_code:
        return ""
    
    code = etf_code.strip().upper()
    
    # 如果是A股ETF数字代码
    if code.isdigit() and len(code) == 6:
        if code.startswith('51') or code.startswith('15'):
            return f"{code}.SS"
        elif code.startswith('159'):
            return f"{code}.SZ"
    
    return code

def validate_us_stock_code(stock_code: str) -> bool:
    """
    验证美股代码格式
    
    Args:
        stock_code: 股票代码
    
    Returns:
        是否有效
    """
    if not stock_code:
        return False
    
    code = stock_code.strip().upper()
    
    # 美股代码通常为1-5个大写字母
    # 有些包含连字符（如BRK-B）
    if re.match(r'^[A-Z]{1,5}(-[A-Z])?$', code):
        return True
    
    return False
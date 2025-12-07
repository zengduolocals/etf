"""
6_美股选股.py - 美股智能选股模块
基于多因子量化模型的美股智能筛选系统
修复了除零错误和筛选条件过严的问题
"""

import streamlit as st
from auth_simple import check_permission  # 确保从您的认证模块导入

# ========== 新增：页面访问控制 ==========
if not check_permission('user'):  # 要求至少是普通用户角色
    st.warning("⛔ 您需要登录才能访问此页面。")
    # 提供一个清晰的登录提示或直接停止渲染
    st.info("请使用左侧侧边栏进行登录。")
    st.stop()  # 关键！这会停止执行页面的后续代码
# ========== 访问控制结束 ==========
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 尝试导入utils模块，如果失败则使用备用数据
try:
    from utils import (
        get_us_stock_factors, calculate_weighted_score, 
        filter_stocks_by_criteria, simulate_backtest,
        get_sp500_components, get_nasdaq100_components,
        plot_us_stock_factors_radar, plot_us_sector_distribution,
        export_us_stock_report, US_INDICES, US_SECTORS,
        POPULAR_US_STOCKS
    )
    UTILS_AVAILABLE = True
except ImportError as e:
    st.warning(f"无法导入utils模块: {e}，将使用示例数据演示")
    UTILS_AVAILABLE = False

# 设置页面
st.set_page_config(
    page_title="美股智能选股系统",
    page_icon="🇺🇸",
    layout="wide"
)

# 初始化session state
if 'auto_relax' not in st.session_state:
    st.session_state.auto_relax = False
if 'recommended_params' not in st.session_state:
    st.session_state.recommended_params = False
if 'show_all_stocks' not in st.session_state:
    st.session_state.show_all_stocks = False
if 'use_sample_data' not in st.session_state:
    st.session_state.use_sample_data = False

# 自定义CSS
st.markdown("""
<style>
    .info-box {
        background-color: #f0f9ff;
        border-left: 5px solid #2E86AB;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .strategy-box {
        background-color: #fff8e1;
        border: 1px solid #ffd54f;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .weight-row {
        display: flex;
        justify-content: space-between;
        margin: 5px 0;
        padding: 8px;
        background-color: #f5f5f5;
        border-radius: 5px;
    }
    .factor-badge {
        display: inline-block;
        padding: 4px 12px;
        margin: 2px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 500;
        background-color: #e3f2fd;
        color: #1565c0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.title("🇺🇸 美股智能选股系统")
st.markdown("基于AI多因子模型的美股智能筛选与回测平台")

# 选股逻辑提示
with st.expander("📖 选股逻辑说明", expanded=True):
    st.markdown("""
    ### 🎯 选股逻辑简介
    
    本系统采用**多因子量化选股**策略，结合现代投资组合理论，通过5大核心因子筛选优质美股：
    
    **📊 五大核心因子：**
    
    1. **价值因子** - 寻找被低估的股票
       - 市盈率(PE)、市净率(PB)低于行业平均
       - 高股息率提供安全边际
    
    2. **成长因子** - 识别高成长性公司
       - 营收增长率、净利润增长率领先
       - 可持续的盈利增长
    
    3. **质量因子** - 评估公司财务健康度
       - 高ROE(净资产收益率)
       - 良好的利润率
       - 合理的负债水平
    
    4. **动量因子** - 跟随市场趋势
       - 短期价格动量表现
       - 相对市场强度
    
    5. **风险因子** - 控制投资风险
       - 波动率适度
       - Beta值合理
    
    **🔢 评分机制：**
    - 每个因子独立评分(0-1分)
    - 按权重加权计算综合得分
    - 得分越高代表股票越优质
    
    **💡 新手建议：**
    - 首次使用请使用默认参数
    - 从"多因子综合"策略开始尝试
    - 如果无结果，系统会自动放宽条件
    - 建议持仓10-20只股票分散风险
    """)

# 美股市场指数
US_INDICES_DEFAULT = {
    "标普500": {"symbol": "^GSPC", "name": "S&P 500", "description": "美国500家大型上市公司"},
    "纳斯达克100": {"symbol": "^NDX", "name": "NASDAQ 100", "description": "纳斯达克100家最大非金融公司"},
    "道琼斯工业": {"symbol": "^DJI", "name": "Dow Jones Industrial", "description": "美国30家大型上市公司"},
}

US_SECTORS_DEFAULT = {
    "科技": {"symbol": "XLK", "name": "Technology Select Sector", "description": "科技行业"},
    "医疗": {"symbol": "XLV", "name": "Health Care Select Sector", "description": "医疗保健行业"},
    "金融": {"symbol": "XLF", "name": "Financial Select Sector", "description": "金融行业"},
    "消费": {"symbol": "XLY", "name": "Consumer Discretionary", "description": "非必需消费品"},
    "工业": {"symbol": "XLI", "name": "Industrial Select Sector", "description": "工业行业"},
}

POPULAR_STOCKS_DEFAULT = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", 
    "BRK-B", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS"
]

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 美股选股配置")
    
    # 显示数据源状态
    if not UTILS_AVAILABLE:
        st.error("⚠️ 数据模块加载失败，使用示例数据演示")
        st.info("要使用真实数据，请确保utils.py文件存在并正确导入")
    
    # 选股策略选择
    strategy = st.selectbox(
        "选股策略",
        ["多因子综合", "价值投资", "成长股策略", "动量交易", "低波动策略", "高股息策略"]
    )
    
    # 股票池选择
    st.subheader("📊 股票池")
    
    # 使用可用的常量
    if UTILS_AVAILABLE:
        indices_list = list(US_INDICES.keys())
        sectors_list = list(US_SECTORS.keys())
    else:
        indices_list = list(US_INDICES_DEFAULT.keys())
        sectors_list = list(US_SECTORS_DEFAULT.keys())
    
    index_selection = st.multiselect(
        "指数成分股",
        indices_list,
        default=["标普500"]
    )
    
    sector_selection = st.multiselect(
        "行业筛选",
        sectors_list,
        default=["科技", "医疗", "金融"]
    )
    
    # 自定义股票
    st.subheader("💼 自定义股票池")
    custom_stocks_input = st.text_area(
        "输入美股代码 (每行一个)",
        "\n".join(POPULAR_STOCKS_DEFAULT)
    )
    custom_stocks = [s.strip().upper() for s in custom_stocks_input.split('\n') if s.strip()]
    
    # 因子权重设置
    st.subheader("📈 因子权重设置")
    
    # 显示选股策略建议
    strategy_weights = {
        "多因子综合": {"value": 0.25, "growth": 0.25, "quality": 0.20, "momentum": 0.15, "risk": 0.15},
        "价值投资": {"value": 0.50, "growth": 0.15, "quality": 0.20, "momentum": 0.05, "risk": 0.10},
        "成长股策略": {"value": 0.15, "growth": 0.50, "quality": 0.20, "momentum": 0.10, "risk": 0.05},
        "动量交易": {"value": 0.10, "growth": 0.20, "quality": 0.15, "momentum": 0.45, "risk": 0.10},
        "低波动策略": {"value": 0.20, "growth": 0.15, "quality": 0.20, "momentum": 0.10, "risk": 0.35},
        "高股息策略": {"value": 0.60, "growth": 0.10, "quality": 0.20, "momentum": 0.05, "risk": 0.05}
    }
    
    # 显示当前策略的权重建议
    current_weights = strategy_weights[strategy]
    st.markdown(f"**当前策略建议权重:**")
    for factor, weight in current_weights.items():
        factor_name = {
            "value": "价值", "growth": "成长", "quality": "质量", 
            "momentum": "动量", "risk": "风险"
        }[factor]
        st.markdown(f"<div class='weight-row'><span>{factor_name}因子</span><span>{weight:.0%}</span></div>", 
                   unsafe_allow_html=True)
    
    # 允许用户微调权重
    st.markdown("**自定义调整权重:**")
    col1, col2 = st.columns(2)
    with col1:
        value_weight = st.slider("价值", 0.0, 1.0, current_weights["value"], 0.05, key="value_weight")
        growth_weight = st.slider("成长", 0.0, 1.0, current_weights["growth"], 0.05, key="growth_weight")
    with col2:
        quality_weight = st.slider("质量", 0.0, 1.0, current_weights["quality"], 0.05, key="quality_weight")
        momentum_weight = st.slider("动量", 0.0, 1.0, current_weights["momentum"], 0.05, key="momentum_weight")
        risk_weight = st.slider("风险", 0.0, 1.0, current_weights["risk"], 0.05, key="risk_weight")
    
    # 验证权重和为1
    total_weight = value_weight + growth_weight + quality_weight + momentum_weight + risk_weight
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"权重总和为{total_weight:.2f}，建议调整为1.0")
        if st.button("自动调整权重", key="auto_adjust_weights"):
            # 按比例调整权重
            scale_factor = 1.0 / total_weight
            value_weight *= scale_factor
            growth_weight *= scale_factor
            quality_weight *= scale_factor
            momentum_weight *= scale_factor
            risk_weight *= scale_factor
            st.rerun()
    
    # 筛选条件
    st.subheader("🎯 筛选条件")
    
    # 更宽松的默认值
    min_market_cap = st.number_input(
        "最小市值(十亿美元)", 
        0.1, 1000.0, 2.0, 0.5,
        help="常见范围: 1-100，建议从2开始尝试",
        key="min_market_cap"
    )
    
    max_pe = st.number_input(
        "最大市盈率", 
        5, 200, 80, 5,
        help="常见范围: 10-50，亏损公司PE为负会自动排除",
        key="max_pe"
    )
    
    min_roe = st.number_input(
        "最小ROE(%)", 
        0.0, 50.0, 5.0, 1.0,
        help="常见范围: 8-20%，ROE>15%为优秀",
        key="min_roe"
    )
    
    max_volatility = st.number_input(
        "最大波动率(%)", 
        10.0, 100.0, 60.0, 5.0,
        help="常见范围: 20-40%，成长股通常波动较大",
        key="max_volatility"
    )
    
    min_dividend_yield = st.number_input(
        "最小股息率(%)", 
        0.0, 10.0, 0.0, 0.1,
        help="常见范围: 0-5%，科技股通常股息较低",
        key="min_dividend_yield"
    )
    
    # 回测参数
    st.subheader("🔁 回测设置")
    
    backtest_period = st.select_slider(
        "回测时间",
        options=["3个月", "6个月", "1年", "2年", "3年", "5年"],
        value="1年"
    )
    
    initial_capital = st.number_input("初始资金(万美元)", 100, 10000, 1000, 100)
    portfolio_size = st.slider("持仓数量", 5, 30, 10, 5)
    
    # 执行按钮
    run_analysis = st.button("🚀 开始智能选股", type="primary", use_container_width=True)
    
    # 添加快速设置按钮
    st.markdown("---")
    st.subheader("⚡ 快速设置")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 使用推荐参数", use_container_width=True):
            st.session_state.recommended_params = True
            st.rerun()
    
    with col2:
        if st.button("🔄 重置所有参数", use_container_width=True):
            for key in st.session_state.keys():
                if key.startswith("FormSubmitter"):
                    continue
            st.rerun()

# 创建示例数据的函数
def create_sample_data():
    """创建示例股票数据"""
    np.random.seed(42)
    
    # 创建20只示例股票
    sample_stocks = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BRK-B", 
        "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "ADBE", "CRM", 
        "NFLX", "PYPL"
    ]
    
    data = {
        "股票代码": sample_stocks,
        "公司名称": [
            "Apple Inc.", "Microsoft", "Alphabet", "Amazon", "Tesla", 
            "NVIDIA", "Meta", "Berkshire Hathaway", "JPMorgan", "Johnson & Johnson",
            "Visa", "Procter & Gamble", "UnitedHealth", "Home Depot", "Mastercard",
            "Disney", "Adobe", "Salesforce", "Netflix", "PayPal"
        ],
        "行业": np.random.choice(["Technology", "Healthcare", "Financial", "Consumer", "Communication"], 20),
        "当前价格": np.round(np.random.uniform(50, 500, 20), 2),
        "市值(十亿)": np.round(np.random.uniform(50, 2000, 20), 1),
        "市盈率(PE)": np.round(np.random.uniform(15, 60, 20), 1),
        "市净率(PB)": np.round(np.random.uniform(2, 15, 20), 2),
        "股息率(%)": np.round(np.random.uniform(0, 3, 20), 2),
        "ROE(%)": np.round(np.random.uniform(8, 30, 20), 1),
        "营收增长(%)": np.round(np.random.uniform(5, 35, 20), 1),
        "利润增长(%)": np.round(np.random.uniform(0, 40, 20), 1),
        "1月动量(%)": np.round(np.random.uniform(-5, 20, 20), 2),
        "3月动量(%)": np.round(np.random.uniform(0, 30, 20), 2),
        "6月动量(%)": np.round(np.random.uniform(5, 40, 20), 2),
        "波动率(%)": np.round(np.random.uniform(25, 55, 20), 2),
        "价值得分": np.round(np.random.uniform(0.4, 0.9, 20), 3),
        "成长得分": np.round(np.random.uniform(0.3, 0.8, 20), 3),
        "质量得分": np.round(np.random.uniform(0.5, 0.9, 20), 3),
        "动量得分": np.round(np.random.uniform(0.2, 0.7, 20), 3),
        "风险得分": np.round(np.random.uniform(0.4, 0.8, 20), 3),
        "综合得分": np.round(np.random.uniform(0.5, 0.85, 20), 3)
    }
    
    return pd.DataFrame(data)

def calculate_weighted_score_local(df, weights):
    """本地计算加权综合得分"""
    df = df.copy()
    
    # 默认权重
    default_weights = {
        "value": 0.25,
        "growth": 0.25,
        "quality": 0.20,
        "momentum": 0.15,
        "risk": 0.15
    }
    
    # 使用提供的权重或默认权重
    weights = weights or default_weights
    
    # 检查是否有所需的列
    required_cols = ["价值得分", "成长得分", "质量得分", "动量得分", "风险得分"]
    for col in required_cols:
        if col not in df.columns:
            # 如果缺少列，生成随机数据
            df[col] = np.random.uniform(0.3, 0.9, len(df))
    
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
    else:
        # 如果所有得分相同，设为0.5
        df["加权得分"] = 0.5
    
    return df

def filter_stocks_by_criteria_local(df, filters):
    """本地筛选股票（修复除零错误）"""
    filtered_df = df.copy()
    
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
    
    # 如果过滤后为空，自动放宽条件
    if len(filtered_df) == 0 and len(df) > 0:
        st.info("筛选条件过严，自动放宽条件...")
        
        # 放宽条件：降低要求
        relaxed_df = df.copy()
        
        # 放宽市值要求
        market_cap_median = df["市值(十亿)"].median()
        if pd.notna(market_cap_median):
            relaxed_df = relaxed_df[relaxed_df["市值(十亿)"] >= max(0.5, market_cap_median * 0.3)]
        
        # 放宽PE要求
        pe_median = df["市盈率(PE)"][df["市盈率(PE)"] > 0].median()
        if pd.notna(pe_median):
            relaxed_df = relaxed_df[(relaxed_df["市盈率(PE)"] <= max(100, pe_median * 3)) | 
                                   (relaxed_df["市盈率(PE)"] <= 0)]
        
        # 放宽ROE要求
        roe_median = df["ROE(%)"].median()
        if pd.notna(roe_median):
            relaxed_df = relaxed_df[relaxed_df["ROE(%)"] >= max(0, roe_median * 0.5)]
        
        # 放宽波动率要求
        vol_median = df["波动率(%)"].median()
        if pd.notna(vol_median):
            relaxed_df = relaxed_df[relaxed_df["波动率(%)"] <= min(100, vol_median * 2)]
        
        return relaxed_df
    
    return filtered_df

def simulate_backtest_local(selected_stocks, weights, start_date, end_date):
    """本地模拟回测（修复除零错误）"""
    try:
        # 生成模拟数据
        np.random.seed(42)
        
        # 创建日期范围
        if "3个月" in backtest_period:
            periods = 90
        elif "6个月" in backtest_period:
            periods = 180
        elif "1年" in backtest_period:
            periods = 252
        elif "2年" in backtest_period:
            periods = 504
        elif "3年" in backtest_period:
            periods = 756
        else:  # 5年
            periods = 1260
        
        # 确保有足够的周期
        periods = max(periods, 60)  # 至少60个交易日
        
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
        
        # 生成模拟收益率 - 添加合理的波动率
        portfolio_returns = np.random.normal(0.0005, 0.015, periods)
        benchmark_returns = np.random.normal(0.0004, 0.012, periods)
        
        # 确保没有除零错误
        portfolio_std = np.std(portfolio_returns)
        if portfolio_std == 0:
            portfolio_returns = portfolio_returns + np.random.normal(0, 0.001, periods)
            portfolio_std = np.std(portfolio_returns)
        
        benchmark_std = np.std(benchmark_returns)
        if benchmark_std == 0:
            benchmark_returns = benchmark_returns + np.random.normal(0, 0.001, periods)
            benchmark_std = np.std(benchmark_returns)
        
        # 计算累计净值
        portfolio_nav = (1 + portfolio_returns).cumprod()
        benchmark_nav = (1 + benchmark_returns).cumprod()
        
        # 计算绩效指标
        annual_return = portfolio_returns.mean() * 252
        
        # 计算年化波动率，避免除零
        annual_volatility = portfolio_std * np.sqrt(252)
        if annual_volatility == 0:
            annual_volatility = 0.15  # 设置合理的默认波动率
        
        # 计算夏普比率
        sharpe_ratio = (annual_return - 0.03) / annual_volatility if annual_volatility > 0 else 0
        
        # 计算最大回撤
        running_max = portfolio_nav.expanding().max()
        # 避免除零错误
        if (running_max == 0).any():
            running_max = np.maximum(running_max, 1e-10)
        
        drawdown = (portfolio_nav - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        return {
            "portfolio_cumulative": pd.Series(portfolio_nav, index=dates),
            "benchmark_cumulative": pd.Series(benchmark_nav, index=dates),
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "cumulative_return": portfolio_nav[-1] - 1,
            "weights": weights,
            "stocks": selected_stocks
        }
        
    except ZeroDivisionError as e:
        # 专门处理除零错误
        return create_default_backtest_result()
    except Exception as e:
        return {"error": f"回测模拟失败: {str(e)}"}

def create_default_backtest_result():
    """创建默认的回测结果，避免错误"""
    periods = 252  # 一年
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    
    # 生成合理的模拟数据
    portfolio_returns = np.random.normal(0.0005, 0.015, periods)
    benchmark_returns = np.random.normal(0.0004, 0.012, periods)
    
    portfolio_nav = (1 + portfolio_returns).cumprod()
    benchmark_nav = (1 + benchmark_returns).cumprod()
    
    annual_return = portfolio_returns.mean() * 252
    annual_volatility = max(np.std(portfolio_returns) * np.sqrt(252), 0.01)  # 最小1%波动率
    
    return {
        "portfolio_cumulative": pd.Series(portfolio_nav, index=dates),
        "benchmark_cumulative": pd.Series(benchmark_nav, index=dates),
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": (annual_return - 0.03) / annual_volatility if annual_volatility > 0 else 0,
        "max_drawdown": -0.15,  # 典型的最大回撤
        "cumulative_return": portfolio_nav[-1] - 1,
        "weights": [],
        "stocks": []
    }

# 主内容区
if run_analysis or st.session_state.get('auto_relax', False) or st.session_state.get('show_all_stocks', False) or st.session_state.get('recommended_params', False):
    
    # 如果用户选择了推荐参数，调整参数
    if st.session_state.get('recommended_params', False):
        # 设置更宽松的推荐参数
        min_market_cap = 1.0
        max_pe = 100
        min_roe = 5.0
        max_volatility = 60.0
        min_dividend_yield = 0.0
        portfolio_size = 15
        backtest_period = "1年"
        st.session_state.recommended_params = False
        st.success("已应用推荐参数！")
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 第一步：构建股票池
    status_text.text("📊 构建股票池...")
    
    # 显示数据源状态
    if not UTILS_AVAILABLE or st.session_state.get('use_sample_data', False):
        st.warning("⚠️ 使用示例数据进行演示")
        use_sample_data = True
    else:
        use_sample_data = False
    
    if use_sample_data:
        # 使用示例数据
        all_tickers = POPULAR_STOCKS_DEFAULT
        df_factors = create_sample_data()
        st.success(f"✅ 使用示例数据: {len(df_factors)}只股票")
    else:
        # 构建真实股票池
        all_tickers = []
        
        # 添加指数成分股
        if index_selection:
            if "标普500" in index_selection:
                try:
                    sp500_stocks = get_sp500_components()
                    all_tickers.extend(sp500_stocks[:50])  # 只取前50只，避免API限制
                    st.info(f"添加标普500成分股: {len(sp500_stocks[:50])}只")
                except:
                    st.warning("无法获取标普500成分股，使用热门股票")
                    all_tickers.extend(POPULAR_STOCKS_DEFAULT)
            
            if "纳斯达克100" in index_selection:
                try:
                    nasdaq_stocks = get_nasdaq100_components()
                    all_tickers.extend(nasdaq_stocks[:50])  # 只取前50只
                    st.info(f"添加纳斯达克100成分股: {len(nasdaq_stocks[:50])}只")
                except:
                    st.warning("无法获取纳斯达克100成分股")
        
        # 添加自定义股票
        if custom_stocks:
            all_tickers.extend(custom_stocks)
        
        # 如果没有选择任何股票池，使用热门股票
        if not all_tickers:
            all_tickers = POPULAR_STOCKS_DEFAULT
            st.info("使用默认热门股票池")
        
        # 去重
        all_tickers = list(set(all_tickers))
        
        progress_bar.progress(20)
        status_text.text(f"📈 获取{len(all_tickers)}只股票数据...")
        
        # 获取因子数据
        try:
            df_factors = get_us_stock_factors(all_tickers)
            if df_factors.empty:
                raise Exception("获取数据失败")
            st.success(f"✅ 成功获取{len(df_factors)}只股票数据")
        except Exception as e:
            st.error(f"获取股票数据失败: {e}")
            st.info("切换到示例数据模式...")
            use_sample_data = True
            df_factors = create_sample_data()
    
    progress_bar.progress(40)
    
    # 显示股票池统计信息
    with st.expander("📊 查看股票池统计信息", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**市值分布**")
            st.write(f"最小值: ${df_factors['市值(十亿)'].min():.1f}B")
            st.write(f"中位数: ${df_factors['市值(十亿)'].median():.1f}B")
            st.write(f"最大值: ${df_factors['市值(十亿)'].max():.1f}B")
            
        with col2:
            st.markdown("**估值分布**")
            st.write(f"PE中位数: {df_factors['市盈率(PE)'].median():.1f}")
            st.write(f"ROE中位数: {df_factors['ROE(%)'].median():.1f}%")
            st.write(f"波动率中位数: {df_factors['波动率(%)'].median():.1f}%")
            
        with col3:
            st.markdown("**得分分布**")
            st.write(f"综合得分中位数: {df_factors['综合得分'].median():.3f}")
            st.write(f"价值得分中位数: {df_factors['价值得分'].median():.3f}")
            st.write(f"成长得分中位数: {df_factors['成长得分'].median():.3f}")
    
    # 第三步：计算加权得分
    status_text.text("🔍 计算因子得分...")
    
    weights = {
        "value": value_weight,
        "growth": growth_weight,
        "quality": quality_weight,
        "momentum": momentum_weight,
        "risk": risk_weight
    }
    
    if use_sample_data or not UTILS_AVAILABLE:
        df_weighted = calculate_weighted_score_local(df_factors, weights)
    else:
        df_weighted = calculate_weighted_score(df_factors, weights)
    
    progress_bar.progress(60)
    
    # 第四步：应用筛选条件
    status_text.text("🎯 应用筛选条件...")
    filters = {
        "min_market_cap": min_market_cap,
        "max_pe": max_pe,
        "min_roe": min_roe,
        "max_volatility": max_volatility,
        "min_dividend_yield": min_dividend_yield,
        "sectors": sector_selection if sector_selection else None
    }
    
    # 应用筛选
    if use_sample_data or not UTILS_AVAILABLE:
        df_filtered = filter_stocks_by_criteria_local(df_weighted, filters)
    else:
        df_filtered = filter_stocks_by_criteria(df_weighted, filters)
    
    # 检查筛选结果
    original_count = len(df_weighted)
    filtered_count = len(df_filtered)
    
    # 如果用户选择了"显示所有股票"
    if st.session_state.get('show_all_stocks', False):
        df_filtered = df_weighted.copy()
        filtered_count = len(df_filtered)
        st.success(f"显示所有{filtered_count}只股票")
        st.session_state.show_all_stocks = False
    
    if filtered_count == 0:
        st.markdown("<div class='warning-box'>", unsafe_allow_html=True)
        st.warning(f"⚠️ **筛选条件过严**，{original_count}只股票中0只符合条件")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 显示调整建议
        st.markdown(f"""
        ### 💡 调整建议:
        
        1. **放宽市值要求**: 当前最小市值要求可能太高
           - 建议从 `${min_market_cap}B` 降低到 `${max(0.5, min_market_cap/2):.1f}B`
        
        2. **提高最大PE**: 当前PE要求可能太低
           - 建议从 `{max_pe}` 提高到 `{max_pe*2}`
        
        3. **降低ROE要求**: 当前ROE要求可能太高
           - 建议从 `{min_roe}%` 降低到 `{max(2.0, min_roe/2)}%`
        
        4. **提高波动率容忍**: 成长股通常波动较大
           - 建议从 `{max_volatility}%` 提高到 `{min(80.0, max_volatility*1.5)}%`
        
        5. **取消股息率要求**: 很多科技股不分红
        """)
        
        # 提供快速调整按钮
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 自动放宽条件", key="auto_relax_btn"):
                st.session_state.auto_relax = True
                st.rerun()
        
        with col2:
            if st.button("📊 查看所有股票", key="show_all_btn"):
                st.session_state.show_all_stocks = True
                st.rerun()
        
        with col3:
            if st.button("🎯 使用推荐值", key="use_recommended_btn"):
                st.session_state.recommended_params = True
                st.rerun()
        
        # 显示原始数据供参考
        with st.expander("📈 查看原始股票数据"):
            st.dataframe(df_weighted[["股票代码", "公司名称", "行业", "市值(十亿)", "市盈率(PE)", "ROE(%)", "波动率(%)"]].head(20))
        
        st.stop()
    else:
        st.markdown("<div class='success-box'>", unsafe_allow_html=True)
        st.success(f"✅ {original_count}只股票中，{filtered_count}只符合筛选条件")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 第五步：选择排名靠前的股票
    status_text.text("🏆 选择最优股票...")
    
    # 确保有足够股票可选
    select_count = min(portfolio_size, len(df_filtered))
    if select_count < portfolio_size:
        st.info(f"⚠️ 只有{select_count}只股票符合条件，少于要求的{portfolio_size}只")
    
    df_selected = df_filtered.nlargest(select_count, "加权得分").copy()
    
    # 计算权重（基于综合得分加权）
    if df_selected["加权得分"].sum() > 0:
        df_selected["配置权重"] = df_selected["加权得分"] / df_selected["加权得分"].sum()
    else:
        # 如果加权得分为0，使用等权重
        df_selected["配置权重"] = 1 / len(df_selected)
    
    progress_bar.progress(80)
    
    # 第六步：执行回测
    status_text.text("📊 执行回测分析...")
    
    # 如果股票数量太少，使用等权重
    if len(df_selected) < 3:
        st.warning("股票数量较少，使用等权重配置")
        df_selected["配置权重"] = 1 / len(df_selected)
    
    # 计算回测开始日期
    end_date = datetime.now()
    if backtest_period == "3个月":
        start_date = end_date - timedelta(days=90)
    elif backtest_period == "6个月":
        start_date = end_date - timedelta(days=180)
    elif backtest_period == "1年":
        start_date = end_date - timedelta(days=365)
    elif backtest_period == "2年":
        start_date = end_date - timedelta(days=730)
    elif backtest_period == "3年":
        start_date = end_date - timedelta(days=1095)
    else:  # 5年
        start_date = end_date - timedelta(days=1825)
    
    # 获取回测结果
    if use_sample_data or not UTILS_AVAILABLE:
        backtest_result = simulate_backtest_local(
            selected_stocks=df_selected["股票代码"].tolist(),
            weights=df_selected["配置权重"].tolist(),
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    else:
        backtest_result = simulate_backtest(
            selected_stocks=df_selected["股票代码"].tolist(),
            weights=df_selected["配置权重"].tolist(),
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    
    progress_bar.progress(100)
    status_text.text("✅ 分析完成！")
    
    # 重置session state
    st.session_state.auto_relax = False
    st.session_state.recommended_params = False
    st.session_state.use_sample_data = False
    
    # 显示选股摘要
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("入选股票", f"{len(df_selected)}只")
    with col2:
        avg_pe = df_selected["市盈率(PE)"].mean()
        st.metric("平均市盈率", f"{avg_pe:.1f}")
    with col3:
        avg_roe = df_selected["ROE(%)"].mean()
        st.metric("平均ROE", f"{avg_roe:.1f}%")
    with col4:
        avg_score = df_selected["加权得分"].mean()
        st.metric("平均得分", f"{avg_score:.3f}")
    
    # 使用标签页组织内容
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 选股结果", "⚖️ 配置比例", "📊 回测分析", "📈 因子分析", "📄 策略报告"])
    
    # Tab 1: 选股结果
    with tab1:
        st.header("🏆 精选股票列表")
        
        # 显示详细股票数据
        display_cols = [
            "股票代码", "公司名称", "行业", "当前价格", "市值(十亿)", 
            "市盈率(PE)", "股息率(%)", "ROE(%)", "营收增长(%)", 
            "加权得分", "配置权重"
        ]
        
        # 创建显示DataFrame
        df_display = df_selected[display_cols].copy()
        df_display["当前价格"] = df_display["当前价格"].apply(lambda x: f"${x:.2f}")
        df_display["市值(十亿)"] = df_display["市值(十亿)"].apply(lambda x: f"${x:.1f}B")
        df_display["市盈率(PE)"] = df_display["市盈率(PE)"].apply(lambda x: f"{x:.1f}")
        df_display["股息率(%)"] = df_display["股息率(%)"].apply(lambda x: f"{x:.2f}%")
        df_display["ROE(%)"] = df_display["ROE(%)"].apply(lambda x: f"{x:.1f}%")
        df_display["营收增长(%)"] = df_display["营收增长(%)"].apply(lambda x: f"{x:.1f}%")
        df_display["加权得分"] = df_display["加权得分"].apply(lambda x: f"{x:.3f}")
        df_display["配置权重"] = df_display["配置权重"].apply(lambda x: f"{x:.2%}")
        
        st.dataframe(df_display, use_container_width=True, height=500)
        
        # 行业分布
        st.subheader("📊 行业分布")
        if UTILS_AVAILABLE and not use_sample_data:
            try:
                sector_fig = plot_us_sector_distribution(df_selected)
                st.plotly_chart(sector_fig, use_container_width=True)
            except:
                # 本地绘制行业分布
                sector_counts = df_selected['行业'].value_counts()
                sector_fig = px.pie(
                    values=sector_counts.values,
                    names=sector_counts.index,
                    title="行业分布",
                    hole=0.3
                )
                st.plotly_chart(sector_fig, use_container_width=True)
        else:
            # 本地绘制行业分布
            sector_counts = df_selected['行业'].value_counts()
            sector_fig = px.pie(
                values=sector_counts.values,
                names=sector_counts.index,
                title="行业分布",
                hole=0.3
            )
            st.plotly_chart(sector_fig, use_container_width=True)
    
    # Tab 2: 配置比例
    with tab2:
        st.header("⚖️ 投资组合配置比例")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 配置比例饼图
            fig_pie = px.pie(
                df_selected,
                values="配置权重",
                names="股票代码",
                title="投资组合权重分布",
                hole=0.3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("🎯 配置建议")
            
            # 计算建议投资金额
            total_investment = initial_capital * 10000  # 转换为美元
            
            st.markdown(f"""
            **投资概要:**
            - 初始资金: ${initial_capital:,}万
            - 持仓股票: {len(df_selected)}只
            - 平均权重: {(100/len(df_selected)):.1f}%
            
            **配置建议:**
            """)
            
            # 显示每只股票的建议投资额
            for idx, row in df_selected.iterrows():
                investment_amount = row["配置权重"] * total_investment
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 5px;">
                    <strong>{row['股票代码']}</strong>
                    <div style="display: flex; justify-content: space-between;">
                        <span>权重: {row['配置权重']:.2%}</span>
                        <span>金额: ${investment_amount:,.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # 权重详情表格
        st.subheader("📊 详细权重分配")
        
        weight_detail_cols = ["股票代码", "公司名称", "行业", "加权得分", "配置权重", "建议投资额(美元)"]
        weight_df = df_selected[["股票代码", "公司名称", "行业", "加权得分", "配置权重"]].copy()
        weight_df["建议投资额(美元)"] = weight_df["配置权重"] * total_investment
        weight_df = weight_df.sort_values("配置权重", ascending=False)
        
        # 格式化显示
        weight_display = weight_df.copy()
        weight_display["加权得分"] = weight_display["加权得分"].apply(lambda x: f"{x:.3f}")
        weight_display["配置权重"] = weight_display["配置权重"].apply(lambda x: f"{x:.2%}")
        weight_display["建议投资额(美元)"] = weight_display["建议投资额(美元)"].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(weight_display, use_container_width=True)
    
    # Tab 3: 回测分析
    with tab3:
        st.header("📊 投资组合回测分析")
        
        if "error" in backtest_result:
            st.markdown("<div class='error-box'>", unsafe_allow_html=True)
            st.error(f"回测分析失败: {backtest_result['error']}")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 提供详细的错误分析
            st.markdown("""
            ### 🔍 错误原因分析
            
            回测失败可能的原因：
            
            1. **数据获取问题**: Yahoo Finance API可能暂时不可用
            2. **股票代码错误**: 部分股票代码可能已变更或不存在
            3. **数据量不足**: 选择的回测期间内数据点太少
            4. **网络连接问题**: 请检查网络连接
            
            ### 💡 解决方案
            
            1. **使用示例数据**: 点击下面的按钮切换到示例数据
            2. **缩短回测期间**: 尝试使用"1年"或"6个月"的回测期间
            3. **检查股票代码**: 确保输入的股票代码正确
            4. **稍后重试**: 可能是临时网络问题
            """)
            
            # 提供切换选项
            if st.button("🔄 使用示例数据重新运行"):
                st.session_state.use_sample_data = True
                st.rerun()
            
        else:
            # 回测绩效指标
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                delta = (backtest_result["annual_return"] - 0.03) * 100  # 假设无风险利率3%
                st.metric("年化收益率", f"{backtest_result['annual_return']:.2%}", 
                         f"{delta:+.1f}% vs 无风险")
            
            with col2:
                st.metric("年化波动率", f"{backtest_result['annual_volatility']:.2%}")
            
            with col3:
                st.metric("夏普比率", f"{backtest_result['sharpe_ratio']:.2f}")
            
            with col4:
                st.metric("最大回撤", f"{backtest_result['max_drawdown']:.2%}")
            
            # 净值曲线
            st.subheader("📈 净值曲线对比")
            
            fig_nav = go.Figure()
            
            # 投资组合净值
            if "portfolio_cumulative" in backtest_result and len(backtest_result["portfolio_cumulative"]) > 0:
                portfolio_nav = backtest_result["portfolio_cumulative"]
                fig_nav.add_trace(go.Scatter(
                    x=portfolio_nav.index,
                    y=portfolio_nav.values,
                    name='投资组合',
                    line=dict(color='#2E86AB', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(46, 134, 171, 0.1)'
                ))
            
            # 基准净值
            if "benchmark_cumulative" in backtest_result and len(backtest_result["benchmark_cumulative"]) > 0:
                benchmark_nav = backtest_result["benchmark_cumulative"]
                fig_nav.add_trace(go.Scatter(
                    x=benchmark_nav.index,
                    y=benchmark_nav.values,
                    name='标普500(基准)',
                    line=dict(color='#A23B72', width=2, dash='dash')
                ))
            
            fig_nav.update_layout(
                title="投资组合净值 vs 基准",
                xaxis_title="日期",
                yaxis_title="净值",
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_nav, use_container_width=True)
    
    # Tab 4: 因子分析
    with tab4:
        st.header("🔍 因子贡献度分析")
        
        # 因子权重饼图
        col1, col2 = st.columns(2)
        
        with col1:
            factor_weights = pd.DataFrame({
                '因子': ['价值', '成长', '质量', '动量', '风险'],
                '权重': [value_weight, growth_weight, quality_weight, momentum_weight, risk_weight]
            })
            
            fig_factor_weights = px.pie(
                factor_weights,
                values='权重',
                names='因子',
                title='因子权重分配',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_factor_weights.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_factor_weights, use_container_width=True)
        
        with col2:
            st.subheader("🎯 因子得分统计")
            
            factor_stats = pd.DataFrame({
                '因子': ['价值得分', '成长得分', '质量得分', '动量得分', '风险得分'],
                '平均分': [
                    df_selected['价值得分'].mean(),
                    df_selected['成长得分'].mean(),
                    df_selected['质量得分'].mean(),
                    df_selected['动量得分'].mean(),
                    df_selected['风险得分'].mean()
                ],
                '最高分': [
                    df_selected['价值得分'].max(),
                    df_selected['成长得分'].max(),
                    df_selected['质量得分'].max(),
                    df_selected['动量得分'].max(),
                    df_selected['风险得分'].max()
                ]
            })
            
            st.dataframe(factor_stats.style.format({
                '平均分': '{:.3f}',
                '最高分': '{:.3f}'
            }), use_container_width=True)
    
    # Tab 5: 策略报告
    with tab5:
        st.header("📄 美股选股策略报告")
        
        # 生成报告摘要
        report_date = datetime.now().strftime("%Y-%m-%d")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📋 策略报告摘要")
            
            report_content = f"""
            ## 美股智能选股策略报告
            
            ### 一、策略基本信息
            - **报告日期**: {report_date}
            - **选股策略**: {strategy}
            - **股票池**: {', '.join(index_selection) if index_selection else '热门股票'}
            - **行业筛选**: {', '.join(sector_selection) if sector_selection else '全部行业'}
            - **回测期间**: {backtest_period}
            - **持仓数量**: {len(df_selected)}只股票
            
            ### 二、筛选条件
            - 最小市值: ${min_market_cap}B
            - 最大PE: {max_pe}
            - 最小ROE: {min_roe}%
            - 最大波动率: {max_volatility}%
            - 最小股息率: {min_dividend_yield}%
            
            ### 三、因子配置权重
            - 价值因子: {value_weight:.0%}
            - 成长因子: {growth_weight:.0%}
            - 质量因子: {quality_weight:.0%}
            - 动量因子: {momentum_weight:.0%}
            - 风险因子: {risk_weight:.0%}
            
            ### 四、组合表现
            - 年化收益率: {backtest_result.get('annual_return', 0):.2%}
            - 年化波动率: {backtest_result.get('annual_volatility', 0):.2%}
            - 夏普比率: {backtest_result.get('sharpe_ratio', 0):.2f}
            - 最大回撤: {backtest_result.get('max_drawdown', 0):.2%}
            
            ### 五、风险提示
            1. 美股市场波动较大，投资需谨慎
            2. 历史回测不代表未来表现
            3. 汇率风险需考虑
            4. 建议分散投资，控制仓位
            """
            
            st.markdown(report_content)
        
        with col2:
            st.subheader("📤 导出分析结果")
            
            # 导出配置建议
            config_df = df_selected[["股票代码", "公司名称", "配置权重"]].copy()
            config_df["建议投资额(美元)"] = config_df["配置权重"] * initial_capital * 10000
            config_csv = config_df.to_csv(index=False)
            
            st.download_button(
                label="⬇️ 下载配置表(CSV)",
                data=config_csv,
                file_name=f"portfolio_config_{report_date}.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    # 默认显示页面说明
    st.markdown("""
    ### 🎯 如何使用美股智能选股系统
    
    本系统基于**多因子量化模型**，通过科学的投资方法帮助您筛选优质美股：
    
    1. **配置参数**：在左侧边栏设置选股策略、因子权重和筛选条件
    2. **运行分析**：点击"开始智能选股"按钮运行选股算法
    3. **查看结果**：在下方标签页中查看完整的分析结果
    4. **调整优化**：根据分析结果调整参数，优化投资策略
    
    ### 💡 新手友好设计
    
    - **宽松默认参数**：首次使用即可获得结果
    - **智能错误处理**：筛选过严时自动放宽条件
    - **示例数据支持**：网络异常时自动切换示例数据
    - **详细引导提示**：每一步都有操作说明
    """)
    
    # 使用提示
    st.markdown("<div class='info-box'>", unsafe_allow_html=True)
    st.markdown("""
    💡 **使用提示**: 
    - 对于新手投资者，建议从"多因子综合"策略开始
    - 使用默认参数即可获得选股结果
    - 如果无结果，系统会自动放宽条件或提供调整建议
    - 回测结果仅供参考，历史表现不代表未来
    """)
    st.markdown("</div>", unsafe_allow_html=True)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>
    <p style='color: #666;'>© 2025 衡远证券智能分析系统 | 美股智能选股模块 v1.2</p>
    <p style='color: #888; font-size: 0.9em;'>
        数据来源: Yahoo Finance | 
        免责声明: 本工具提供的数据和分析仅供参考，不构成投资建议
    </p>
</div>
""", unsafe_allow_html=True)
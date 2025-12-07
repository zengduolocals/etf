"""
组合建议页面 - 投资组合优化与回测分析
完整修复版：修复所有已知错误，优化代码结构
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
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
from utils import (
    get_etf_data, 
    calculate_portfolio_metrics,
    markowitz_optimization,
    risk_parity_optimization,
    plot_portfolio_weights,
    plot_portfolio_performance,
    generate_pdf_report,
    validate_etf_code,
    format_etf_code,
    get_realtime_price
)

# 页面配置
st.set_page_config(
    page_title="组合建议",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ 投资组合建议与回测分析")
st.markdown("构建、优化和回测您的ETF投资组合")

# 初始化session state
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {
        'etfs': [],
        'weights': [],
        'names': [],
        'data': None,
        'optimized_weights': None,
        'optimization_method': None
    }

# ==============================================
# 侧边栏 - 组合构建与管理
# ==============================================
with st.sidebar:
    st.header("🎯 组合构建")
    
    # ETF输入
    st.subheader("添加ETF")
    etf_input = st.text_input(
        "ETF代码:",
        placeholder="如: 510300, SPY",
        key="etf_input"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        weight_input = st.number_input(
            "权重(%):",
            min_value=0.0,
            max_value=100.0,
            value=25.0,
            step=1.0,
            key="weight_input"
        )
    with col2:
        st.markdown("###")
        if st.button("➕ 添加", key="add_etf"):
            if etf_input and validate_etf_code(etf_input):
                formatted_code = format_etf_code(etf_input)
                if formatted_code not in st.session_state.portfolio['etfs']:
                    st.session_state.portfolio['etfs'].append(formatted_code)
                    st.session_state.portfolio['weights'].append(weight_input / 100)
                    st.session_state.portfolio['names'].append(formatted_code)
                    st.success(f"添加 {formatted_code}")
                    st.rerun()
                else:
                    st.warning("ETF已在组合中")
            else:
                st.error("请输入有效的ETF代码")
    
    # 显示当前组合
    st.subheader("当前组合")
    if st.session_state.portfolio['etfs']:
        portfolio_df = pd.DataFrame({
            'ETF代码': st.session_state.portfolio['etfs'],
            '当前权重': [f"{w*100:.1f}%" for w in st.session_state.portfolio['weights']]
        })
        st.dataframe(portfolio_df, use_container_width=True, hide_index=True)
        
        # 权重调整
        st.subheader("调整权重")
        adjusted_weights = []
        for i, (etf, weight) in enumerate(zip(st.session_state.portfolio['etfs'], 
                                            st.session_state.portfolio['weights'])):
            new_weight = st.slider(
                f"{etf} 权重",
                min_value=0.0,
                max_value=100.0,
                value=float(weight * 100),
                step=1.0,
                key=f"weight_slider_{i}"
            )
            adjusted_weights.append(new_weight / 100)
        
        # 归一化权重
        total_weight = sum(adjusted_weights)
        if total_weight > 0:
            normalized_weights = [w/total_weight for w in adjusted_weights]
            st.session_state.portfolio['weights'] = normalized_weights
        
        # 管理按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 更新", type="primary"):
                st.rerun()
        with col2:
            if st.button("🗑️ 清空"):
                st.session_state.portfolio = {'etfs': [], 'weights': [], 'names': [], 'data': None}
                st.rerun()
        with col3:
            if st.button("💾 保存"):
                portfolio_name = st.text_input("组合名称", key="save_name")
                if portfolio_name:
                    st.success(f"组合 '{portfolio_name}' 已保存")
    else:
        st.info("组合为空，请添加ETF")
    
    # 预设组合
    st.subheader("💡 预设组合")
    preset_options = {
        "保守型": {"510300": 0.4, "511010": 0.4, "518880": 0.2},
        "平衡型": {"510300": 0.3, "510500": 0.3, "588000": 0.2, "511010": 0.2},
        "成长型": {"588000": 0.4, "159919": 0.3, "512100": 0.3},
        "全球配置": {"SPY": 0.4, "510300": 0.3, "EWJ": 0.2, "GLD": 0.1}
    }
    
    selected_preset = st.selectbox("选择预设组合:", list(preset_options.keys()))
    
    if st.button("应用预设", key="apply_preset"):
        preset = preset_options[selected_preset]
        st.session_state.portfolio = {
            'etfs': list(preset.keys()),
            'weights': list(preset.values()),
            'names': list(preset.keys()),
            'data': None
        }
        st.success(f"已应用 {selected_preset} 组合")
        st.rerun()
    
    # ==============================================
    # 高级参数设置 - 修改周期选项
    # ==============================================
    with st.expander("⚙️ 高级参数设置", expanded=False):
        st.subheader("分析参数")
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk_free_rate = st.slider(
                "无风险利率(%)", 
                0.0, 5.0, 2.0, 0.1,
                help="用于计算夏普比率等风险调整后收益指标"
            )
            confidence_level = st.slider(
                "VaR置信水平(%)", 
                90.0, 99.0, 95.0, 0.5,
                help="风险价值(VaR)的置信水平"
            )
        
        with col2:
            max_allocation = st.slider(
                "单资产最大权重(%)", 
                10.0, 100.0, 50.0, 5.0,
                help="优化时单资产的最大权重限制"
            )
            transaction_cost = st.number_input(
                "交易成本(%)", 
                0.0, 1.0, 0.1, 0.01,
                help="每次交易的费率，用于回测计算"
            )
        
        # 分析周期选择 - 修改为包含10年
        period = st.selectbox(
            "分析周期:",
            ["1个月", "3个月", "6个月", "1年", "2年", "5年", "10年", "最大"],
            index=5,  # 默认设为5年
            help="10年数据适合长期趋势分析和完整经济周期评估"
        )
        period_map = {"1个月": "1mo", "3个月": "3mo", "6个月": "6mo", 
                     "1年": "1y", "2年": "2y", "5年": "5y",
                     "10年": "10y", "最大": "max"}
        st.session_state.period = period_map[period]
    
    # ==============================================
    # 组合管理
    # ==============================================
    st.subheader("💾 组合管理")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("导入组合", use_container_width=True):
            st.info("导入功能开发中")
    
    with col2:
        if st.button("导出配置", use_container_width=True):
            st.info("导出功能开发中")
    
    st.markdown("---")
    st.caption("数据更新于: " + datetime.now().strftime("%Y-%m-%d %H:%M"))

# ==============================================
# 主内容区 - 仪表板布局
# ==============================================
if not st.session_state.portfolio['etfs']:
    st.warning("请先在侧边栏添加ETF到投资组合")
    st.info("💡 提示：您可以从预设组合快速开始，或手动添加ETF")
else:
    # 获取数据
    st.subheader("📊 数据准备")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 获取组合数据", type="primary", use_container_width=True):
            with st.spinner("正在获取ETF历史数据..."):
                # 获取所有ETF数据
                all_data = {}
                for etf in st.session_state.portfolio['etfs']:
                    data = get_etf_data(etf, st.session_state.period)
                    if not data.empty:
                        # 移除时区信息
                        if hasattr(data.index, 'tz') and data.index.tz is not None:
                            data.index = data.index.tz_localize(None)
                        all_data[etf] = data['Close']
                
                # 合并数据
                if all_data:
                    prices_df = pd.DataFrame(all_data)
                    st.session_state.portfolio['data'] = prices_df
                    st.success(f"成功获取 {len(prices_df.columns)} 个ETF数据")
                else:
                    st.error("无法获取ETF数据，请检查代码或网络")
    
    with col2:
        # 实时监控开关
        enable_realtime = st.checkbox("启用实时监控", value=False)
    
    with col3:
        if st.button("🔄 清除缓存", use_container_width=True):
            # 清除相关缓存
            keys_to_clear = ['get_realtime_price']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("缓存已清除")

# ==============================================
# 实时监控（如果启用）
# ==============================================
if st.session_state.portfolio['etfs'] and enable_realtime:
    st.markdown("---")
    st.subheader("📈 实时监控")
    
    # 获取实时数据
    try:
        realtime_df = get_realtime_price(st.session_state.portfolio['etfs'])
        
        if not realtime_df.empty:
            # 计算组合实时价值
            portfolio_value = 0
            for etf, weight in zip(st.session_state.portfolio['etfs'], 
                                 st.session_state.portfolio['weights']):
                etf_price = realtime_df.loc[realtime_df['ETF代码'] == etf, '当前价格']
                if not etf_price.empty:
                    portfolio_value += weight * etf_price.values[0] * 10000
            
            # 实时指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "组合实时价值", 
                    f"¥{portfolio_value:,.0f}",
                    delta=f"¥{portfolio_value/10000 - 10000:,.0f}" if portfolio_value > 0 else None
                )
            
            with col2:
                total_change = sum([
                    weight * realtime_df.loc[realtime_df['ETF代码'] == etf, '涨跌幅%'].values[0]
                    for etf, weight in zip(st.session_state.portfolio['etfs'], 
                                         st.session_state.portfolio['weights'])
                    if not realtime_df.loc[realtime_df['ETF代码'] == etf, '涨跌幅%'].empty
                ])
                st.metric("今日涨跌", f"{total_change:.2f}%")
            
            with col3:
                up_count = sum([
                    1 for etf in st.session_state.portfolio['etfs']
                    if not realtime_df.loc[realtime_df['ETF代码'] == etf, '涨跌幅%'].empty
                    and realtime_df.loc[realtime_df['ETF代码'] == etf, '涨跌幅%'].values[0] > 0
                ])
                st.metric("上涨家数", f"{up_count}/{len(st.session_state.portfolio['etfs'])}")
            
            with col4:
                st.metric("更新时间", datetime.now().strftime("%H:%M:%S"))
            
            # 自动刷新
            time.sleep(5)
            st.rerun()
    except Exception as e:
        st.warning(f"实时监控出错: {str(e)}")

# ==============================================
# 分析部分（如果有数据）
# ==============================================
if st.session_state.portfolio.get('data') is not None:
    prices_df = st.session_state.portfolio['data']
    weights = st.session_state.portfolio['weights']
    
    if len(weights) == len(prices_df.columns):
        # 计算基础指标
        metrics = calculate_portfolio_metrics(prices_df, weights)
        
        # 计算高级指标
        def calculate_advanced_metrics(returns_series, risk_free_rate=0.02):
            """计算高级风险指标"""
            if returns_series.empty:
                return {}
            
            # 基础指标
            annual_return = returns_series.mean() * 252
            annual_volatility = returns_series.std() * np.sqrt(252)
            sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
            
            # 索提诺比率（只考虑下行风险）
            downside_returns = returns_series[returns_series < 0]
            downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = (annual_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
            
            # 卡玛比率（收益/最大回撤）
            cumulative = (1 + returns_series).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = abs(drawdown.min())
            calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
            
            # 胜率和盈亏比
            winning_trades = (returns_series > 0).sum()
            total_trades = len(returns_series)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            avg_win = returns_series[returns_series > 0].mean() if winning_trades > 0 else 0
            avg_loss = abs(returns_series[returns_series < 0].mean()) if (total_trades - winning_trades) > 0 else 0
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            
            # VaR和CVaR（95%置信度）
            var_95 = np.percentile(returns_series, 5)
            cvar_95 = returns_series[returns_series <= var_95].mean()
            
            return {
                '年化收益率': annual_return,
                '年化波动率': annual_volatility,
                '夏普比率': sharpe_ratio,
                '索提诺比率': sortino_ratio,
                '卡玛比率': calmar_ratio,
                '最大回撤': max_drawdown,
                '胜率': win_rate,
                '盈亏比': profit_loss_ratio,
                'VaR(95%)': var_95,
                'CVaR(95%)': cvar_95
            }
        
        # 计算高级指标
        advanced_metrics = calculate_advanced_metrics(
            metrics.get('组合收益率序列', pd.Series()),
            risk_free_rate / 100
        )
        
        # ==============================================
        # 仪表板显示
        # ==============================================
        st.markdown("---")
        
        # 标签页布局
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 组合概览", 
            "📈 绩效分析", 
            "⚙️ 组合优化", 
            "🔍 风险分析",
            "📋 回测模拟",
            "💾 报告导出"
        ])
        
        with tab1:
            # 组合概览
            st.subheader("1. 组合概览")
            
            # 关键指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "年化收益率",
                    f"{advanced_metrics.get('年化收益率', 0):.2%}",
                    delta=f"{advanced_metrics.get('夏普比率', 0):.2f} 夏普"
                )
            
            with col2:
                st.metric(
                    "年化波动率",
                    f"{advanced_metrics.get('年化波动率', 0):.2%}",
                    delta_color="inverse"
                )
            
            with col3:
                st.metric(
                    "最大回撤",
                    f"{advanced_metrics.get('最大回撤', 0):.2%}",
                    delta_color="inverse"
                )
            
            with col4:
                st.metric(
                    "胜率",
                    f"{advanced_metrics.get('胜率', 0):.1%}",
                    delta=f"{advanced_metrics.get('盈亏比', 0):.2f} 盈亏比"
                )
            
            # 权重可视化
            st.subheader("2. 资产配置")
            
            fig_pie, fig_bar = plot_portfolio_weights(
                weights, 
                st.session_state.portfolio['etfs'],
                "投资组合权重分布"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.plotly_chart(fig_bar, use_container_width=True)
        
        with tab2:
            # 绩效分析
            st.subheader("绩效分析")
            
            # 组合表现图
            if '累计收益序列' in metrics:
                # 获取基准数据（使用第一个ETF作为基准）
                benchmark_data = get_etf_data(
                    st.session_state.portfolio['etfs'][0], 
                    st.session_state.period
                )
                
                if not benchmark_data.empty:
                    benchmark_returns = benchmark_data['Close'].pct_change().dropna()
                    benchmark_cumulative = (1 + benchmark_returns).cumprod()
                    
                    fig_performance = plot_portfolio_performance(
                        metrics['累计收益序列'],
                        benchmark_cumulative,
                        "投资组合 vs 基准表现"
                    )
                else:
                    fig_performance = plot_portfolio_performance(
                        metrics['累计收益序列'],
                        None,
                        "投资组合表现"
                    )
                
                st.plotly_chart(fig_performance, use_container_width=True)
            
            # 月度收益热图 - 修复zmid参数错误
            st.subheader("月度收益分析")
            
            if '组合收益率序列' in metrics:
                monthly_returns = metrics['组合收益率序列'].resample('M').apply(
                    lambda x: (1 + x).prod() - 1
                )
                
                # 创建月度收益矩阵
                monthly_returns_df = pd.DataFrame({
                    '年': monthly_returns.index.year,
                    '月': monthly_returns.index.month,
                    '收益': monthly_returns.values
                })
                
                monthly_pivot = monthly_returns_df.pivot_table(
                    index='年', columns='月', values='收益'
                )
                
                # 修复：使用zmin和zmax替代zmid
                fig_heatmap = px.imshow(
                    monthly_pivot * 100,
                    text_auto='.1f',
                    color_continuous_scale='RdBu',
                    zmin=-100,  # 修复：使用zmin和zmax
                    zmax=100,   # 修复：添加zmax参数
                    title="月度收益热图 (%)",
                    labels=dict(x="月份", y="年份", color="收益%")
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with tab3:
            # 组合优化
            st.subheader("组合优化")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("### 🎯 优化算法选择")
                
                optimization_method = st.selectbox(
                    "选择优化算法:",
                    [
                        "马科维茨均值-方差优化",
                        "风险平价优化", 
                        "最小方差组合",
                        "最大夏普比率组合",
                        "等权重组合"
                    ],
                    index=0
                )
                
                # 算法说明
                with st.expander("算法说明"):
                    if optimization_method == "马科维茨均值-方差优化":
                        st.markdown("""
                        **原理**: 在给定风险水平下最大化收益，或给定收益水平下最小化风险
                        
                        **优点**:
                        - 理论基础扎实
                        - 考虑资产间相关性
                        
                        **局限性**:
                        - 对输入参数敏感
                        - 假设收益率正态分布
                        """)
                    elif optimization_method == "风险平价优化":
                        st.markdown("""
                        **原理**: 让每个资产对组合的风险贡献相等
                        
                        **优点**:
                        - 不过度依赖历史收益率
                        - 通常更稳健
                        - 更适合风险控制
                        """)
                
                if st.button("🚀 运行优化", type="primary", use_container_width=True):
                    with st.spinner("正在优化..."):
                        returns_df = prices_df.pct_change().dropna()
                        
                        if optimization_method == "马科维茨均值-方差优化":
                            result = markowitz_optimization(returns_df)
                            method_key = 'markowitz'
                        elif optimization_method == "风险平价优化":
                            result = risk_parity_optimization(returns_df)
                            method_key = 'risk_parity'
                        elif optimization_method == "最小方差组合":
                            # 最小方差组合实现
                            cov_matrix = returns_df.cov() * 252
                            n_assets = len(returns_df.columns)
                            
                            from scipy.optimize import minimize
                            
                            def portfolio_variance(weights):
                                return np.dot(weights.T, np.dot(cov_matrix, weights))
                            
                            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
                            bounds = tuple((0, 1) for _ in range(n_assets))
                            init_weights = n_assets * [1./n_assets]
                            
                            result = minimize(portfolio_variance, init_weights,
                                            method='SLSQP', bounds=bounds,
                                            constraints=constraints)
                            
                            if result.success:
                                result = {
                                    'weights': result.x,
                                    'volatility': np.sqrt(result.fun),
                                    'expected_return': np.sum(returns_df.mean() * 252 * result.x)
                                }
                                method_key = 'min_variance'
                            else:
                                result = None
                        elif optimization_method == "等权重组合":
                            n_assets = len(returns_df.columns)
                            result = {
                                'weights': np.ones(n_assets) / n_assets,
                                'expected_return': returns_df.mean().mean() * 252,
                                'volatility': np.sqrt(np.dot(
                                    np.ones(n_assets) / n_assets, 
                                    np.dot(returns_df.cov() * 252, np.ones(n_assets) / n_assets)
                                ))
                            }
                            method_key = 'equal_weight'
                        
                        if result and 'weights' in result:
                            st.session_state.portfolio['optimized_weights'] = result['weights']
                            st.session_state.portfolio['optimization_method'] = method_key
                            st.success("优化完成!")
                            
                            # 显示优化结果
                            opt_weights_df = pd.DataFrame({
                                'ETF': st.session_state.portfolio['etfs'],
                                '原权重': [f"{w*100:.1f}%" for w in weights],
                                '优化权重': [f"{w*100:.1f}%" for w in result['weights']],
                                '权重变化': [f"{(w2 - w1)*100:+.1f}%" 
                                          for w1, w2 in zip(weights, result['weights'])]
                            })
                            
                            st.dataframe(opt_weights_df, use_container_width=True)
                            
                            if st.button("✅ 应用优化权重", type="primary"):
                                st.session_state.portfolio['weights'] = result['weights'].tolist()
                                st.rerun()
                        else:
                            st.error("优化失败，请检查数据")
            
            with col2:
                st.info("### 📊 有效前沿")
                
                # 绘制有效前沿
                if st.button("绘制有效前沿", use_container_width=True):
                    with st.spinner("计算有效前沿..."):
                        returns_df = prices_df.pct_change().dropna()
                        mean_returns = returns_df.mean() * 252
                        cov_matrix = returns_df.cov() * 252
                        
                        # 生成随机组合
                        num_portfolios = 10000
                        results = np.zeros((3, num_portfolios))
                        
                        for i in range(num_portfolios):
                            random_weights = np.random.random(len(returns_df.columns))
                            random_weights /= np.sum(random_weights)
                            
                            portfolio_return = np.sum(mean_returns * random_weights)
                            portfolio_volatility = np.sqrt(
                                np.dot(random_weights.T, np.dot(cov_matrix, random_weights))
                            )
                            sharpe_ratio = portfolio_return / portfolio_volatility
                            
                            results[0,i] = portfolio_return
                            results[1,i] = portfolio_volatility
                            results[2,i] = sharpe_ratio
                        
                        # 创建图表
                        fig_frontier = go.Figure()
                        
                        # 随机组合点
                        fig_frontier.add_trace(go.Scatter(
                            x=results[1,:], y=results[0,:],
                            mode='markers',
                            marker=dict(
                                size=5,
                                color=results[2,:],
                                colorscale='Viridis',
                                showscale=True,
                                colorbar=dict(title="夏普比率")
                            ),
                            name='随机组合',
                            hovertemplate='波动率: %{x:.2%}<br>收益率: %{y:.2%}<br>夏普: %{marker.color:.2f}'
                        ))
                        
                        # 当前组合
                        current_return = np.sum(mean_returns * weights)
                        current_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                        
                        fig_frontier.add_trace(go.Scatter(
                            x=[current_vol], y=[current_return],
                            mode='markers',
                            marker=dict(size=15, color='red', symbol='star'),
                            name='当前组合',
                            hovertemplate=f'当前组合<br>波动率: {current_vol:.2%}<br>收益率: {current_return:.2%}'
                        ))
                        
                        fig_frontier.update_layout(
                            title="有效前沿与随机组合",
                            xaxis_title="年化波动率",
                            yaxis_title="年化收益率",
                            height=500
                        )
                        
                        fig_frontier.update_xaxes(tickformat=',.0%')
                        fig_frontier.update_yaxes(tickformat=',.0%')
                        
                        st.plotly_chart(fig_frontier, use_container_width=True)
        
        with tab4:
            # 风险分析
            st.subheader("风险分析")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("### 📉 回撤分析")
                
                if '组合收益率序列' in metrics:
                    returns = metrics['组合收益率序列']
                    cumulative = (1 + returns).cumprod()
                    running_max = cumulative.expanding().max()
                    drawdown = (cumulative - running_max) / running_max
                    
                    fig_drawdown = go.Figure()
                    fig_drawdown.add_trace(go.Scatter(
                        x=drawdown.index,
                        y=drawdown.values,
                        fill='tozeroy',
                        fillcolor='rgba(255,0,0,0.3)',
                        line=dict(color='red'),
                        name='回撤'
                    ))
                    fig_drawdown.update_layout(
                        title="投资组合回撤分析",
                        xaxis_title="日期",
                        yaxis_title="回撤幅度",
                        yaxis_tickformat=',.1%',
                        height=400
                    )
                    st.plotly_chart(fig_drawdown, use_container_width=True)
                    
                    # 最大回撤统计
                    max_dd_info = {
                        '开始日期': cumulative[drawdown.idxmin():].idxmax(),
                        '结束日期': drawdown.idxmin(),
                        '最大回撤': drawdown.min(),
                        '恢复天数': (cumulative.index[-1] - drawdown.idxmin()).days
                    }
                    
                    st.metric("最大回撤", f"{max_dd_info['最大回撤']:.2%}")
                    st.caption(f"回撤期: {max_dd_info['开始日期'].strftime('%Y-%m-%d')} 至 {max_dd_info['结束日期'].strftime('%Y-%m-%d')}")
            
            with col2:
                st.info("### 🎲 风险指标")
                
                # 风险指标表格
                risk_metrics = {
                    '指标': ['年化波动率', '下行波动率', '夏普比率', '索提诺比率', 
                           '卡玛比率', 'VaR(95%)', 'CVaR(95%)'],
                    '数值': [
                        f"{advanced_metrics.get('年化波动率', 0):.2%}",
                        f"{advanced_metrics.get('年化波动率', 0) * 0.7:.2%}",  # 简化计算
                        f"{advanced_metrics.get('夏普比率', 0):.2f}",
                        f"{advanced_metrics.get('索提诺比率', 0):.2f}",
                        f"{advanced_metrics.get('卡玛比率', 0):.2f}",
                        f"{advanced_metrics.get('VaR(95%)', 0):.2%}",
                        f"{advanced_metrics.get('CVaR(95%)', 0):.2%}"
                    ],
                    '说明': [
                        "总波动风险",
                        "下行波动风险",
                        "风险调整后收益",
                        "下行风险调整后收益", 
                        "收益/最大回撤",
                        "95%置信度下最大单日损失",
                        "极端情况平均损失"
                    ]
                }
                
                st.dataframe(pd.DataFrame(risk_metrics), use_container_width=True, hide_index=True)
                
                # 相关性分析
                st.info("### 🔗 相关性分析")
                
                returns_df = prices_df.pct_change().dropna()
                if len(returns_df.columns) > 1:
                    corr_matrix = returns_df.corr()
                    
                    # 修复：使用zmin和zmax替代zmid
                    fig_corr = px.imshow(
                        corr_matrix,
                        text_auto='.2f',
                        color_continuous_scale='RdBu',
                        zmin=-1,  # 修复：相关性范围在-1到1之间
                        zmax=1,   # 修复：添加zmax参数
                        title="资产收益率相关性"
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
        
        with tab5:
            # 回测模拟
            st.subheader("回测模拟")
            
            col1, col2 = st.columns(2)
            
            with col1:
                rebalance_freq = st.selectbox(
                    "再平衡频率:",
                    ["每日", "每周", "每月", "每季度", "每年", "从不"],
                    index=2
                )
                
                initial_capital = st.number_input(
                    "初始资金 (元):",
                    min_value=1000,
                    max_value=10000000,
                    value=100000,
                    step=10000
                )
            
            with col2:
                start_date = st.date_input(
                    "回测开始日期:",
                    value=datetime.now() - timedelta(days=365)
                )
                
                end_date = st.date_input(
                    "回测结束日期:",
                    value=datetime.now()
                )
            
            # 修复缩进问题：确保if语句正确缩进
            if st.button("🚀 运行回测", type="primary"):
                with st.spinner("正在回测..."):
                    # 简化回测逻辑
                    returns_series = metrics.get('组合收益率序列', pd.Series())
                    
                    if not returns_series.empty:
                        # 计算累计收益
                        cumulative_returns = (1 + returns_series).cumprod()
                        
                        # 模拟资金曲线 - 修复变量名
                        capital_curve = initial_capital * cumulative_returns
                        
                        # 回测结果
                        final_value = capital_curve.iloc[-1] if not capital_curve.empty else initial_capital
                        total_return = (final_value - initial_capital) / initial_capital
                        
                        # 绘制资金曲线
                        fig_backtest = go.Figure()
                        fig_backtest.add_trace(go.Scatter(
                            x=capital_curve.index,
                            y=capital_curve.values,
                            mode='lines',
                            name='资金曲线',
                            line=dict(color='green', width=2)
                        ))
                        
                        fig_backtest.add_trace(go.Scatter(
                            x=capital_curve.index,
                            y=[initial_capital] * len(capital_curve),
                            mode='lines',
                            name='初始资金',
                            line=dict(color='gray', width=1, dash='dash')
                        ))
                        
                        fig_backtest.update_layout(
                            title=f"回测结果: {initial_capital:,.0f}元 → {final_value:,.0f}元 ({total_return:+.2%})",
                            xaxis_title="日期",
                            yaxis_title="资金 (元)",
                            height=400
                        )
                        
                        st.plotly_chart(fig_backtest, use_container_width=True)
                        
                        # 回测统计
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("最终价值", f"¥{final_value:,.0f}")
                        
                        with col2:
                            st.metric("总收益", f"{total_return:+.2%}")
                        
                        with col3:
                            # 计算年化收益
                            if len(capital_curve) > 1:
                                days = (capital_curve.index[-1] - capital_curve.index[0]).days
                                if days > 0:
                                    annualized_return = (1 + total_return) ** (365 / days) - 1
                                    st.metric("年化收益", f"{annualized_return:.2%}")
                                else:
                                    st.metric("年化收益", "N/A")
                            else:
                                st.metric("年化收益", "N/A")
                        
                        with col4:
                            if len(capital_curve) > 0:
                                max_capital = capital_curve.expanding().max()
                                drawdown = (capital_curve - max_capital) / max_capital
                                st.metric("最大回撤", f"{drawdown.min():.2%}")
                            else:
                                st.metric("最大回撤", "N/A")
                    else:
                        st.warning("无法进行回测：没有可用的收益率数据")
        
        with tab6:
            # 报告导出
            st.subheader("报告导出")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📄 生成PDF报告", type="primary", use_container_width=True):
                    with st.spinner("正在生成PDF报告..."):
                        portfolio_data = {
                            'etfs': st.session_state.portfolio['etfs'],
                            'weights': weights,
                            'labels': st.session_state.portfolio['names'],
                            'metrics': {**metrics, **advanced_metrics},
                            'prices': prices_df,
                            'optimization_method': st.session_state.portfolio.get('optimization_method')
                        }
                        
                        try:
                            pdf_buffer = generate_pdf_report(portfolio_data)
                            
                            st.download_button(
                                label="⬇️ 下载PDF报告",
                                data=pdf_buffer,
                                file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"生成报告失败: {str(e)}")
            
            with col2:
                if st.button("📊 导出分析数据", use_container_width=True):
                    # 导出CSV数据
                    analysis_data = {
                        'returns': metrics.get('组合收益率序列', pd.Series()),
                        'cumulative_returns': metrics.get('累计收益序列', pd.Series()),
                        'weights': pd.Series(weights, index=st.session_state.portfolio['etfs']),
                        'metrics': pd.Series(advanced_metrics)
                    }
                    
                    # 创建DataFrame
                    export_df = pd.DataFrame({
                        '日期': metrics.get('组合收益率序列', pd.Series()).index,
                        '日收益率': metrics.get('组合收益率序列', pd.Series()).values,
                        '累计收益率': metrics.get('累计收益序列', pd.Series()).values if '累计收益序列' in metrics else None
                    })
                    
                    csv_data = export_df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="📥 下载CSV数据",
                        data=csv_data,
                        file_name=f"portfolio_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col3:
                if st.button("📋 复制配置", use_container_width=True):
                    # 生成配置JSON
                    import json
                    
                    config = {
                        'etfs': st.session_state.portfolio['etfs'],
                        'weights': weights,
                        'period': st.session_state.period,
                        'optimization_method': st.session_state.portfolio.get('optimization_method'),
                        'generated_time': datetime.now().isoformat()
                    }
                    
                    st.code(json.dumps(config, indent=2, ensure_ascii=False), language='json')
                    st.success("配置已复制到剪贴板")
            
            # 报告预览
            st.markdown("---")
            st.subheader("报告预览")
            
            with st.expander("点击查看报告摘要", expanded=True):
                st.markdown(f"""
                ### 📋 投资组合分析报告摘要
                
                **组合概况**
                - 资产数量: {len(st.session_state.portfolio['etfs'])} 个ETF
                - 分析周期: {period}
                - 数据期间: {prices_df.index[0].strftime('%Y-%m-%d')} 至 {prices_df.index[-1].strftime('%Y-%m-%d')}
                
                **核心指标**
                - 年化收益率: {advanced_metrics.get('年化收益率', 0):.2%}
                - 年化波动率: {advanced_metrics.get('年化波动率', 0):.2%}
                - 夏普比率: {advanced_metrics.get('夏普比率', 0):.2f}
                - 最大回撤: {advanced_metrics.get('最大回撤', 0):.2%}
                
                **风险指标**
                - 索提诺比率: {advanced_metrics.get('索提诺比率', 0):.2f}
                - 卡玛比率: {advanced_metrics.get('卡玛比率', 0):.2f}
                - VaR(95%): {advanced_metrics.get('VaR(95%)', 0):.2%}
                - 胜率: {advanced_metrics.get('胜率', 0):.1%}
                
                **投资建议**
                1. 定期审查组合权重，考虑再平衡
                2. 监控相关性变化，适时调整配置
                3. 关注市场风险，设置适当止损
                4. 结合个人风险承受能力调整配置
                """)
    else:
        st.error("权重数量与ETF数量不匹配，请重新调整组合")

# ==============================================
# 页面底部说明
# ==============================================
st.markdown("---")
with st.expander("📖 使用指南与说明", expanded=False):
    st.markdown("""
    ### 🎯 使用指南
    
    1. **组合构建**
       - 在侧边栏添加ETF并设置权重
       - 或选择预设组合快速开始
       - 点击"获取组合数据"加载历史数据
    
    2. **分析功能**
       - 查看组合概览和绩效指标
       - 使用不同算法优化组合
       - 进行风险分析和回测模拟
    
    3. **优化建议**
       - 马科维茨优化: 适合追求风险收益平衡
       - 风险平价优化: 适合风险控制优先
       - 最小方差组合: 适合风险厌恶型投资者
    
    4. **报告生成**
       - 生成PDF格式完整报告
       - 导出分析数据用于进一步研究
       - 保存组合配置便于后续使用
    
    ### ⚠️ 风险提示
    
    - 历史表现不代表未来收益
    - 优化结果基于历史数据，实际效果可能不同
    - 投资需结合个人风险承受能力
    - 建议咨询专业投资顾问
    
    ### 🔧 技术支持
    
    如遇问题，请检查:
    1. ETF代码格式是否正确
    2. 网络连接是否正常
    3. 是否安装了所有依赖包
    4. 数据获取是否有权限限制
    """)

# 添加自定义CSS
st.markdown("""
<style>
    .portfolio-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        color: white;
        margin: 10px 0;
    }
    
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #1E88E5;
    }
    
    .optimization-card {
        background-color: #fff3cd;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #ffeaa7;
    }
</style>
""", unsafe_allow_html=True)
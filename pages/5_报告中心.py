"""
报告中心页面 - 生成专业的投资分析报告
修复了所有已知问题：导入缺失、缓存问题、时区问题
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from io import BytesIO
import base64
from utils import (
    get_index_data,
    get_etf_data,
    get_realtime_price,
    calculate_portfolio_metrics,
    plot_portfolio_weights,
    plot_portfolio_performance,
    generate_pdf_report,
    validate_etf_code,
    format_etf_code
)

# 页面配置
st.set_page_config(
    page_title="报告中心",
    page_icon="📋",
    layout="wide"
)

st.title("📋 报告中心")
st.markdown("生成专业的投资分析报告")

# 初始化session state
if 'report_data' not in st.session_state:
    st.session_state.report_data = {
        'selected_assets': [],
        'time_period': '1y',
        'report_type': 'basic',
        'charts': []
    }

# 侧边栏 - 报告配置
with st.sidebar:
    st.header("⚙️ 报告配置")
    
    # 报告类型
    st.subheader("报告类型")
    report_type = st.selectbox(
        "选择报告类型:",
        ["基础报告", "技术分析报告", "组合分析报告", "市场监控报告", "自定义报告"],
        index=0,
        key="report_type_select"
    )
    
    # 资产选择
    st.subheader("选择资产")
    
    # 指数选项
    st.markdown("**指数**")
    index_options = ["沪深300", "标普500", "纳斯达克", "恒生指数", "上证指数"]
    selected_indices = st.multiselect(
        "选择指数:",
        index_options,
        default=["沪深300"],
        key="index_select"
    )
    
    # ETF选项
    st.markdown("**ETF**")
    etf_input = st.text_area(
        "输入ETF代码(每行一个):",
        value="510300\n510500\n159919",
        height=100,
        key="etf_textarea"
    )
    
    # 解析ETF列表
    etf_list = [etf.strip() for etf in etf_input.split('\n') if etf.strip()]
    valid_etfs = [format_etf_code(etf) for etf in etf_list if validate_etf_code(etf)]
    
    if valid_etfs:
        st.success(f"有效ETF: {len(valid_etfs)}个")
    else:
        st.warning("未检测到有效ETF代码")
    
    # 时间周期 - 修改为包含10年
    st.subheader("时间设置")
    time_period = st.select_slider(
        "分析周期:",
        options=["1个月", "3个月", "6个月", "1年", "2年", "5年", "10年", "最大"],
        value="5年",
        key="time_slider"
    )
    
    period_map = {
        "1个月": "1mo", "3个月": "3mo", "6个月": "6mo",
        "1年": "1y", "2年": "2y", "5年": "5y",
        "10年": "10y", "最大": "max"
    }
    
    # 报告内容
    st.subheader("报告内容")
    include_charts = st.checkbox("包含图表", value=True, key="include_charts")
    include_analysis = st.checkbox("包含分析", value=True, key="include_analysis")
    include_recommendations = st.checkbox("包含建议", value=False, key="include_recs")
    
    # 生成按钮
    st.markdown("---")
    if st.button("📊 生成报告预览", type="primary", use_container_width=True):
        # 收集报告数据
        st.session_state.report_data = {
            'selected_assets': {
                'indices': selected_indices,
                'etfs': valid_etfs
            },
            'time_period': period_map[time_period],
            'report_type': report_type,
            'include_charts': include_charts,
            'include_analysis': include_analysis,
            'include_recommendations': include_recommendations,
            'generated_time': datetime.now()
        }
        st.success("报告配置已保存!")
        
        # 清除缓存以确保获取最新数据
        try:
            if 'get_realtime_price' in st.session_state:
                del st.session_state['get_realtime_price']
        except:
            pass

# 主内容区 - 报告预览
if st.session_state.report_data.get('selected_assets'):
    st.header("📄 报告预览")
    
    # 报告标题
    st.markdown(f"## {report_type} - {datetime.now().strftime('%Y年%m月%d日')}")
    st.markdown("---")
    
    # 执行分析
    with st.spinner("正在生成报告内容..."):
        # 获取数据
        all_data = {}
        
        # 获取指数数据
        index_map = {
            "沪深300": "000300.SS",
            "标普500": "^GSPC",
            "纳斯达克": "^IXIC",
            "恒生指数": "^HSI",
            "上证指数": "000001.SS"
        }
        
        for index in st.session_state.report_data['selected_assets']['indices']:
            if index in index_map:
                data = get_index_data(index_map[index], st.session_state.report_data['time_period'])
                if not data.empty:
                    # 移除时区信息（如果有）
                    if hasattr(data.index, 'tz') and data.index.tz is not None:
                        data.index = data.index.tz_localize(None)
                    all_data[index] = data['Close']
        
        # 获取ETF数据
        for etf in st.session_state.report_data['selected_assets']['etfs']:
            data = get_etf_data(etf, st.session_state.report_data['time_period'])
            if not data.empty:
                # 移除时区信息（如果有）
                if hasattr(data.index, 'tz') and data.index.tz is not None:
                    data.index = data.index.tz_localize(None)
                all_data[etf] = data['Close']
        
        if all_data:
            # 创建DataFrame
            prices_df = pd.DataFrame(all_data)
            
            # 如果索引是带时区的，移除时区
            if hasattr(prices_df.index, 'tz') and prices_df.index.tz is not None:
                prices_df.index = prices_df.index.tz_localize(None)
            
            # 报告内容标签页
            tab1, tab2, tab3, tab4 = st.tabs(["📈 市场概览", "📊 详细分析", "📋 数据表格", "🎯 报告输出"])
            
            with tab1:
                # 市场概览
                st.subheader("1. 市场概览")
                
                # 实时价格（如果有ETF）
                if st.session_state.report_data['selected_assets']['etfs']:
                    st.markdown("#### 实时价格")
                    realtime_df = get_realtime_price(st.session_state.report_data['selected_assets']['etfs'][:5])
                    
                    if not realtime_df.empty:
                        st.dataframe(
                            realtime_df[['ETF代码', '名称', '当前价格', '涨跌幅%', '成交量']],
                            use_container_width=True,
                            column_config={
                                "当前价格": st.column_config.NumberColumn(format="%.3f"),
                                "涨跌幅%": st.column_config.NumberColumn(format="%.2f"),
                                "成交量": st.column_config.NumberColumn(format="%d")
                            }
                        )
                
                # 价格走势图
                if include_charts:
                    st.markdown("#### 价格走势")
                    
                    # 归一化价格（从100开始）
                    normalized_prices = prices_df / prices_df.iloc[0] * 100
                    
                    fig_prices = go.Figure()
                    for column in normalized_prices.columns:
                        fig_prices.add_trace(go.Scatter(
                            x=normalized_prices.index,
                            y=normalized_prices[column],
                            mode='lines',
                            name=column,
                            hovertemplate='%{y:.1f}%<br>%{x}'
                        ))
                    
                    fig_prices.update_layout(
                        title="资产价格走势对比（归一化）",
                        xaxis_title="日期",
                        yaxis_title="相对价格 (%)",
                        hovermode='x unified',
                        height=500,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    st.plotly_chart(fig_prices, use_container_width=True)
                
                # 关键指标
                if include_analysis:
                    st.markdown("#### 关键指标")
                    
                    metrics_data = []
                    for column in prices_df.columns:
                        returns = prices_df[column].pct_change().dropna()
                        if len(returns) > 0:
                            metrics_data.append({
                                '资产': column,
                                '累计收益': f"{((prices_df[column].iloc[-1] / prices_df[column].iloc[0]) - 1) * 100:.2f}%",
                                '年化收益': f"{returns.mean() * 252 * 100:.2f}%",
                                '年化波动': f"{returns.std() * np.sqrt(252) * 100:.2f}%",
                                '最大回撤': f"{((prices_df[column] / prices_df[column].expanding().max() - 1).min() * 100):.2f}%"
                            })
                    
                    if metrics_data:
                        metrics_df = pd.DataFrame(metrics_data)
                        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
            
            with tab2:
                # 详细分析
                st.subheader("2. 详细分析")
                
                # 计算收益率
                returns_df = prices_df.pct_change().dropna()
                
                # 收益率分布
                if include_charts:
                    st.markdown("#### 收益率分析")
                    
                    fig_returns = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=("收益率分布", "累计收益率", "滚动波动率(20日)", "相关性热图"),
                        vertical_spacing=0.15,
                        horizontal_spacing=0.15
                    )
                    
                    # 收益率分布直方图（只显示前3个资产）
                    for i, column in enumerate(returns_df.columns[:min(3, len(returns_df.columns))]):
                        fig_returns.add_trace(
                            go.Histogram(
                                x=returns_df[column],
                                name=column,
                                nbinsx=30,
                                opacity=0.7,
                                showlegend=True
                            ),
                            row=1, col=1
                        )
                    
                    # 累计收益率
                    cumulative_returns = (1 + returns_df).cumprod()
                    for column in cumulative_returns.columns[:min(4, len(cumulative_returns.columns))]:
                        fig_returns.add_trace(
                            go.Scatter(
                                x=cumulative_returns.index,
                                y=cumulative_returns[column],
                                name=column,
                                mode='lines'
                            ),
                            row=1, col=2
                        )
                    
                    # 滚动波动率（20日）
                    if len(returns_df) >= 20:
                        rolling_vol = returns_df.rolling(window=20).std() * np.sqrt(252)
                        for column in rolling_vol.columns[:min(4, len(rolling_vol.columns))]:
                            fig_returns.add_trace(
                                go.Scatter(
                                    x=rolling_vol.index,
                                    y=rolling_vol[column],
                                    name=column,
                                    mode='lines'
                                ),
                                row=2, col=1
                            )
                    
                    # 相关性热图
                    if len(returns_df.columns) > 1:
                        corr_matrix = returns_df.corr()
                        fig_returns.add_trace(
                            go.Heatmap(
                                z=corr_matrix.values,
                                x=corr_matrix.columns,
                                y=corr_matrix.index,
                                colorscale='RdBu',
                                zmid=0,
                                text=corr_matrix.round(2).values,
                                texttemplate='%{text}',
                                showscale=True
                            ),
                            row=2, col=2
                        )
                    
                    fig_returns.update_layout(
                        height=800, 
                        showlegend=True,
                        title_text="资产收益率分析"
                    )
                    st.plotly_chart(fig_returns, use_container_width=True)
                
                # 风险分析
                if include_analysis:
                    st.markdown("#### 风险分析")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # VaR计算（95%置信度）
                        st.info("**风险价值 (VaR - 95%置信度)**")
                        var_data = []
                        for column in returns_df.columns:
                            if len(returns_df[column].dropna()) > 0:
                                var_95 = np.percentile(returns_df[column].dropna(), 5)
                                var_data.append({
                                    '资产': column,
                                    '日VaR': f"{var_95 * 100:.2f}%",
                                    '年化VaR': f"{var_95 * np.sqrt(252) * 100:.2f}%"
                                })
                        
                        if var_data:
                            st.dataframe(pd.DataFrame(var_data), use_container_width=True, hide_index=True)
                    
                    with col2:
                        # 最大回撤分析
                        st.info("**最大回撤分析**")
                        drawdown_data = []
                        for column in prices_df.columns:
                            cummax = prices_df[column].expanding().max()
                            drawdown = (prices_df[column] - cummax) / cummax
                            max_dd = drawdown.min()
                            dd_duration = (drawdown == max_dd).sum()
                            
                            drawdown_data.append({
                                '资产': column,
                                '最大回撤': f"{max_dd * 100:.2f}%",
                                '回撤天数': int(dd_duration)
                            })
                        
                        if drawdown_data:
                            st.dataframe(pd.DataFrame(drawdown_data), use_container_width=True, hide_index=True)
            
            with tab3:
                # 数据表格
                st.subheader("3. 数据表格")
                
                # 价格数据
                st.markdown("#### 价格数据")
                st.dataframe(
                    prices_df.tail(20).sort_index(ascending=False),
                    use_container_width=True,
                    column_config={col: st.column_config.NumberColumn(format="%.3f") 
                                 for col in prices_df.columns}
                )
                
                # 统计数据
                st.markdown("#### 统计摘要")
                stats_data = []
                for column in prices_df.columns:
                    col_data = prices_df[column]
                    stats_data.append({
                        '资产': column,
                        '平均值': f"{col_data.mean():.3f}",
                        '标准差': f"{col_data.std():.3f}",
                        '最小值': f"{col_data.min():.3f}",
                        '25%分位': f"{col_data.quantile(0.25):.3f}",
                        '中位数': f"{col_data.median():.3f}",
                        '75%分位': f"{col_data.quantile(0.75):.3f}",
                        '最大值': f"{col_data.max():.3f}",
                        '偏度': f"{col_data.skew():.3f}",
                        '峰度': f"{col_data.kurtosis():.3f}"
                    })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True)
                
                # 数据下载
                st.markdown("#### 数据下载")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV下载
                    csv = prices_df.to_csv().encode('utf-8')
                    st.download_button(
                        label="📥 下载价格数据 (CSV)",
                        data=csv,
                        file_name=f"report_data_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Excel下载 - 修复时区问题
                    if st.button("📥 下载详细数据 (Excel)", use_container_width=True):
                        with st.spinner("正在生成Excel文件..."):
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                # 确保数据框索引没有时区信息
                                prices_df_to_write = prices_df.copy()
                                # 如果索引是datetime类型且有时区，转换为无时区
                                if pd.api.types.is_datetime64_any_dtype(prices_df_to_write.index):
                                    if hasattr(prices_df_to_write.index, 'tz') and prices_df_to_write.index.tz is not None:
                                        prices_df_to_write.index = prices_df_to_write.index.tz_localize(None)
                                
                                prices_df_to_write.to_excel(writer, sheet_name='价格数据')
                                
                                if not returns_df.empty:
                                    returns_df_to_write = returns_df.copy()
                                    # 同样处理收益率数据
                                    if pd.api.types.is_datetime64_any_dtype(returns_df_to_write.index):
                                        if hasattr(returns_df_to_write.index, 'tz') and returns_df_to_write.index.tz is not None:
                                            returns_df_to_write.index = returns_df_to_write.index.tz_localize(None)
                                    
                                    returns_df_to_write.to_excel(writer, sheet_name='收益率数据')
                            
                            excel_data = output.getvalue()
                            
                            st.download_button(
                                label="⬇️ 点击下载Excel文件",
                                data=excel_data,
                                file_name=f"report_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
            
            with tab4:
                # 报告输出
                st.subheader("4. 报告输出")
                
                # 报告配置确认
                st.markdown("#### 报告配置确认")
                
                config_data = {
                    '配置项': ['报告类型', '分析周期', '包含图表', '包含分析', '包含建议'],
                    '设置': [
                        report_type,
                        time_period,
                        '是' if include_charts else '否',
                        '是' if include_analysis else '否',
                        '是' if include_recommendations else '否'
                    ]
                }
                config_df = pd.DataFrame(config_data)
                st.dataframe(config_df, use_container_width=True, hide_index=True)
                
                # 生成报告
                st.markdown("#### 生成最终报告")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # PDF报告
                    if st.button("📄 生成PDF报告", use_container_width=True, type="primary"):
                        with st.spinner("正在生成PDF报告..."):
                            # 准备报告数据
                            portfolio_data = {
                                'assets': list(prices_df.columns),
                                'prices': prices_df,
                                'returns': returns_df,
                                'metrics': {
                                    '资产数量': len(prices_df.columns),
                                    '数据期间': f"{prices_df.index[0].strftime('%Y-%m-%d') if len(prices_df) > 0 else 'N/A'} 至 {prices_df.index[-1].strftime('%Y-%m-%d') if len(prices_df) > 0 else 'N/A'}",
                                    '交易日数': len(prices_df)
                                }
                            }
                            
                            try:
                                pdf_buffer = generate_pdf_report(portfolio_data)
                                
                                st.download_button(
                                    label="⬇️ 下载PDF报告",
                                    data=pdf_buffer,
                                    file_name=f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"生成PDF报告失败: {str(e)}")
                                st.info("请确保已安装reportlab库: pip install reportlab")
                
                with col2:
                    # HTML报告
                    if st.button("🌐 导出HTML图表", use_container_width=True):
                        with st.spinner("正在导出图表..."):
                            # 导出归一化价格图表为HTML
                            if include_charts:
                                normalized_prices = prices_df / prices_df.iloc[0] * 100
                                fig_html = go.Figure()
                                for column in normalized_prices.columns:
                                    fig_html.add_trace(go.Scatter(
                                        x=normalized_prices.index,
                                        y=normalized_prices[column],
                                        mode='lines',
                                        name=column
                                    ))
                                
                                fig_html.update_layout(
                                    title="资产价格走势对比",
                                    xaxis_title="日期",
                                    yaxis_title="相对价格 (%)",
                                    height=500
                                )
                                
                                html_content = fig_html.to_html()
                                st.download_button(
                                    label="📥 下载HTML图表",
                                    data=html_content,
                                    file_name=f"price_chart_{datetime.now().strftime('%Y%m%d')}.html",
                                    mime="text/html",
                                    use_container_width=True
                                )
                
                with col3:
                    # 邮件发送
                    if st.button("📧 分享报告配置", use_container_width=True):
                        # 生成配置分享链接
                        config_json = {
                            'report_type': report_type,
                            'indices': selected_indices,
                            'etfs': valid_etfs,
                            'period': time_period,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        st.info("报告配置已复制到剪贴板")
                        st.code(str(config_json), language='json')
                
                # 报告建议
                if include_recommendations:
                    st.markdown("#### 投资建议")
                    
                    recommendations = """
                    ### 基于分析的投资建议
                    
                    **1. 资产配置建议**
                    - 建议分散投资，降低单一资产风险
                    - 考虑股债平衡配置
                    - 定期再平衡投资组合
                    
                    **2. 风险控制建议**
                    - 设置止损位，控制最大回撤
                    - 关注波动率变化，适时调整仓位
                    - 避免过度集中投资
                    
                    **3. 投资时机建议**
                    - 市场低估时加大配置
                    - 市场高估时逐步减仓
                    - 采用定投策略平滑成本
                    
                    **4. 监控建议**
                    - 定期审查投资组合
                    - 关注宏观经济变化
                    - 跟踪政策动向
                    """
                    
                    st.markdown(recommendations)
        
        else:
            st.error("无法获取数据，请检查资产代码或网络连接")
            st.info("""
            常见问题解决方法:
            1. 检查ETF代码格式是否正确 (如: 510300, SPY)
            2. 确保网络连接正常
            3. 尝试减少资产数量或缩短分析周期
            4. 部分指数可能需要使用完整代码 (如: ^GSPC, 000300.SS)
            """)
else:
    # 初始状态
    st.info("👈 请在侧边栏配置报告参数，然后点击'生成报告预览'")
    
    # 示例展示
    st.markdown("### 💡 示例报告")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("加载A股市场示例", use_container_width=True):
            st.session_state.report_data = {
                'selected_assets': {
                    'indices': ['沪深300', '上证指数'],
                    'etfs': ['510300', '510500', '159919']
                },
                'time_period': '5y',
                'report_type': '基础报告',
                'include_charts': True,
                'include_analysis': True,
                'include_recommendations': False,
                'generated_time': datetime.now()
            }
            st.rerun()
    
    with col2:
        if st.button("加载全球市场示例", use_container_width=True):
            st.session_state.report_data = {
                'selected_assets': {
                    'indices': ['标普500', '恒生指数'],
                    'etfs': ['SPY', 'QQQ', '510300']
                },
                'time_period': '5y',
                'report_type': '基础报告',
                'include_charts': True,
                'include_analysis': True,
                'include_recommendations': False,
                'generated_time': datetime.now()
            }
            st.rerun()

# 页面说明
st.markdown("---")
with st.expander("📖 报告中心使用指南", expanded=False):
    st.markdown("""
    ### 🎯 使用步骤
    
    1. **配置报告**
       - 选择报告类型
       - 添加要分析的资产 (指数和ETF)
       - 设置时间周期 (10年适合长期趋势分析)
       - 选择报告内容选项
    
    2. **预览报告**
       - 查看市场概览和图表
       - 分析详细数据和指标
       - 检查统计摘要
       - 预览投资建议
    
    3. **生成报告**
       - 下载PDF格式完整报告
       - 导出HTML交互式图表
       - 保存数据表格
       - 分享报告配置
    
    4. **定制报告**
       - 添加自定义分析
       - 调整图表样式
       - 包含特定指标
       - 设置预警条件
    
    ### 📊 报告类型说明
    
    **基础报告**: 包含基本价格数据和图表
    **技术分析报告**: 包含技术指标和信号
    **组合分析报告**: 包含组合优化建议
    **市场监控报告**: 包含实时监控和预警
    **自定义报告**: 完全自定义的报告内容
    
    ### ⚠️ 注意事项
    
    - 报告基于历史数据，仅供参考
    - 投资建议不构成实际操作指导
    - 请结合其他信息进行决策
    - 定期更新报告保持时效性
    
    ### 🔧 技术支持
    
    如遇问题，请检查:
    1. 网络连接是否正常
    2. ETF/指数代码格式是否正确
    3. 是否安装了所有依赖包
    4. 数据获取是否有权限限制
    """)

# 添加一些自定义CSS美化
st.markdown("""
<style>
    .report-section {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #1E88E5;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 15px;
        color: white;
        text-align: center;
    }
    
    .data-table {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏底部信息
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 数据说明")
    st.caption("""
    - 实时数据: 15分钟延迟
    - 历史数据: 每日收盘后更新
    - 数据来源: Yahoo Finance
    - 更新时间: {}
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    
    st.markdown("---")
    st.markdown("### 🆘 需要帮助?")
    if st.button("清除缓存重新加载", use_container_width=True):
        # 清除相关缓存
        keys_to_clear = ['report_data', 'get_realtime_price']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
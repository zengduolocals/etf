"""
指数分析页面
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils import get_index_data, plot_kline, validate_etf_code

# 页面配置
st.set_page_config(
    page_title="指数分析",
    page_icon="📊",
    layout="wide"
)

st.title("📊 指数分析")
st.markdown("分析主要股票指数的历史走势和技术指标")

# 侧边栏 - 控制面板
with st.sidebar:
    st.header("分析参数")
    
    # 指数选择
    st.subheader("选择指数")
    index_options = {
        "标普500": "^GSPC",
        "道琼斯": "^DJI",
        "纳斯达克": "^IXIC",
        "沪深300": "000300.SS",
        "上证指数": "000001.SS",
        "深证成指": "399001.SZ",
        "创业板指": "399006.SZ",
        "恒生指数": "^HSI",
        "日经225": "^N225",
        "德国DAX": "^GDAXI"
    }
    
    selected_index = st.selectbox(
        "选择指数:",
        list(index_options.keys()),
        index=3
    )
    index_code = index_options[selected_index]
    
    # 自定义指数输入
    custom_index = st.text_input(
        "或输入自定义指数代码:",
        placeholder="如: ^GSPC, 000300.SS"
    )
    
    if custom_index and validate_etf_code(custom_index):
        index_code = custom_index
    
    # 时间周期 - 修改为包含10年选项
    st.subheader("时间周期")
    period_options = {
        "1个月": "1mo",
        "3个月": "3mo", 
        "6个月": "6mo",
        "1年": "1y",
        "2年": "2y",
        "5年": "5y",
        "10年": "10y",
        "最大": "max"
    }
    
    period = st.select_slider(
        "选择分析周期:",
        options=list(period_options.keys()),
        value="5年"
    )
    
    # 技术指标
    st.subheader("技术指标")
    show_ma = st.checkbox("显示移动平均线", value=True)
    ma_periods = st.multiselect(
        "选择MA周期:",
        [5, 10, 20, 30, 60, 120],
        default=[5, 20, 60]
    )
    
    # 数据更新
    st.subheader("数据更新")
    if st.button("🔄 更新数据", type="primary"):
        st.cache_data.clear()
        st.rerun()

# 主内容区
tab1, tab2, tab3 = st.tabs(["📈 K线分析", "📊 技术指标", "📋 数据明细"])

with tab1:
    st.subheader(f"{selected_index} K线图")
    
    if st.button("获取数据", type="primary", key="get_data_kline"):
        with st.spinner(f"正在获取{selected_index}数据..."):
            # 获取数据
            data = get_index_data(index_code, period_options[period])
            
            if not data.empty:
                # 显示K线图
                fig = plot_kline(data, f"{selected_index} K线图")
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "当前价格",
                        f"{data['Close'].iloc[-1]:.2f}",
                        f"{(data['Close'].iloc[-1] - data['Close'].iloc[-2])/data['Close'].iloc[-2]*100:.2f}%"
                    )
                with col2:
                    # 计算52周最高最低（如果数据足够）
                    if len(data) >= 252:
                        st.metric("52周最高", f"{data['High'].tail(252).max():.2f}")
                    else:
                        st.metric("期间最高", f"{data['High'].max():.2f}")
                with col3:
                    if len(data) >= 252:
                        st.metric("52周最低", f"{data['Low'].tail(252).min():.2f}")
                    else:
                        st.metric("期间最低", f"{data['Low'].min():.2f}")
                with col4:
                    st.metric("平均成交量", f"{data['Volume'].mean():,.0f}")
            else:
                st.error("无法获取数据，请检查指数代码或网络连接")

with tab2:
    st.subheader("技术指标分析")
    
    if st.button("计算技术指标", type="primary", key="calc_indicators"):
        with st.spinner("正在计算技术指标..."):
            data = get_index_data(index_code, period_options[period])
            
            if not data.empty:
                # 计算技术指标
                data['MA5'] = data['Close'].rolling(window=5).mean()
                data['MA20'] = data['Close'].rolling(window=20).mean()
                data['MA60'] = data['Close'].rolling(window=60).mean()
                
                # RSI计算
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                data['RSI'] = 100 - (100 / (1 + rs))
                
                # 布林带
                data['BB_middle'] = data['Close'].rolling(window=20).mean()
                bb_std = data['Close'].rolling(window=20).std()
                data['BB_upper'] = data['BB_middle'] + 2 * bb_std
                data['BB_lower'] = data['BB_middle'] - 2 * bb_std
                
                # 创建子图
                from plotly.subplots import make_subplots
                
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.5, 0.25, 0.25],
                    subplot_titles=("价格与移动平均线", "RSI指标", "布林带")
                )
                
                # 价格和MA
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['Close'], name='收盘价', line=dict(color='blue')),
                    row=1, col=1
                )
                
                if show_ma:
                    for ma_period in ma_periods:
                        if len(data) >= ma_period:
                            ma = data['Close'].rolling(window=ma_period).mean()
                            fig.add_trace(
                                go.Scatter(x=data.index, y=ma, name=f'MA{ma_period}'),
                                row=1, col=1
                            )
                
                # RSI
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['RSI'], name='RSI', line=dict(color='purple')),
                    row=2, col=1
                )
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                # 布林带
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['BB_upper'], name='上轨', line=dict(color='gray', dash='dash')),
                    row=3, col=1
                )
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['BB_middle'], name='中轨', line=dict(color='black')),
                    row=3, col=1
                )
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['BB_lower'], name='下轨', line=dict(color='gray', dash='dash'),
                             fill='tonexty', fillcolor='rgba(128,128,128,0.1)'),
                    row=3, col=1
                )
                fig.add_trace(
                    go.Scatter(x=data.index, y=data['Close'], name='收盘价', line=dict(color='blue')),
                    row=3, col=1
                )
                
                fig.update_layout(height=800, showlegend=True, title_text=f"{selected_index} 技术指标分析")
                st.plotly_chart(fig, use_container_width=True)
                
                # 指标解读
                col1, col2 = st.columns(2)
                with col1:
                    st.info("""
                    **📊 RSI指标解读:**
                    - >70: 可能超买，考虑卖出
                    - <30: 可能超卖，考虑买入
                    - 50: 多空平衡线
                    """)
                
                with col2:
                    st.info("""
                    **📈 布林带解读:**
                    - 价格触及上轨: 可能回调
                    - 价格触及下轨: 可能反弹
                    - 带宽收窄: 波动率降低，可能突破
                    """)
            else:
                st.error("无法获取数据")

with tab3:
    st.subheader("数据明细")
    
    if st.button("显示详细数据", type="primary", key="show_details"):
        data = get_index_data(index_code, period_options[period])
        
        if not data.empty:
            # 显示数据表
            st.dataframe(
                data.sort_index(ascending=False),
                use_container_width=True,
                column_config={
                    "Open": st.column_config.NumberColumn(format="%.2f"),
                    "High": st.column_config.NumberColumn(format="%.2f"),
                    "Low": st.column_config.NumberColumn(format="%.2f"),
                    "Close": st.column_config.NumberColumn(format="%.2f"),
                    "Volume": st.column_config.NumberColumn(format="%d")
                }
            )
            
            # 数据统计
            st.subheader("📊 数据统计")
            stats_df = pd.DataFrame({
                '统计量': ['平均值', '标准差', '最小值', '25%分位数', '中位数', '75%分位数', '最大值'],
                '收盘价': [
                    data['Close'].mean(),
                    data['Close'].std(),
                    data['Close'].min(),
                    data['Close'].quantile(0.25),
                    data['Close'].median(),
                    data['Close'].quantile(0.75),
                    data['Close'].max()
                ],
                '成交量': [
                    data['Volume'].mean(),
                    data['Volume'].std(),
                    data['Volume'].min(),
                    data['Volume'].quantile(0.25),
                    data['Volume'].median(),
                    data['Volume'].quantile(0.75),
                    data['Volume'].max()
                ]
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
            
            # 数据下载
            csv = data.to_csv().encode('utf-8')
            st.download_button(
                label="📥 下载CSV数据",
                data=csv,
                file_name=f"{index_code}_{period}_data.csv",
                mime="text/csv"
            )
        else:
            st.error("无法获取数据")

# 页面说明
st.markdown("---")
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    ### 使用指南
    
    1. **选择指数**: 从预设列表选择或输入自定义代码
    2. **设置周期**: 选择分析的时间范围（10年适合长期趋势分析）
    3. **获取数据**: 点击"获取数据"按钮加载数据
    4. **分析图表**: 在标签页中查看不同分析视图
    
    ### 指数代码格式
    - 美股指数: ^GSPC (标普500), ^DJI (道琼斯)
    - A股指数: 000300.SS (沪深300), 000001.SS (上证指数)
    - 港股指数: ^HSI (恒生指数)
    
    ### 注意事项
    - 10年数据量较大，加载可能需要一些时间
    - 数据可能有15分钟延迟
    - 技术指标仅供参考
    - 历史表现不代表未来
    """)
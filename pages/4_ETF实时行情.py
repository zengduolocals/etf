"""
ETF实时行情页面
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils import get_realtime_price, validate_etf_code, format_etf_code

# 页面配置
st.set_page_config(
    page_title="实时行情",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ETF实时行情")
st.markdown("监控ETF实时价格和交易数据")

# 初始化session state
if 'tracked_etfs' not in st.session_state:
    st.session_state.tracked_etfs = ['510300', '510500', '159919', '588000']

# 侧边栏 - 监控管理
with st.sidebar:
    st.header("🎯 监控管理")
    
    # 添加ETF
    st.subheader("添加监控")
    new_etf = st.text_input(
        "输入ETF代码:",
        placeholder="如: 510300, SPY",
        key="new_etf_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ 添加", key="add_track"):
            if new_etf and validate_etf_code(new_etf):
                formatted_etf = format_etf_code(new_etf)
                if formatted_etf not in st.session_state.tracked_etfs:
                    st.session_state.tracked_etfs.append(formatted_etf)
                    st.success(f"已添加 {formatted_etf}")
                    st.rerun()
                else:
                    st.warning("ETF已在监控列表中")
            else:
                st.error("请输入有效的ETF代码")
    
    with col2:
        if st.button("🗑️ 清空", key="clear_track"):
            st.session_state.tracked_etfs = []
            st.rerun()
    
    # 监控列表
    st.subheader("监控列表")
    if st.session_state.tracked_etfs:
        for i, etf in enumerate(st.session_state.tracked_etfs):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{i+1}. {etf}")
            with col2:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.tracked_etfs.pop(i)
                    st.rerun()
    else:
        st.info("监控列表为空")
    
    # 预设组合
    st.subheader("💡 预设监控")
    preset_groups = {
        "A股宽基": ["510300", "510500", "159919", "588000"],
        "行业ETF": ["512000", "512010", "512880", "515050"],
        "债券黄金": ["511010", "511260", "518880", "159937"],
        "全球市场": ["SPY", "QQQ", "VT", "GLD"]
    }
    
    selected_group = st.selectbox("选择预设组:", list(preset_groups.keys()))
    
    if st.button("应用预设", key="apply_group"):
        st.session_state.tracked_etfs = preset_groups[selected_group]
        st.success(f"已应用 {selected_group} 监控组")
        st.rerun()
    
    # 自动刷新
    st.subheader("🔄 刷新设置")
    auto_refresh = st.checkbox("自动刷新", value=False)
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔(秒)", 5, 60, 30)
        st.info(f"每 {refresh_interval} 秒刷新一次")
        
        # 使用streamlit的自动刷新功能
        time.sleep(refresh_interval)
        st.rerun()

# 主内容区
if not st.session_state.tracked_etfs:
    st.warning("请先在侧边栏添加要监控的ETF")
else:
    # 刷新按钮
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### 监控 {len(st.session_state.tracked_etfs)} 个ETF")
    with col2:
        if st.button("🔄 手动刷新", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col3:
        update_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"**更新时间:** {update_time}")
    
    # 获取实时数据
    with st.spinner("正在获取实时数据..."):
        realtime_df = get_realtime_price(st.session_state.tracked_etfs)
    
    if not realtime_df.empty:
        # 标签页布局
        tab1, tab2, tab3 = st.tabs(["📊 价格表格", "📈 价格走势", "🎯 涨跌分析"])
        
        with tab1:
            # 格式化显示
            display_df = realtime_df.copy()
            
            # 添加颜色格式化
            def color_positive_green(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        color = 'green'
                    elif val < 0:
                        color = 'red'
                    else:
                        color = 'black'
                    return f'color: {color}'
                return ''
            
            # 应用样式
            styled_df = display_df.style.applymap(color_positive_green, 
                                                 subset=['涨跌额', '涨跌幅%'])
            
            # 显示表格
            st.dataframe(
                styled_df,
                use_container_width=True,
                column_config={
                    "当前价格": st.column_config.NumberColumn(format="%.3f"),
                    "涨跌额": st.column_config.NumberColumn(format="%.3f"),
                    "涨跌幅%": st.column_config.NumberColumn(format="%.2f"),
                    "昨收": st.column_config.NumberColumn(format="%.3f"),
                    "开盘": st.column_config.NumberColumn(format="%.3f"),
                    "最高": st.column_config.NumberColumn(format="%.3f"),
                    "最低": st.column_config.NumberColumn(format="%.3f"),
                    "成交量": st.column_config.NumberColumn(format="%d")
                }
            )
            
            # 汇总统计
            st.subheader("📊 市场汇总")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("平均涨跌幅", 
                         f"{display_df['涨跌幅%'].mean():.2f}%",
                         delta=f"{display_df['涨跌幅%'].mean():.2f}%")
            
            with col2:
                up_count = (display_df['涨跌幅%'] > 0).sum()
                total_count = len(display_df)
                st.metric("上涨家数", f"{up_count}/{total_count}")
            
            with col3:
                st.metric("平均价格", f"{display_df['当前价格'].mean():.3f}")
            
            with col4:
                st.metric("总成交量", f"{display_df['成交量'].sum():,}")
        
        with tab2:
            # 价格走势图
            st.subheader("价格走势比较")
            
            # 创建价格走势图
            fig_price = go.Figure()
            
            for _, row in display_df.iterrows():
                fig_price.add_trace(go.Bar(
                    x=[row['ETF代码']],
                    y=[row['当前价格']],
                    name=row['ETF代码'],
                    text=f"{row['当前价格']:.3f}",
                    textposition='auto',
                    marker_color='green' if row['涨跌幅%'] > 0 else 'red'
                ))
            
            fig_price.update_layout(
                title="ETF当前价格对比",
                xaxis_title="ETF代码",
                yaxis_title="价格",
                showlegend=False,
                height=500
            )
            
            st.plotly_chart(fig_price, use_container_width=True)
            
            # 涨跌幅图
            fig_change = px.bar(
                display_df,
                x='ETF代码',
                y='涨跌幅%',
                color='涨跌幅%',
                color_continuous_scale=['red', 'white', 'green'],
                title="ETF涨跌幅对比",
                text='涨跌幅%'
            )
            fig_change.update_traces(texttemplate='%{text:.2f}%')
            fig_change.update_layout(height=400)
            
            st.plotly_chart(fig_change, use_container_width=True)
        
        with tab3:
            # 详细分析
            st.subheader("详细分析")
            
            # 创建分析图表
            col1, col2 = st.columns(2)
            
            with col1:
                # 涨跌幅分布
                fig_dist = px.histogram(
                    display_df,
                    x='涨跌幅%',
                    nbins=20,
                    title="涨跌幅分布",
                    color_discrete_sequence=['blue']
                )
                fig_dist.update_layout(height=400)
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                # 价格-成交量散点图
                fig_scatter = px.scatter(
                    display_df,
                    x='涨跌幅%',
                    y='成交量',
                    size='当前价格',
                    color='ETF代码',
                    title="涨跌幅 vs 成交量",
                    hover_data=['名称']
                )
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # 相关性分析
            st.subheader("相关性矩阵")
            
            # 获取历史数据计算相关性
            correlation_data = []
            for etf in st.session_state.tracked_etfs[:5]:  # 限制数量避免过多计算
                try:
                    # 获取5天数据计算日相关性
                    hist_data = get_etf_data(etf, "5d")
                    if not hist_data.empty:
                        correlation_data.append(hist_data['Close'])
                except:
                    continue
            
            if len(correlation_data) > 1:
                corr_df = pd.DataFrame(correlation_data).T
                corr_df.columns = st.session_state.tracked_etfs[:len(correlation_data)]
                corr_matrix = corr_df.corr()
                
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto='.2f',
                    title="ETF价格相关性",
                    color_continuous_scale='RdBu',
                    aspect="auto"
                )
                fig_corr.update_layout(height=500)
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("需要至少2个ETF的历史数据来计算相关性")
        
        # 数据导出
        st.markdown("---")
        st.subheader("📥 数据导出")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV导出
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下载CSV数据",
                data=csv,
                file_name=f"etf_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # JSON导出
            json_str = display_df.to_json(orient='records', force_ascii=False)
            st.download_button(
                label="下载JSON数据",
                data=json_str,
                file_name=f"etf_realtime_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    else:
        st.error("无法获取实时数据，请检查ETF代码或网络连接")

# 页面说明
st.markdown("---")
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    ### 实时行情使用指南
    
    1. **添加监控**:
       - 在侧边栏输入ETF代码
       - 点击添加按钮或选择预设组
    
    2. **数据查看**:
       - 表格视图: 查看详细价格信息
       - 图表视图: 可视化价格走势
       - 分析视图: 深入分析市场表现
    
    3. **自动刷新**:
       - 开启自动刷新功能
       - 设置刷新间隔
       - 实时跟踪市场变化
    
    4. **数据导出**:
       - 导出CSV格式数据
       - 导出JSON格式数据
       - 保存当前快照
    
    ### ETF代码格式
    - A股ETF: 510300 (沪深300ETF)
    - 美股ETF: SPY (标普500ETF)
    - 港股ETF: 2800.HK (盈富基金)
    
    ### 注意事项
    - 实时数据可能有延迟
    - 部分ETF可能无法获取数据
    - 建议使用主流ETF代码
    - 数据仅供参考
    """)
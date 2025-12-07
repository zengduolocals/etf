"""
首页 - ETF分析应用
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import validate_etf_code, format_etf_code

# 页面配置
st.set_page_config(
    page_title="衡远证券智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 应用标题
st.title("📈 衡远证券智能分析系统")
st.markdown("专业、智能、实时的多市场投资分析平台")
st.markdown("---")

# 两列布局
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🌟 应用介绍")
    st.markdown("""
    ### 欢迎使用 衡远证券智能分析系统 v2.2.0
    
    本应用提供一站式多市场投资分析解决方案，包含以下核心功能：
    
    **📊 主要功能模块：**
    
    1. **指数分析** - 查看主要指数历史走势和技术指标
    2. **组合建议** - 构建和优化投资组合
    3. **实时行情** - 监控实时价格和交易数据
    4. **报告中心** - 生成专业投资分析报告
    5. **美股选股** - 🇺🇸 基于AI多因子模型的美股智能选股 *新*
    
    **🎯 核心特色：**
    - 多维度风险评估
    - 智能组合优化
    - 实时数据更新
    - 专业报告生成
    - 美股多因子分析
    """)

with col2:
    st.header("🚀 快速开始")
    
    # 市场选择
    market = st.radio("选择市场:", ["A股", "美股"], horizontal=True)
    
    if market == "A股":
        # 快速查询ETF
        st.subheader("快速查询ETF")
        etf_code = st.text_input("输入ETF代码:", placeholder="如: 510300")
        
        if st.button("快速查询", type="primary", use_container_width=True):
            if etf_code and validate_etf_code(etf_code):
                formatted_code = format_etf_code(etf_code)
                st.success(f"ETF代码有效: {formatted_code}")
                st.session_state.quick_code = formatted_code
                st.switch_page("pages/4_ETF实时行情.py")
            else:
                st.error("请输入有效的ETF代码")
    else:
        # 美股快速查询
        st.subheader("美股快速查询")
        us_stock = st.text_input("输入美股代码:", placeholder="如: AAPL")
        
        if st.button("快速分析", type="primary", use_container_width=True):
            if us_stock:
                st.success(f"美股代码: {us_stock.upper()}")
                st.session_state.quick_stock = us_stock.upper()
                st.switch_page("pages/6_美股选股.py")
            else:
                st.error("请输入美股代码")

# 功能模块介绍
st.markdown("---")
st.header("🔍 功能模块详解")

cols = st.columns(5)  # 改为5列

with cols[0]:
    st.markdown('<div style="text-align: center; margin-bottom: 10px;"><span style="font-size: 2em;">📊</span></div>', unsafe_allow_html=True)
    st.markdown("### 指数分析")
    st.markdown("""
    - 主要指数历史数据
    - K线图可视化
    - 技术指标分析
    - 多周期查看
    """)
    if st.button("进入指数分析", key="btn_index", use_container_width=True):
        st.switch_page("pages/2_指数分析.py")

with cols[1]:
    st.markdown('<div style="text-align: center; margin-bottom: 10px;"><span style="font-size: 2em;">⚖️</span></div>', unsafe_allow_html=True)
    st.markdown("### 组合建议")
    st.markdown("""
    - 投资组合构建
    - 风险收益分析
    - 权重优化
    - 回测模拟
    """)
    if st.button("进入组合建议", key="btn_portfolio", use_container_width=True):
        st.switch_page("pages/3_组合建议.py")

with cols[2]:
    st.markdown('<div style="text-align: center; margin-bottom: 10px;"><span style="font-size: 2em;">📈</span></div>', unsafe_allow_html=True)
    st.markdown("### 实时行情")
    st.markdown("""
    - 实时价格监控
    - 涨跌幅分析
    - 成交量跟踪
    - 价格预警
    """)
    if st.button("进入实时行情", key="btn_realtime", use_container_width=True):
        st.switch_page("pages/4_ETF实时行情.py")

with cols[3]:
    st.markdown('<div style="text-align: center; margin-bottom: 10px;"><span style="font-size: 2em;">📋</span></div>', unsafe_allow_html=True)
    st.markdown("### 报告中心")
    st.markdown("""
    - 专业报告生成
    - 数据导出
    - 图表汇总
    - PDF下载
    """)
    if st.button("进入报告中心", key="btn_report", use_container_width=True):
        st.switch_page("pages/5_报告中心.py")

with cols[4]:
    st.markdown('<div style="text-align: center; margin-bottom: 10px;"><span style="font-size: 2em;">🇺🇸</span></div>', unsafe_allow_html=True)
    st.markdown("### 美股选股")
    st.markdown("""
    - AI多因子模型
    - 美股智能筛选
    - 历史回测分析
    - 专业选股报告
    """)
    if st.button("进入美股选股", key="btn_us_stock", type="primary", use_container_width=True):
        st.switch_page("pages/6_美股选股.py")

# 新增美股选股功能介绍
st.markdown("---")
st.header("🇺🇸 美股智能选股模块介绍")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("""
    ### 📊 五大核心因子模型
    
    **1. 价值因子**
    - 市盈率(PE)、市净率(PB)分析
    - 股息率筛选
    - 低估值股票识别
    
    **2. 成长因子**
    - 营收增长率分析
    - 净利润增长率评估
    - 高成长性股票筛选
    
    **3. 质量因子**
    - ROE、ROA质量评估
    - 财务健康状况分析
    - 现金流质量检测
    
    **4. 动量因子**
    - 价格动量分析
    - 相对强度指标
    - 趋势识别
    
    **5. 风险因子**
    - 波动率控制
    - Beta值分析
    - 风险调整收益
    """)

with col_right:
    st.markdown("""
    ### 🎯 三大选股策略
    
    **多因子综合策略**
    - 五大因子加权评分
    - 智能权重配置
    - 综合排名选股
    
    **行业轮动策略**
    - 行业ETF分析
    - 板块轮动识别
    - 行业配置优化
    
    **风险平价策略**
    - 波动率均衡配置
    - 风险贡献平衡
    - 组合风险优化
    """)

# 使用说明
st.markdown("---")
st.header("📖 使用说明")

with st.expander("点击查看详细使用指南", expanded=False):
    tabs = st.tabs(["A股分析", "美股选股", "注意事项"])
    
    with tabs[0]:
        st.markdown("""
        ### 🎯 A股分析使用步骤
        
        1. **数据获取**
           - 在相应页面输入ETF或指数代码
           - 选择时间周期和参数
           - 点击"获取数据"按钮
        
        2. **分析功能**
           - 查看图表和指标
           - 调整分析参数
           - 比较不同资产表现
        
        3. **组合优化**
           - 添加多个ETF到组合
           - 设置权重或自动优化
           - 查看风险收益特征
        
        4. **报告生成**
           - 选择报告类型
           - 自定义报告内容
           - 下载PDF格式报告
        """)
    
    with tabs[1]:
        st.markdown("""
        ### 🇺🇸 美股选股使用步骤
        
        1. **策略配置**
           - 选择选股策略（多因子/行业轮动/风险平价）
           - 设置因子权重和筛选条件
           - 配置回测参数
        
        2. **股票筛选**
           - 选择股票池（标普500/纳斯达克/自定义）
           - 设置筛选条件（市值/估值/成长性）
           - 运行智能选股
        
        3. **回测分析**
           - 查看历史回测表现
           - 分析绩效指标
           - 优化策略参数
        
        4. **报告生成**
           - 生成选股报告
           - 导出股票列表
           - 下载分析图表
        """)
    
    with tabs[2]:
        st.markdown("""
        ### ⚠️ 注意事项
        
        **数据说明：**
        - A股数据来源：公开市场数据
        - 美股数据来源：Yahoo Finance
        - 数据更新频率：实时/15分钟延迟
        - 数据仅供参考，可能存在延迟
        
        **风险提示：**
        - 历史表现不代表未来收益
        - 投资需谨慎，风险自担
        - 建议结合专业意见
        - 美股投资需注意汇率风险
        
        **免责声明：**
        - 本工具提供的数据和分析仅供参考
        - 不构成任何投资建议或保证
        - 用户应独立判断和决策
        """)

# 侧边栏信息
with st.sidebar:
    st.markdown("""
    <div style="text-align: center;">
        <div style="font-size: 3em;">📈</div>
        <h2>衡远证券</h2>
        <p>智能分析系统</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.header("🧭 导航菜单")
    
    # 快速导航按钮
    if st.button("🏠 首页", use_container_width=True, type="secondary"):
        st.rerun()
    
    if st.button("📊 指数分析", use_container_width=True):
        st.switch_page("pages/2_指数分析.py")
    
    if st.button("⚖️ 组合建议", use_container_width=True):
        st.switch_page("pages/3_组合建议.py")
    
    if st.button("📈 实时行情", use_container_width=True):
        st.switch_page("pages/4_ETF实时行情.py")
    
    if st.button("📋 报告中心", use_container_width=True):
        st.switch_page("pages/5_报告中心.py")
    
    if st.button("🇺🇸 美股选股", use_container_width=True, type="primary"):
        st.switch_page("pages/6_美股选股.py")
    
    st.markdown("---")
    
    # 数据更新状态
    st.subheader("📊 数据状态")
    st.info(f"数据最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 市场状态概览
    st.subheader("📈 市场概览")
    
    # A股常用ETF
    st.markdown("**A股常用ETF**")
    etf_list = pd.DataFrame({
        '代码': ['510300', '510500', '159919', '588000'],
        '名称': ['沪深300ETF', '中证500ETF', '沪深300ETF', '科创50ETF'],
        '市场': ['上海', '上海', '深圳', '上海']
    })
    st.dataframe(etf_list, use_container_width=True, hide_index=True)
    
    # 美股主要指数
    st.markdown("**美股主要指数**")
    us_index = pd.DataFrame({
        '代码': ['^GSPC', '^IXIC', '^DJI', '^RUT'],
        '名称': ['标普500', '纳斯达克', '道琼斯', '罗素2000'],
        '交易所': ['NYSE', 'NASDAQ', 'NYSE', 'NASDAQ']
    })
    st.dataframe(us_index, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # 应用信息
    st.subheader("ℹ️ 应用信息")
    st.markdown("""
    **版本**: 2.2.0  
    **更新日期**: 2025-12-05  
    **新增功能**: 美股智能选股  
    **数据源**: Yahoo Finance + 公开数据  
    **技术支持**: zengduo@jdvcap.com
    """)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px;'>
    <h4>© 2024-2025 衡远证券智能分析系统</h4>
    <p style='color: #666;'>数据仅供参考，投资需谨慎 | 版本 v2.2.0 🇺🇸</p>
    <p style='color: #888; font-size: 0.9em;'>
        技术支持: zengduo@jdvcap.com | 
        免责声明: 本系统提供的数据和分析仅供参考，不构成任何投资建议
    </p>
</div>
""", unsafe_allow_html=True)
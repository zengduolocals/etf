"""
app.py - 增强版ETF分析系统入口
包含用户登录、缓存管理、错误处理和性能监控
"""

import sys
print("=== 诊断信息 ===")
print("/Users/zengfrank/Desktop/indexonlineapp/venv/bin/python3:", sys.executable)

import streamlit as st
import os
from datetime import datetime
import time

# 添加当前目录到Python路径，确保导入正常
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入认证模块
try:
    from auth_simple import login_widget, check_permission, show_user_profile, require_login
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    st.warning(f"用户认证模块加载失败: {e}")

# 应用配置
st.set_page_config(
    page_title="衡远证券智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/etf-analysis-app',
        'Report a bug': 'https://github.com/yourusername/etf-analysis-app/issues',
        'About': """
        # 衡远证券智能分析系统 v2.3
        
        ## 功能特性
        - 多市场数据获取
        - 投资组合优化
        - 实时行情监控
        - 专业报告生成
        - 美股智能选股
        - 用户认证系统
        
        ## 技术支持
        - Email: zengduo@jdvcap.com
        
        """
    }
)

# 自定义CSS样式
st.markdown("""
<style>
    /* 主容器 */
    .main {
        padding: 2rem;
    }
    
    /* 标题样式 */
    .title {
        color: #1E88E5;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 副标题 */
    .subtitle {
        color: #546E7A;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 3rem;
    }
    
    /* 功能卡片 */
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 2rem;
        color: white;
        height: 100%;
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
    }
    
    .feature-card h3 {
        color: white;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* 登录相关样式 */
    .login-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 2rem;
        color: white;
        margin: 2rem auto;
        max-width: 500px;
    }
    
    .login-title {
        text-align: center;
        font-size: 2rem;
        margin-bottom: 1.5rem;
    }
    
    .login-button {
        background-color: white !important;
        color: #667eea !important;
        border: none !important;
        font-weight: bold !important;
    }
    
    /* 状态指示器 */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online {
        background-color: #4CAF50;
        box-shadow: 0 0 10px #4CAF50;
    }
    
    .status-offline {
        background-color: #f44336;
    }
    
    /* 按钮组 */
    .btn-group {
        display: flex;
        gap: 10px;
        margin-top: 20px;
    }
    
    /* 数据统计卡片 */
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        border-left: 4px solid #1E88E5;
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
    }
    
    .stat-label {
        color: #546E7A;
        font-size: 0.9rem;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

class ETFApp:
    """ETF应用管理类"""
    
    def __init__(self):
        self.start_time = time.time()
        self.app_version = "2.3.0"  # 更新版本号
        self.last_update = "2025-12-05"
        
    def get_app_uptime(self):
        """获取应用运行时间"""
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def clear_cache(self):
        """清除应用缓存"""
        try:
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            if hasattr(st, 'cache_resource'):
                st.cache_resource.clear()
            return True
        except Exception as e:
            st.error(f"清除缓存失败: {e}")
            return False
    
    def check_dependencies(self):
        """检查依赖包"""
        import importlib
        import pkg_resources
        
        dependencies = [
            'streamlit',
            'yfinance',
            'pandas',
            'numpy',
            'plotly',
            'scipy',
            'reportlab',
            'streamlit-authenticator',
            'bcrypt',
            'pyjwt'
        ]
        
        missing = []
        for dep in dependencies:
            try:
                importlib.import_module(dep.replace('-', '_'))
            except ImportError:
                missing.append(dep)
        
        return missing

def show_login_page():
    """显示登录页面"""
    st.markdown('<h1 class="title">🔐 衡远证券智能分析系统</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">请登录以访问专业投资分析工具</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown("""
            <div class="login-container">
                <h2 class="login-title">用户登录</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if AUTH_AVAILABLE:
                # 显示登录组件
                authentication_status, name = login_widget()
                
                if authentication_status:
                    # 登录成功，显示欢迎信息
                    st.success(f"登录成功！欢迎回来，{name}！")
                    time.sleep(1)
                    st.rerun()
                elif authentication_status is False:
                    st.error("用户名或密码错误")
                else:
                    # 显示登录提示
                    st.info("""
                    ### 默认测试账号
                    
                    **管理员账号:**
                    - 用户名: admin
                    - 密码: admin123
                    
                    **访客账号:**
                    - 用户名: guest
                    - 密码: guest123
                    
                    ### 新用户注册
                    请联系管理员获取账号或使用访客账号体验基础功能。
                    """)
            else:
                st.error("用户认证系统不可用")
                st.info("请联系系统管理员")
    
    # 显示系统信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("""
        ### 🔒 安全认证
        - 用户分级权限管理
        - 密码加密存储
        - 会话安全控制
        """)
    
    with col2:
        st.info("""
        ### 📊 专业功能
        - 多市场数据分析
        - 智能投资建议
        - 实时行情监控
        """)
    
    with col3:
        st.info("""
        ### 🚀 高性能
        - 数据缓存优化
        - 异步数据加载
        - 实时数据更新
        """)

def main():
    """主函数"""
    
    # 检查用户登录状态
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    # 如果用户未登录，显示登录页面
    if not st.session_state['authenticated']:
        show_login_page()
        return
    
    # 用户已登录，显示主应用
    app = ETFApp()
    
    # 显示用户信息
    if AUTH_AVAILABLE:
        show_user_profile()
    
    # 应用标题
    st.markdown('<h1 class="title">📈 衡远证券智能分析系统</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">欢迎，{st.session_state.get("username", "用户")}！专业、智能、实时的投资分析平台</p>', unsafe_allow_html=True)
    
    # 状态栏
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{app.app_version}</div>
            <div class="stat-label">应用版本</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        uptime = app.get_app_uptime()
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{uptime}</div>
            <div class="stat-label">运行时间</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">6</div>
            <div class="stat-label">功能模块</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">200+</div>
            <div class="stat-label">支持资产</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 功能模块展示
    st.markdown("## 🚀 核心功能")
    
    cols = st.columns(6)
    
    features = [
        {
            "title": "🏠 首页",
            "description": "应用介绍和导航中心",
            "page": "pages/1_首页.py",
            "color": "#2196F3",
            "icon": "🏠",
            "required_role": "user"
        },
        {
            "title": "📊 指数分析",
            "description": "指数历史数据和技术分析",
            "page": "pages/2_指数分析.py",
            "color": "#4CAF50",
            "icon": "📊",
            "required_role": "user"
        },
        {
            "title": "⚖️ 组合建议",
            "description": "投资组合构建和优化",
            "page": "pages/3_组合建议.py",
            "color": "#FF9800",
            "icon": "⚖️",
            "required_role": "user"
        },
        {
            "title": "📈 实时行情",
            "description": "ETF实时价格监控",
            "page": "pages/4_ETF实时行情.py",
            "color": "#9C27B0",
            "icon": "📈",
            "required_role": "user"
        },
        {
            "title": "📋 报告中心",
            "description": "专业分析报告生成",
            "page": "pages/5_报告中心.py",
            "color": "#F44336",
            "icon": "📋",
            "required_role": "user"
        },
        {
            "title": "🇺🇸 美股选股",
            "description": "基于AI多因子模型的美股智能选股",
            "page": "pages/6_美股选股.py",
            "color": "#2E86AB",
            "icon": "🇺🇸",
            "required_role": "user"
        }
    ]
    
    user_role = st.session_state.get('user_role', 'guest')
    
    for idx, feature in enumerate(features):
        with cols[idx]:
            with st.container():
                st.markdown(f"""
                <div style="
                    background: {feature['color']};
                    border-radius: 15px;
                    padding: 1.5rem;
                    color: white;
                    height: 250px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                ">
                    <div>
                        <h3 style="color: white; margin-bottom: 1rem;">{feature['icon']} {feature['title']}</h3>
                        <p style="color: rgba(255,255,255,0.9);">{feature['description']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 检查用户权限
                has_permission = check_permission(feature['required_role'])
                
                if has_permission:
                    if st.button(f"进入{feature['title'].split()[0]}", key=f"btn_{idx}", 
                               use_container_width=True, type="primary"):
                        try:
                            st.switch_page(feature['page'])
                        except Exception as e:
                            st.error(f"页面跳转失败: {e}")
                            st.info(f"请确保文件 {feature['page']} 存在")
                else:
                    st.button(f"进入{feature['title'].split()[0]}", 
                            use_container_width=True, disabled=True,
                            help="权限不足，请联系管理员")
    
    # 管理员专用功能
    if user_role == 'admin':
        st.markdown("---")
        st.markdown("## ⚙️ 管理员功能")
        
        admin_cols = st.columns(3)
        
        with admin_cols[0]:
            if st.button("👥 用户管理", use_container_width=True):
                st.info("用户管理功能开发中...")
        
        with admin_cols[1]:
            if st.button("📊 系统监控", use_container_width=True):
                st.info("系统监控功能开发中...")
        
        with admin_cols[2]:
            if st.button("🔧 系统设置", use_container_width=True):
                st.info("系统设置功能开发中...")
    
    # 快速开始指南
    st.markdown("---")
    st.markdown("## 🎯 快速开始")
    
    with st.expander("点击查看三步快速开始指南", expanded=True):
        steps = st.columns(3)
        
        with steps[0]:
            st.markdown("### 1️⃣ 选择功能")
            st.markdown("""
            1. 点击上方功能卡片
            2. 或使用侧边栏导航
            3. 选择需要的分析模块
            """)
        
        with steps[1]:
            st.markdown("### 2️⃣ 输入参数")
            st.markdown("""
            1. 输入ETF或指数股票代码
            2. 设置分析周期
            3. 调整其他参数
            """)
        
        with steps[2]:
            st.markdown("### 3️⃣ 查看结果")
            st.markdown("""
            1. 查看可视化图表
            2. 分析投资指标
            3. 下载报告数据
            """)
    
    st.markdown("---")
    
    # 应用管理
    st.markdown("## ⚙️ 应用管理")
    
    management_cols = st.columns(4)
    
    with management_cols[0]:
        if st.button("🔄 刷新缓存", use_container_width=True):
            if app.clear_cache():
                st.success("缓存已刷新！")
                st.rerun()
    
    with management_cols[1]:
        if st.button("🔍 检查依赖", use_container_width=True):
            missing = app.check_dependencies()
            if missing:
                st.error(f"缺少依赖包: {', '.join(missing)}")
                st.code("pip install " + " ".join(missing))
            else:
                st.success("所有依赖包已安装！")
    
    with management_cols[2]:
        if st.button("📊 系统状态", use_container_width=True):
            try:
                import psutil
                import platform
                
                sys_info = {
                    "系统": platform.system(),
                    "版本": platform.version(),
                    "处理器": platform.processor(),
                    "Python版本": platform.python_version(),
                    "内存使用": f"{psutil.virtual_memory().percent}%",
                    "CPU使用率": f"{psutil.cpu_percent()}%",
                    "登录用户": st.session_state.get('username', '未登录'),
                    "用户角色": st.session_state.get('user_role', '未设置')
                }
                
                st.json(sys_info)
            except ImportError:
                st.warning("请先安装psutil包: pip install psutil")
    
    with management_cols[3]:
        if st.button("🐛 检查页面", use_container_width=True):
            # 检查所有页面文件是否存在
            missing_pages = []
            for feature in features:
                if not os.path.exists(feature['page']):
                    missing_pages.append(feature['page'])
            
            if missing_pages:
                st.error(f"缺失页面文件: {', '.join(missing_pages)}")
            else:
                st.success("所有页面文件完整！")
    
    # 侧边栏
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 2rem;">📈</div>
            <h2 style="color: #1E88E5;">衡远证券</h2>
            <p style="color: #546E7A;">智能分析系统</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 导航菜单
        st.markdown("### 🧭 导航菜单")
        
        selected_page = st.selectbox(
            "选择功能页面",
            ["首页", "指数分析", "组合建议", "实时行情", "报告中心", "美股选股"],
            label_visibility="collapsed"
        )
        
        page_map = {
            "首页": "pages/1_首页.py",
            "指数分析": "pages/2_指数分析.py",
            "组合建议": "pages/3_组合建议.py",
            "实时行情": "pages/4_ETF实时行情.py",
            "报告中心": "pages/5_报告中心.py",
            "美股选股": "pages/6_美股选股.py"
        }
        
        if st.button("🚀 前往选中页面", type="primary", use_container_width=True):
            try:
                st.switch_page(page_map[selected_page])
            except Exception as e:
                st.error(f"页面跳转失败: {e}")
        
        st.markdown("---")
        
        # 快捷操作
        st.markdown("### ⚡ 快捷操作")
        
        quick_actions = st.columns(2)
        with quick_actions[0]:
            if st.button("📈 沪深300", use_container_width=True):
                st.session_state.quick_etf = "510300"
                st.switch_page("pages/2_指数分析.py")
        
        with quick_actions[1]:
            if st.button("🇺🇸 标普500", use_container_width=True):
                st.session_state.quick_etf = "^GSPC"
                st.switch_page("pages/2_指数分析.py")
        
        st.markdown("---")
        
        # 数据源信息
        st.markdown("### 📡 数据源")
        st.info("""
        **数据提供商:**
        - Yahoo Finance
        - 公开市场数据
        
        **更新频率:**
        - 实时数据: 15分钟延迟
        - 历史数据: 每日更新
        
        **支持市场:**
        - A股、港股、美股
        - 主要全球指数
        """)
        
        st.markdown("---")
        
        # 应用信息
        st.markdown("### ℹ️ 应用信息")
        
        info_data = {
            "版本": app.app_version,
            "最后更新": app.last_update,
            "运行时间": app.get_app_uptime(),
            "登录用户": st.session_state.get('username', '未登录'),
            "用户角色": st.session_state.get('user_role', '未设置'),
            "开发者": "DUO ZENG",
            "技术支持": "zengduo@jdvcap.com"
        }
        
        for key, value in info_data.items():
            st.text(f"{key}: {value}")
    
    # 页脚
    st.markdown("---")
    
    footer_cols = st.columns([2, 1, 1])
    
    with footer_cols[0]:
        st.markdown("""
        **© 2025 衡远证券智能分析系统**
        
        **版本更新 v2.3.0:**
        - 新增用户认证系统
        - 增加权限管理功能
        - 优化数据安全性
        - 改进用户体验
        
        免责声明：本应用提供的数据和分析仅供参考，不构成任何投资建议。
        用户应自行承担投资风险，并建议咨询专业投资顾问。
        """)
    
    with footer_cols[1]:
        st.markdown("""
        **相关链接**
        - [用户手册](https://example.com)
        - [API文档](https://example.com/api)
        - [更新日志](https://example.com/changelog)
        """)
    
    with footer_cols[2]:
        st.markdown("""
        **联系方式**
        - Email: zengduo@jdvcap.com
        - 技术支持: support@hengyuan.com
        - 业务咨询: business@hengyuan.com
        """)

if __name__ == "__main__":
    # 设置环境变量
    os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
    os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'true'
    
    # 初始化session state
    if 'quick_etf' not in st.session_state:
        st.session_state.quick_etf = ""
    if 'quick_stock' not in st.session_state:
        st.session_state.quick_stock = ""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'user_role' not in st.session_state:
        st.session_state.user_role = "guest"
    
    # 运行主函数
    main()
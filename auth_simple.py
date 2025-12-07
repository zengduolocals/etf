"""
auth_simple.py - 极简用户认证系统 (兼容版)
功能：管理员/用户两级登录，管理员可修改账户信息
特点：无外部依赖、无密码哈希、完全兼容旧代码
"""

import streamlit as st

# ==================== 系统配置 ====================
# 默认账户信息 (用户名: [密码, 角色, 显示名称])
DEFAULT_ACCOUNTS = {
    "admin": ["admin123", "admin", "系统管理员"],
    "user": ["user123", "user", "普通用户"]
}

# ==================== 核心函数 ====================

def init_session_state():
    """初始化会话状态"""
    if 'accounts' not in st.session_state:
        st.session_state.accounts = DEFAULT_ACCOUNTS.copy()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    
    if 'display_name' not in st.session_state:
        st.session_state.display_name = None

def check_login(username, password):
    """检查用户名和密码"""
    if username in st.session_state.accounts:
        stored_password, role, display_name = st.session_state.accounts[username]
        if password == stored_password:
            return True, role, display_name
    return False, None, None

def login_widget():
    """
    显示登录界面
    返回: (authentication_status, display_name) - 兼容旧版本
    """
    init_session_state()
    
    # 如果已登录，显示用户信息和登出按钮
    if st.session_state.logged_in:
        show_logged_in_status()
        return True, st.session_state.display_name
    
    # 未登录状态：显示登录表单
    return show_login_form_compatible()

def show_login_form_compatible():
    """兼容旧版本的登录表单，返回2个值"""
    with st.sidebar:
        st.markdown("---")
        st.subheader("🔐 用户登录")
        
        # 登录表单
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            
            submitted = st.form_submit_button("登录", use_container_width=True, type="primary")
            
            if submitted:
                if username and password:
                    success, role, display_name = check_login(username, password)
                    
                    if success:
                        # 更新会话状态
                        st.session_state.logged_in = True
                        st.session_state.current_user = username
                        st.session_state.user_role = role
                        st.session_state.display_name = display_name
                        
                        st.success(f"✅ 登录成功！欢迎 {display_name}")
                        st.rerun()
                        return True, display_name
                    else:
                        st.error("❌ 用户名或密码错误")
                else:
                    st.warning("⚠️ 请输入用户名和密码")
        
        # 默认账户提示
        with st.expander("默认账户", expanded=False):
            st.info("""
            **管理员账户**
            - 用户名: `admin`
            - 密码: `admin123`
            
            **普通用户账户**
            - 用户名: `user`
            - 密码: `user123`
            """)
    
    return False, None

def show_logged_in_status():
    """显示已登录状态"""
    with st.sidebar:
        # 用户信息卡片
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        ">
            <h4 style="margin:0;">👤 {st.session_state.display_name}</h4>
            <p style="margin:5px 0; opacity:0.9;">{st.session_state.current_user}</p>
            <div style="
                background: rgba(255,255,255,0.2);
                display: inline-block;
                padding: 3px 10px;
                border-radius: 15px;
                font-size: 12px;
            ">
                {'管理员' if st.session_state.user_role == 'admin' else '普通用户'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 登出按钮 - 使用callback确保稳定性
        if st.button("🚪 退出登录", key="logout_btn", use_container_width=True, type="primary"):
            perform_logout()
            st.rerun()
        
        # 如果是管理员，显示账户管理选项
        if st.session_state.user_role == 'admin':
            st.markdown("---")
            if st.button("⚙️ 管理账户", key="manage_accounts", use_container_width=True):
                st.session_state.show_account_management = True
        
        # 账户管理面板
        if st.session_state.get('show_account_management', False):
            show_account_management()

def perform_logout():
    """执行退出登录"""
    # 1. 清除所有会话状态（除了账户数据）
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.display_name = None
    st.session_state.show_account_management = False
    
    # 2. 添加一个小延迟确保状态更新
    import time
    time.sleep(0.1)

def show_account_management():
    """显示账户管理界面（仅管理员可见）"""
    with st.sidebar.expander("账户管理", expanded=True):
        st.write("### 修改账户信息")
        
        # 选择要修改的账户
        account_type = st.selectbox(
            "选择账户类型",
            ["管理员账户 (admin)", "用户账户 (user)"],
            key="account_selector"
        )
        
        # 根据选择显示当前信息
        target_account = "admin" if "admin" in account_type else "user"
        current_password, current_role, current_name = st.session_state.accounts[target_account]
        
        # 修改表单
        with st.form(f"edit_account_{target_account}"):
            st.write(f"**当前信息**")
            st.write(f"- 用户名: {target_account}")
            st.write(f"- 显示名: {current_name}")
            
            new_display_name = st.text_input("新显示名", value=current_name, key=f"name_{target_account}")
            new_password = st.text_input("新密码", type="password", value=current_password, key=f"pwd_{target_account}")
            confirm_password = st.text_input("确认新密码", type="password", key=f"confirm_{target_account}")
            
            submitted = st.form_submit_button("保存更改", use_container_width=True)
            
            if submitted:
                if new_password != confirm_password:
                    st.error("❌ 两次输入的密码不一致")
                elif not new_password:
                    st.error("❌ 密码不能为空")
                else:
                    # 更新账户信息
                    st.session_state.accounts[target_account] = [
                        new_password, 
                        current_role, 
                        new_display_name
                    ]
                    
                    # 如果当前登录用户修改了自己的账户，更新显示名
                    if st.session_state.current_user == target_account:
                        st.session_state.display_name = new_display_name
                    
                    st.success(f"✅ {target_account}账户信息已更新！")
                    st.rerun()

# ==================== 兼容性函数 ====================

def show_user_profile():
    """
    兼容旧版本代码的函数
    注意：在极简版本中，用户信息已自动显示在侧边栏
    此函数仅用于兼容，避免导入错误
    """
    if st.session_state.get('logged_in'):
        st.sidebar.info(f"👤 当前用户: {st.session_state.get('display_name', '')}")
        
        # 简化的登出按钮
        if st.sidebar.button("退出登录", key="compat_logout"):
            perform_logout()
            st.rerun()
    else:
        st.sidebar.warning("请先登录")

def login_widget_extended():
    """
    扩展版登录组件，返回3个值
    返回: (logged_in, username, display_name)
    """
    init_session_state()
    
    if st.session_state.logged_in:
        show_logged_in_status()
        return True, st.session_state.current_user, st.session_state.display_name
    
    # 调用原有的登录逻辑
    success, display_name = login_widget()
    if success:
        return True, st.session_state.current_user, display_name
    
    return False, None, None

# ==================== 权限检查函数 ====================

def check_permission(required_role="user"):
    """
    检查用户权限
    参数: required_role - 需要的角色 ("admin" 或 "user")
    返回: bool - 是否有权限
    """
    if not st.session_state.logged_in:
        return False
    
    # 角色权限层级：admin > user
    role_level = {"guest": 0, "user": 1, "admin": 2}
    
    user_level = role_level.get(st.session_state.user_role, 0)
    required_level = role_level.get(required_role, 1)
    
    return user_level >= required_level

def require_login(required_role="user"):
    """
    页面权限装饰器
    用法: @require_login("admin")
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_permission(required_role):
                st.error(f"⛔ 权限不足")
                st.info(f"此功能需要 **{required_role}** 权限")
                
                if not st.session_state.logged_in:
                    st.warning("请先登录")
                elif st.session_state.user_role == "user":
                    st.warning(f"当前账户 '{st.session_state.display_name}' 是普通用户")
                
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化会话状态
    init_session_state()
    
    # 设置页面配置
    st.set_page_config(page_title="简易认证系统", layout="wide")
    
    # 显示登录组件
    st.title("🔐 极简用户认证系统")
    
    # 兼容旧版本调用方式
    auth_status, name = login_widget()
    
    if auth_status:
        st.success(f"### 欢迎使用，{name}！")
        
        # 显示当前用户信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("当前用户", name)
        with col2:
            st.metric("用户角色", "管理员" if st.session_state.user_role == "admin" else "普通用户")
        with col3:
            st.metric("登录状态", "已登录")
        
        st.markdown("---")
        
        # 权限测试区域
        st.write("### 权限测试")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**用户功能测试**")
            if check_permission("user"):
                st.success("✅ 有用户权限")
                st.button("测试用户功能", key="user_func")
            else:
                st.error("❌ 无用户权限")
        
        with col2:
            st.write("**管理员功能测试**")
            if check_permission("admin"):
                st.success("✅ 有管理员权限")
                if st.button("测试管理员功能", key="admin_func"):
                    st.info("这是一个只有管理员能看到的功能")
            else:
                st.error("❌ 无管理员权限")
    
    else:
        st.info("### 请使用左侧侧边栏登录")
        st.write("这是一个极简的认证系统演示，特点如下：")
        st.markdown("""
        - ✅ **无外部依赖**：不使用streamlit-authenticator等第三方库
        - ✅ **退出稳定**：退出登录功能可靠
        - ✅ **权限管理**：管理员/用户两级权限
        - ✅ **账户管理**：管理员可修改账户信息
        - ✅ **完全兼容**：兼容旧版本代码调用方式
        """)
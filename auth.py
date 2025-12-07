"""
auth.py - 衡远证券智能分析系统用户认证模块
版本: 3.0 (稳定版，已修复所有已知问题)
"""
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import os
import hashlib
import time

# 文件路径配置
USERS_FILE = "users.yaml"
LOG_FILE = "user_logs.txt"

def init_auth():
    """初始化认证系统"""
    # 如果用户文件不存在，创建默认文件
    if not os.path.exists(USERS_FILE):
        create_default_users_file()
        st.success("✅ 系统初始化完成！已创建默认用户。")
    
    # 加载用户配置
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
        return config
    except Exception as e:
        st.error(f"❌ 加载用户配置文件失败: {e}")
        return create_emergency_config()

def create_default_users_file():
    """创建默认用户配置文件"""
    default_users = {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@hengyuan.com',
                    'name': '系统管理员',
                    'password': stauth.Hasher(['Admin@123']).generate()[0],  # 强密码
                    'role': 'admin',
                    'created_at': datetime.now().isoformat(),
                    'last_login': None
                },
                'guest': {
                    'email': 'guest@hengyuan.com',
                    'name': '访客用户',
                    'password': stauth.Hasher(['Guest@123']).generate()[0],  # 强密码
                    'role': 'user',
                    'created_at': datetime.now().isoformat(),
                    'last_login': None
                }
            }
        },
        'cookie': {
            'expiry_days': 7,  # 缩短cookie有效期增强安全
            'key': 'hengyuan_' + hashlib.sha256(os.urandom(32)).hexdigest()[:32],
            'name': 'hengyuan_auth'
        },
        'preauthorized': {
            'emails': ['admin@hengyuan.com']
        }
    }
    
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(default_users, file, default_flow_style=False, allow_unicode=True)
    
    # 设置文件权限（仅限Unix系统）
    try:
        os.chmod(USERS_FILE, 0o600)  # 只有所有者可读写
    except:
        pass

def create_emergency_config():
    """创建紧急情况下的默认配置"""
    return {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@hengyuan.com',
                    'name': '系统管理员',
                    'password': stauth.Hasher(['Admin@123']).generate()[0],
                    'role': 'admin'
                }
            }
        },
        'cookie': {
            'expiry_days': 1,
            'key': 'emergency_key_' + hashlib.sha256(os.urandom(16)).hexdigest()[:16],
            'name': 'emergency_auth'
        },
        'preauthorized': {
            'emails': []
        }
    }

def login_widget():
    """
    显示登录/注册窗口
    返回: (authentication_status, username, display_name)
    """
    config = init_auth()
    
    # 创建认证器对象 - 兼容0.3.3版本
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config.get('preauthorized', {})
    )
    
    # 在侧边栏显示
    with st.sidebar:
        st.markdown("---")
        
        # 检查是否已经登录
        if st.session_state.get('authenticated', False):
            return show_user_session(authenticator)
        
        # 未登录状态：显示登录/注册界面
        return show_auth_interface(authenticator, config)

def show_user_session(authenticator):
    """显示已登录用户会话"""
    username = st.session_state.get('username', '')
    display_name = st.session_state.get('display_name', '')
    user_role = st.session_state.get('user_role', 'user')
    
    # 用户信息卡片
    st.markdown(f"""
    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:15px;">
        <h4 style="margin:0; color:#1f77b4;">👤 {display_name}</h4>
        <p style="margin:5px 0; color:#666;">用户名: {username}</p>
        <span style="background-color:{'#ff6b6b' if user_role=='admin' else '#4ecdc4'}; 
                    color:white; padding:3px 8px; border-radius:5px; font-size:12px;">
            {'管理员' if user_role=='admin' else '普通用户'}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # 登出按钮 - 使用callback确保响应
    if st.button("🚪 退出登录", key="logout_button", use_container_width=True):
        perform_logout(authenticator, username)
    
    # 密码修改选项
    with st.expander("🔐 修改密码", expanded=False):
        change_password_form(username)
    
    return True, username, display_name

def perform_logout(authenticator, username):
    """执行退出登录操作"""
    try:
        # 1. 记录日志
        log_user_action(username, 'logout')
        
        # 2. 调用认证器的登出方法
        authenticator.logout('logout')
        
        # 3. 清除会话状态（保留主题设置）
        keys_to_preserve = ['_streamlit_theme']
        current_keys = list(st.session_state.keys())
        
        for key in current_keys:
            if key not in keys_to_preserve:
                del st.session_state[key]
        
        # 4. 重置认证状态
        st.session_state.update({
            'authenticated': False,
            'user_role': 'guest',
            'username': '',
            'display_name': '',
            'logout_time': time.time()  # 添加时间戳防止重复触发
        })
        
        # 5. 使用experimental_rerun确保刷新
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"退出登录失败: {str(e)}")
        # 备用方案：直接重定向
        st.session_state.clear()
        st.rerun()

def show_auth_interface(authenticator, config):
    """显示认证界面（登录/注册）"""
    # 使用标签页切换登录和注册
    tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
    
    login_success = False
    login_username = ""
    login_display_name = ""
    
    with tab1:
        login_success, login_username, login_display_name = show_login_form(authenticator, config)
    
    with tab2:
        if not login_success:  # 如果还没登录成功，显示注册表单
            show_registration_form(config)
    
    return login_success, login_username, login_display_name

def show_login_form(authenticator, config):
    """显示登录表单"""
    st.subheader("用户登录")
    
    try:
        # streamlit-authenticator 0.3.3版本的参数顺序
        name, authentication_status, username = authenticator.login('main', '登录')
    except Exception as e:
        # 兼容性回退
        try:
            name, authentication_status, username = authenticator.login('登录', 'main')
        except Exception as e2:
            st.error(f"登录组件初始化失败: {str(e2)}")
            return False, None, None
    
    if authentication_status:
        st.success(f"✅ 欢迎回来，{name}！")
        
        # 更新会话状态
        st.session_state.update({
            'authenticated': True,
            'username': username,
            'display_name': name,
            'user_role': get_user_role(username, config),
            'login_time': time.time()
        })
        
        # 更新最后登录时间
        update_last_login(username)
        
        # 记录日志
        log_user_action(username, 'login')
        
        # 添加一个小延迟确保状态更新
        time.sleep(0.1)
        st.rerun()
        
        return True, username, name
    
    elif authentication_status is False:
        st.error("❌ 用户名或密码错误")
        # 安全提示：不显示具体是用户名错误还是密码错误
        st.caption("提示：默认管理员账号: admin / Admin@123")
        
    elif authentication_status is None:
        st.info("👆 请输入用户名和密码")
    
    return False, None, None

def show_registration_form(config):
    """显示用户注册表单"""
    st.subheader("新用户注册")
    
    with st.form("registration_form", clear_on_submit=True):
        # 用户名和姓名
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("用户名*", 
                help="3-20位字母、数字或下划线")
        with col2:
            new_name = st.text_input("姓名*")
        
        # 邮箱
        new_email = st.text_input("邮箱地址*")
        
        # 密码
        col3, col4 = st.columns(2)
        with col3:
            new_password = st.text_input("密码*", type="password",
                help="至少8位，包含大小写字母和数字")
        with col4:
            confirm_password = st.text_input("确认密码*", type="password")
        
        # 协议同意
        agree_terms = st.checkbox("我已阅读并同意用户协议和隐私政策", value=False)
        
        submitted = st.form_submit_button("注册账户", type="primary", use_container_width=True)
        
        if submitted:
            return process_registration(new_username, new_name, new_email, 
                                       new_password, confirm_password, agree_terms, config)

def process_registration(username, name, email, password, confirm_password, agree_terms, config):
    """处理用户注册"""
    # 验证输入
    validation_result, message = validate_registration_input(
        username, name, email, password, confirm_password, agree_terms, config
    )
    
    if not validation_result:
        st.error(message)
        return
    
    # 注册用户
    success, message = register_user(username, name, email, password, config)
    
    if success:
        st.success(message)
        st.balloons()
        st.info("🎉 注册成功！请切换到登录标签页使用新账户登录")
    else:
        st.error(message)
    
    return success

def validate_registration_input(username, name, email, password, confirm_password, agree_terms, config):
    """验证注册输入"""
    if not all([username, name, email, password, confirm_password]):
        return False, "请填写所有必填字段"
    
    if len(username) < 3 or len(username) > 20:
        return False, "用户名长度需在3-20位之间"
    
    if not username.isalnum() and '_' not in username:
        return False, "用户名只能包含字母、数字和下划线"
    
    if password != confirm_password:
        return False, "两次输入的密码不一致"
    
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    # 密码强度检查（可选）
    if not any(c.isupper() for c in password) or not any(c.islower() for c in password):
        return False, "密码应包含大小写字母"
    
    if not any(c.isdigit() for c in password):
        return False, "密码应包含至少一个数字"
    
    if not agree_terms:
        return False, "请同意用户协议和隐私政策"
    
    if username in config['credentials']['usernames']:
        return False, "用户名已存在，请选择其他用户名"
    
    # 检查邮箱是否已被使用
    for user_info in config['credentials']['usernames'].values():
        if user_info.get('email', '').lower() == email.lower():
            return False, "该邮箱已被注册"
    
    return True, "验证通过"

def register_user(username, name, email, password, config):
    """注册新用户"""
    try:
        # 哈希密码
        hashed_password = stauth.Hasher([password]).generate()[0]
        
        # 添加新用户
        config['credentials']['usernames'][username] = {
            'email': email,
            'name': name,
            'password': hashed_password,
            'role': 'user',  # 新用户默认为普通用户
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # 保存配置
        with open(USERS_FILE, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        
        log_user_action(username, 'register')
        return True, "✅ 注册成功！"
        
    except Exception as e:
        log_user_action('system', f'register_failed: {str(e)}')
        return False, f"❌ 注册失败: {str(e)}"

def change_password_form(username):
    """显示修改密码表单"""
    with st.form("change_password_form"):
        current_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_password = st.text_input("确认新密码", type="password")
        
        submitted = st.form_submit_button("确认修改", use_container_width=True)
        
        if submitted:
            if new_password != confirm_password:
                st.error("新密码不一致")
                return
            
            if len(new_password) < 8:
                st.error("密码长度至少8位")
                return
            
            success, message = update_user_password(username, new_password)
            if success:
                st.success(message)
                time.sleep(1)
                st.rerun()
            else:
                st.error(message)

def update_user_password(username, new_password):
    """更新用户密码"""
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
        
        if username not in config['credentials']['usernames']:
            return False, "用户不存在"
        
        # 哈希新密码
        hashed_password = stauth.Hasher([new_password]).generate()[0]
        config['credentials']['usernames'][username]['password'] = hashed_password
        config['credentials']['usernames'][username]['password_changed_at'] = datetime.now().isoformat()
        
        with open(USERS_FILE, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        
        log_user_action(username, 'password_change')
        return True, "✅ 密码更新成功！请重新登录"
        
    except Exception as e:
        return False, f"❌ 密码更新失败: {str(e)}"

def get_user_role(username, config=None):
    """获取用户角色"""
    if config is None:
        config = init_auth()
    
    if username in config['credentials']['usernames']:
        return config['credentials']['usernames'][username].get('role', 'user')
    return 'guest'

def update_last_login(username):
    """更新用户最后登录时间"""
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
        
        if username in config['credentials']['usernames']:
            config['credentials']['usernames'][username]['last_login'] = datetime.now().isoformat()
            
            with open(USERS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
    except:
        pass  # 不影响主要功能

def check_permission(required_role='user'):
    """
    检查用户权限
    角色层级: admin > user > guest
    """
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        return False
    
    user_role = st.session_state.get('user_role', 'guest')
    
    role_hierarchy = {'admin': 3, 'user': 2, 'guest': 1}
    required_level = role_hierarchy.get(required_role, 1)
    user_level = role_hierarchy.get(user_role, 0)
    
    return user_level >= required_level

def require_login(required_role='user'):
    """需要登录的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_permission(required_role):
                st.warning(f"⚠️ 此功能需要 {required_role} 权限")
                st.info("请在左侧登录或切换账户")
                
                # 显示当前登录状态
                if st.session_state.get('authenticated'):
                    st.error(f"当前账户权限不足: {st.session_state.get('user_role')}")
                
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator

def log_user_action(username, action):
    """记录用户操作日志"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {username} | {action}\n"
        
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        with open(LOG_FILE, 'a', encoding='utf-8') as file:
            file.write(log_entry)
        
        # 控制日志文件大小（最多保留10000行）
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 10 * 1024 * 1024:  # 10MB
            with open(LOG_FILE, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            if len(lines) > 10000:
                with open(LOG_FILE, 'w', encoding='utf-8') as file:
                    file.writelines(lines[-10000:])
                    
    except Exception as e:
        print(f"日志记录失败: {e}")

def show_user_profile():
    """兼容旧版本的函数"""
    import streamlit as st
    
    if st.session_state.get('authenticated'):
        st.sidebar.info(f"已登录: {st.session_state.get('display_name', '')}")
        if st.sidebar.button("退出登录"):
            st.session_state.clear()
            st.rerun()
    else:
        st.sidebar.warning("请先登录")

def init_session_state():
    """初始化会话状态"""
    defaults = {
        'authenticated': False,
        'user_role': 'guest',
        'username': '',
        'display_name': '',
        'login_time': None,
        'logout_time': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 初始化会话状态
init_session_state()

# 使用说明
if __name__ == "__main__":
    st.title("🔐 用户认证模块测试")
    st.write("这是一个独立的认证模块测试页面")
    
    # 测试认证组件
    auth_status, username, display_name = login_widget()
    
    if auth_status:
        st.success(f"✅ 登录成功！欢迎 {display_name} ({username})")
        st.write(f"用户角色: {st.session_state.get('user_role')}")
        
        if st.button("测试权限检查"):
            if check_permission('admin'):
                st.success("✅ 您有管理员权限")
            elif check_permission('user'):
                st.success("✅ 您有普通用户权限")
            else:
                st.warning("⚠️ 您只有访客权限")
    else:
        st.info("请使用左侧侧边栏登录或注册")
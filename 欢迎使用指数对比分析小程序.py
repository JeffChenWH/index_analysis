import streamlit as st

st.set_page_config(
    page_title="欢迎使用指数对比分析小程序",
    page_icon="👋",
)

# ————————————————————————————————————————————提示信息————————————————————————————————————————————

# 使用CSS自定义布局
st.markdown(
    """
    <style>
    .custom-container {
        display: flex;
        align-items: center;  /* 垂直居中 */
        justify-content: space-between; /* 左右分布 */
        gap: 20px; /* 元素间距 */
    }
    .text-box {
        flex: 1;
    }
    .image-box {
        flex-shrink: 0; /* 图片不压缩 */
    }
    h1.custom-title {
        margin: 0; /* 移除默认外边距 */
        line-height: 1.2; /* 标题行高 */
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# 构建布局
st.markdown(
    """
    <div class="custom-container">
        <div class="text-box">
             <h1 class="custom-title">多指数对比工具</h1>
        </div>
        <div class="image-box">
            <img align=\"right\" src=\"https://bbs-pic.datacourse.cn/forum/201611/22/235658pvw0qyqbfwvjzo7v.png\" width=\"350\" height=\"80\">
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.write(
    """本工具实现选择指数进行对比分析的功能，具体而言，包括指数基本信息表格展示、历史收益率分析、指数成分股对比等功能，数据来源于万德接口"""
)

# 使用HTML和CSS将作者信息固定在底部
st.sidebar.markdown(
    """
    <style>
    .sidebar-container {
        display: flex;
        flex-direction: column;
        min-height: 70vh; /* 确保容器至少占满整个视口高度 */
    }
    .sidebar-content {
        flex: 1; /* 这部分会占据所有可用空间，将footer推到底部 */
    }
    .sidebar-footer {
        padding: 1rem;
        border-top: 1px solid #ddd;
        margin-top: auto; /* 与 flex: 1 配合，实现推至底部 */
    }
    </style>
    <div class="sidebar-container">
        <div class="sidebar-content">
            <!-- 你的侧边栏主内容在这里 -->
        </div>
        <div class="sidebar-footer">
            由 <strong>Jeff_Chen</strong> 开发</br>
            联系邮箱：<a href="mailto:Jeff_ChenWH@Outlook.com">Jeff_ChenWH@Outlook.com</a></br>
            应用程序版本下载：<a href="https://github.com/Jeff-ChenWH/index_analysis/releases/tag/v1.0.0">v1.0.0</a></br>
            Github仓库：<a href="https://github.com/Jeff-ChenWH/index_analysis">https://github.com/Jeff-ChenWH/index_analysis</a></br>
             <strong>版本 1.0.0</strong>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ————————————————————————————————————————————WindPy连接————————————————————————————————————————————

# from WindPy import w

# # 连接状态管理
# if 'wind_initialized' not in st.session_state:
#     st.session_state.wind_initialized = False
#     st.session_state.wind_connected = False

# # 初始化Wind（仅在首次运行时执行）
# if not st.session_state.wind_initialized:
#     with st.spinner("初始化Wind连接..."):
#         try:
#             # 尝试连接Wind
#             w.start(waitTime=600)
#             st.session_state.wind_initialized = True
            
#             # 验证连接
#             if w.isconnected():
#                 st.session_state.wind_connected = True
#                 st.success("✅ Wind连接成功")
#             else:
#                 st.warning("⚠️ 连接失败，请重试")
#         except Exception as e:
#             st.error(f"初始化错误: {str(e)}")
#             st.session_state.wind_initialized = True

# # 主应用界面
# # st.title("Wind数据终端")

# # 显示连接状态
# if st.session_state.wind_connected:
#     st.success("✅ Wind连接正常")
# else:
#     st.warning("⚠️ 未连接Wind")

# import streamlit as st
# from WindPy import w
# import time

# # 检查是否为初始化进程
# is_init_process = st.secrets.get("is_init", False) or st.query_params.get("init", "false").lower() == "true"

# 初始化Wind（仅在初始化进程中执行）
# if is_init_process:
# st.set_page_config(layout="wide", page_title="Wind初始化")
# st.subheader("Wind初始化中...")

# with st.spinner("正在连接Wind终端，请勿关闭此窗口..."):
#     try:
#         # 尝试连接Wind
#         w.start(waitTime=600)
        
#         # 验证连接
#         if w.isconnected():
#             st.success("✅ Wind连接成功！")
#             # st.write("此窗口将在10秒后自动关闭")
#             # time.sleep(10)
#             # st.stop()
#         else:
#             st.error("⚠️ Wind连接失败，请检查终端是否已启动")
#     except Exception as e:
#         st.error(f"连接错误: {str(e)}")

# # 保持窗口打开
# st.stop()
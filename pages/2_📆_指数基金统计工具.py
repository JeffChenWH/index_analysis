from calendar import c
import datetime
import re
import numpy as np
from WindPy import w
from math import log

import streamlit as st
import pandas as pd
import altair as alt
from urllib.error import URLError
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import statsmodels.api as sm

st.set_page_config(page_title="指数基金统计工具", page_icon="📆", layout="wide")

# ————————————————————————————————————————————初始配置模块————————————————————————————————————————————
# 全局时间配置：定义默认日期范围，默认起止日期为五年前和今天
FIVE_YEARS_AGO = (datetime.datetime.now() - datetime.timedelta(days=5*365)).date().strftime('%Y-%m-%d')
TODAY = datetime.datetime.now().date().strftime('%Y-%m-%d')

# ————————————————————————————————————————————数据缓存模块————————————————————————————————————————————

# 缓存指数跟踪基金数据
@st.cache_data
def get_tracking_funds(indexes):
    """获取跟踪指数的所有基金信息"""
    tracking_funds_data = {}
    for index in indexes:
        tracking_funds_data[index] = w.wset("indexrelevancefund",f"date={st.session_state.end_date};windcode={index}",usedf=True)[1]
        tracking_funds_data[index].rename(columns={
            'fundcode':'基金代码',
            'fundname':'基金名称',
            'scale':'基金规模（亿元）',
            'excessreturn':'过去一年超额收益（%）',
            'establishmentday':'基金成立日',
            'fundmanager':'基金经理',
            'company':'基金公司',
            'unitnav':'单位净值',
            'managementrate':'管理费',
            'windavg':'Wind三年评级',
            'fundtype':'基金类型'}, inplace=True)

        # 健壮性检查：如果该指数没有对应的基金数据，跳过后续处理
        if tracking_funds_data[index] is not None and not tracking_funds_data[index].empty:
            tracking_funds_data[index].set_index('基金代码', inplace=True)
            # 检查基金规模数据的存在性和格式转换
            if '基金规模（亿元）' in tracking_funds_data[index].columns:
                tracking_funds_data[index]['基金规模（亿元）'] = tracking_funds_data[index]['基金规模（亿元）'].apply(lambda x: x/100000000 if pd.notnull(x) else 0.0)
        else:
            # 如果没有基金数据，设置为None
            tracking_funds_data[index] = None

        # TODO: 获取近三个月基金走势信息并嵌入文件中
    return tracking_funds_data

# TODO：为show_corr_scatter函数提供数据接口，从万德获取数据
@st.cache_data
def get_tracking_error(fund_codes, start_date, end_date):
    """获取基金的跟踪误差、股息率、超额收益和份额波动率数据"""
    if not fund_codes:
        return pd.DataFrame()
    
    try:
        # 获取基金跟踪误差与规模数据
        tracking_error_data = w.wss(fund_codes, "fund_info_name,risk_trackerror_trackindex,risk_navoverbenchannualreturn,netasset_total_cc",
                                  f"startDate={start_date};endDate={end_date};period=1;returnType=1;unit=1",
                                  f"tradeDate={end_date};currencyType=Cur=CNY", 
                                  usedf=True)[1]
                                  
        # 删掉没有数据的基金代码，避免重复计算
        fund_codes_available = tracking_error_data.dropna().index.tolist()

        # 计算基金份额波动率：对每个基金获取日频份额数据，然后计算波动率
        volatility_data = {}
        for fund_code in fund_codes_available:
            try:
                # 获取基金份额日频数据（根据指定的日期范围）
                share_data = w.wsd(fund_code, "unit_fundshare_total", start_date, end_date, usedf=True)[1]
                
                if not share_data.empty and len(share_data) > 1:
                    # 计算日收益率
                    daily_returns = share_data.pct_change().dropna()
                    # 计算年化波动率（假设252个交易日）
                    annualized_volatility = daily_returns.std() * np.sqrt(252) * 100
                    volatility_data[fund_code] = annualized_volatility.iloc[0] if not annualized_volatility.empty else np.nan
                else:
                    volatility_data[fund_code] = np.nan
            except Exception as e:
                volatility_data[fund_code] = np.nan
        
        # 将波动率数据转换为DataFrame
        volatility_df = pd.DataFrame(list(volatility_data.items()), columns=['基金代码', '份额波动率(%)'])
        volatility_df.set_index('基金代码', inplace=True)
        
        # 合并数据
        result_data = pd.concat([tracking_error_data, volatility_df], axis=1)
        result_data.columns = ['基金名称', '跟踪误差(%)', '超额收益(%)', '基金规模（亿元）', '份额波动率(%)']
        
        # 清理数据，移除空值，对数化规模避免图像绘制差别过大
        result_data = result_data.dropna()
        result_data = result_data[~result_data.index.str.endswith('HK')] # 去掉香港指数
        result_data['基金规模（对数）'] = result_data['基金规模（亿元）'].map(lambda x: np.log(x+1))
        result_data['基金规模（亿元）'] = result_data['基金规模（亿元）'].map(lambda x: x/100000000)

        # 对基金类型进行分类
        result_data['基金类型'] = result_data['基金名称'].map(lambda x: 'ETF联接' if '联接' in x else 'ETF' if 'ETF' in x else '场外基金')

        return result_data
    except Exception as e:
        st.error(f"获取基金数据时出错: {str(e)}")
        return pd.DataFrame()

# ————————————————————————————————————————————提示信息————————————————————————————————————————————

# 使用CSS自定义布局实现图表垂直居中
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

st.divider()

# ————————————————————————————————————————————辅助函数模块————————————————————————————————————————————

# TODO:三倍标准差去极值函数
def MAD(data, threshold=3):
    """
    计算数据的MAD（中位数绝对偏差），并返回超过阈值的异常值索引。
    
    参数:
    data (pd.Series或np.array): 输入数据
    threshold (float): 异常值判断阈值，默认3倍MAD
    
    返回:
    pd.Index: 异常值索引
    """
    median = np.median(data)
    mad = np.median(np.abs(data - median))
    lower_bound = median - threshold * mad
    upper_bound = median + threshold * mad
    return data[(data < lower_bound) | (data > upper_bound)].index

# TODO:对数据进行回归分析
def regress(data, x_col, y_col):
    """
    对数据进行简单线性回归分析。
    
    参数:
    data (pd.DataFrame): 输入数据，包含x_col和y_col列
    x_col (str): 自变量列名
    y_col (str): 因变量列名
    
    返回:
    tuple: 包含回归系数(params)、R²值(rsquared)、p值(pvalues)
    """
    X = sm.add_constant(data[x_col])
    model = sm.OLS(data[y_col], X).fit()
    return model.params, model.rsquared, model.pvalues

# 变量选择表单函数
def create_variable_selection_form(fund_data, form_key, title_prefix=""):
    """
    创建变量选择表单的可重用函数
    
    参数:
    fund_data (pd.DataFrame): 基金数据
    form_key (str): 表单的唯一标识符
    title_prefix (str): 图表标题前缀
    
    返回:
    tuple: (x_var, y_var) 选中的变量，如果未选择或选择不完整则返回(None, None)
    """
    # 变量选择表单 - 先选择变量再提交
    with st.form(key=form_key):
        # 获取可用的变量列
        available_columns = [col for col in fund_data.columns if col not in ['基金名称', '基金类型', '基金规模（亿元）', '基金规模（对数）']]
        
        # 变量选择组件
        selected_vars = st.multiselect(
            "选择变量（最多选择两个）",
            options=available_columns,
            max_selections=2,
            placeholder="请选择两个变量进行对比"
        )
        
        # 提交按钮
        submit_button = st.form_submit_button("生成散点图")
        
        # 处理表单提交
        if submit_button:
            if len(selected_vars) == 2:
                x_var, y_var = selected_vars
                # 显示散点图
                show_corr_scatter(fund_data, x_var, y_var, f"{title_prefix}变量散点图")
                return x_var, y_var
            elif len(selected_vars) == 1:
                st.warning("请选择两个变量进行对比分析")
            else:
                st.info("请选择两个变量来生成散点图")
    
    # 如果没有选择变量，显示提示信息
    if not selected_vars:
        st.info("请在表单中选择两个变量来生成散点图")
    
    return None, None

# ————————————————————————————————————————————绘图函数模块————————————————————————————————————————————

# 显示跟踪各指数的基金竞争格局
def show_tracking_funds(indexes):
    """显示跟踪各指数的基金竞争格局"""
    # 获取跟踪各指数的基金数据
    tracking_funds_data = get_tracking_funds(indexes)
    
    # 获取指数名称
    index_info = get_information_data(indexes)
    
    # 创建标签页
    tabs = st.tabs([name for name in index_info['指数名称']])
    
    # 用于存储原始数据的字典
    data_dict = {}
    
    for i, (index_code, name) in enumerate(zip(index_info.index, index_info['指数名称'])):
        with tabs[i]:
            # 获取当前指数的基金数据，检查是否存在有效数据
            if tracking_funds_data[index_code] is None or tracking_funds_data[index_code].empty:
                st.info(f"{name}({index_code})没有对应的基金产品")
                continue
                
            fund_df = tracking_funds_data[index_code].copy()
            
            # 使用正则表达式筛选基金代码，只保留以OF、SZ、SH、HK结尾的基金
            fund_df = fund_df[fund_df.index.astype(str).str.match(r'.*\.(OF|SZ|SH|HK)$')]
            
            # 只显示前50大基金
            fund_df_top50 = fund_df.head(50)
            
            # 显示处理后的数据
            st.dataframe(fund_df_top50.style.background_gradient(
                        cmap='Oranges', 
                        subset=['基金规模（亿元）', '过去一年超额收益（%）','单位净值', '管理费', 'Wind三年评级']
                            ).format({
                                '基金规模（亿元）': "{:.2f}",
                                '过去一年超额收益（%）': "{:.2f}",
                                '单位净值': "{:.4f}",
                                '管理费': "{:.2f}",
                                'Wind三年评级': "{:.0f}"
                            }),
                use_container_width=True)
            
            # 将原始数据储存在字典里备用
            data_dict[index_code] = fund_df
    
    # 显示详细的原始数据，默认隐藏
    st.divider()
    st.subheader("基金原始数据")
    
    if len(index_info) > 8:
        st.error("最多只能选择8个指数进行对比")
    else:
        # 默认隐藏原始数据
        with st.expander("点击查看原始数据"):
            tabs = st.tabs([name for name in index_info['指数名称']])
            for i, (index_code, name) in enumerate(zip(index_info.index, index_info['指数名称'])):
                with tabs[i]:
                    if tracking_funds_data[index_code] is None or tracking_funds_data[index_code].empty:
                        st.info(f"{name}({index_code})没有对应的基金产品")
                        continue
                    else:
                        st.dataframe(data_dict[index_code], use_container_width=True)

# TODO: 该函数实现绘制不同基金产品跟踪误差和份额波动率的散点图，并且由用户点击散点点可以查看具体基金产品的信息，用plotly实现；除此之外，还需要在图像下方打印原始数据
# 1.如果用户输入的是指数代码，那么就获取跟踪该指数的所有基金产品，并获取份额波动率和跟踪误差绘制图像
# 2.如果用户上传了一个包含基金代码的文件，那么就获取该文件中的所有基金产品，并获取份额波动率和跟踪误差绘制图像，这种情况下，不同的基金类型应该有不同的颜色
def show_corr_scatter(fund_data, x_var, y_var, chart_title="基金变量散点图"):
    """显示基金变量散点图"""
    if fund_data.empty:
        st.info("没有可用的基金数据用于绘制散点图")
        return
    
    # 对原始数据做MAD取极值处理，剔除超过5倍标准差的基金
    x_outliers = MAD(fund_data[x_var], threshold=5)
    y_outliers = MAD(fund_data[y_var], threshold=5)
    
    # 合并异常值索引并移除异常值
    outliers = x_outliers.union(y_outliers)
    if not outliers.empty:
        st.info(f"检测到 {len(outliers)} 个异常值，已从分析中移除")
        fund_data_cleaned = fund_data.drop(outliers)
    else:
        fund_data_cleaned = fund_data
    
    # 对清理后的数据进行回归分析
    try:
        params, rsquared, pvalues = regress(fund_data_cleaned, x_var, y_var)
        intercept = params['const']
        slope = params[x_var]
        
        # 创建回归直线数据
        x_min = fund_data_cleaned[x_var].min()
        x_max = fund_data_cleaned[x_var].max()
        x_line = np.linspace(x_min, x_max, 100)
        y_line = intercept + slope * x_line
        
        # 创建交互式散点图
        fig = go.Figure()
        
        # 定义基金类型的颜色映射
        color_map = {
            'ETF': '#1f77b4',      # 蓝色
            'ETF联接': '#ff7f0e',   # 橙色
            '场外基金': '#d2b48c'   # 金色
        }
        
        # 为每种基金类型创建独立的散点图trace，实现图例交互功能
        for fund_type, color in color_map.items():
            # 筛选当前基金类型的数据
            fund_type_data = fund_data_cleaned[fund_data_cleaned['基金类型'] == fund_type]
            
            if not fund_type_data.empty:
                fig.add_trace(go.Scatter(
                    x=fund_type_data[x_var],
                    y=fund_type_data[y_var],
                    mode='markers',
                    marker=dict(
                        size=fund_type_data['基金规模（对数）'], # 对数处理，避免规模悬殊导致的点过密
                        color=color,
                        sizemode='diameter',
                        sizeref=2. * max(fund_data_cleaned['基金规模（对数）'])/50, # 调整分母为20^2，使散点大小更合理
                        sizemin=4
                    ),
                    text=fund_type_data['基金名称'],  # 基金名称作为悬停文本
                    customdata=fund_type_data['基金规模（亿元）'],
                    hovertemplate=
                        "<b>%{text}</b><br>" +
                        f"{x_var}: %{{x:.2f}}%<br>" +
                        f"{y_var}: %{{y:.2f}}%<br>" +
                        "基金规模: %{customdata:.2f}亿元<br>" +
                        f"基金类型: {fund_type}<br>" +
                        "<extra></extra>",
                    name=fund_type,
                    legendgroup=fund_type,
                    showlegend=True
                ))
        
        # 添加回归直线
        fig.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode='lines',
            line=dict(color='red', width=2),
            name='回归直线'
        ))
        
        # 在右上角添加R²值和p值注释
        fig.add_annotation(
            x=1,
            y=1,
            xref='paper',
            yref='paper',
            text=f'R² = {rsquared:.4f}<br>p = {pvalues[x_var]:.4f}',
            showarrow=False,
            bgcolor='white',
            bordercolor='black',
            borderwidth=1,
            font=dict(size=12),
            align='left'
        )
        
        # 图例已经通过独立的散点图trace自动创建，无需额外添加
        
        # 设置图表布局
        fig.update_layout(
            title=f"{x_var} vs {y_var} 散点图",
            xaxis_title=x_var,
            yaxis_title=y_var,
            hovermode='closest',
            height=600,
            legend_title_text='基金类型'
        )
        
        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示回归分析结果
        st.subheader("回归分析结果")
        regression_results = pd.DataFrame({
            '参数': ['截距', '斜率', 'R²', 'p值'],
            '值': [intercept, slope, rsquared, pvalues[x_var]]
        })
        st.dataframe(regression_results.style.format({
            '值': "{:.6f}"
        }), use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.warning(f"回归分析失败: {str(e)}")
        # 如果回归分析失败，仍然显示散点图
        # 创建交互式散点图
        fig = go.Figure()
        
        # 定义基金类型的颜色映射
        color_map = {
            'ETF': '#1f77b4',      # 蓝色
            'ETF联接': '#ff7f0e',   # 橙色
            '场外基金': '#d2b48c'   # 金色
        }
        
        # 为每种基金类型创建独立的散点图trace，实现图例交互功能
        for fund_type, color in color_map.items():
            # 筛选当前基金类型的数据
            fund_type_data = fund_data_cleaned[fund_data_cleaned['基金类型'] == fund_type]
            
            if not fund_type_data.empty:
                fig.add_trace(go.Scatter(
                    x=fund_type_data[x_var],
                    y=fund_type_data[y_var],
                    mode='markers',
                    marker=dict(
                        size=fund_type_data['基金规模（对数）'], # 使用已经计算好的对数规模
                        color=color,
                        sizemode='diameter',
                        sizeref=2. * max(fund_data_cleaned['基金规模（对数）'])/(20**2), # 调整分母为20^2，使散点大小更合理
                        sizemin=4
                    ),
                    text=fund_type_data['基金名称'],  # 基金名称作为悬停文本
                    customdata=fund_type_data['基金规模（亿元）'],
                    hovertemplate=
                        "<b>%{text}</b><br>" +
                        f"{x_var}: %{{x:.2f}}%<br>" +
                        f"{y_var}: %{{y:.2f}}%<br>" +
                        "基金规模: %{customdata:.2f}亿元<br>" +
                        f"基金类型: {fund_type}<br>" +
                        "<extra></extra>",
                    name=fund_type,
                    legendgroup=fund_type,
                    showlegend=True
                ))
        
        # 图例已经通过独立的散点图trace自动创建，无需额外添加
        
        # 设置图表布局
        fig.update_layout(
            title=f"{x_var} vs {y_var} 散点图",
            xaxis_title=x_var,
            yaxis_title=y_var,
            hovermode='closest',
            height=600,
            legend_title_text='基金类型'
        )
        
        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
    
    # 显示原始数据
    st.subheader("基金跟踪误差与波动率原始数据")
    st.dataframe(fund_data_cleaned.style.format({
        '跟踪误差(%)': "{:.4f}",
        '波动率(%)': "{:.4f}",
        '基金规模（亿元）': "{:.2f}"
    }), use_container_width=True)

# ————————————————————————————————————————————主程序模块——————————————————————————————————————————————

def main(index_codes):
    try:
        # 在主程序头部执行一次万德终端启动
        w.start()

        # 检查是否有上传的文件
        uploaded_file = st.session_state.get('uploaded_file', None)
        
        # 只有在有指数代码时才显示指数相关分析
        if index_codes:

            # 在主程序中添加散点图功能
            # st.divider()
            st.subheader("基金跟踪误差与波动率分析")

            # 如果没有上传文件，使用当前选择的指数对应的基金
            # 获取当前选择指数的基金
            tracking_funds_data = get_tracking_funds(index_codes)
            
            # 收集所有基金代码
            all_fund_codes = []
            for index_code in index_codes:
                if tracking_funds_data[index_code] is not None and not tracking_funds_data[index_code].empty:
                    all_fund_codes.extend(tracking_funds_data[index_code].index.tolist())
            
            if all_fund_codes:
                # 获取基金数据
                fund_data = get_tracking_error(all_fund_codes, st.session_state.start_date, st.session_state.end_date)
                if not fund_data.empty:
                    # 使用封装的函数创建变量选择表单
                    create_variable_selection_form(fund_data, "variable_selection_form", "指数跟踪基金的")
                else:
                    st.warning("未能获取到有效的基金数据")
            else:
                st.info("当前选择的指数没有对应的基金产品")

        elif uploaded_file:
            # 处理上传的文件
            fund_codes = handle_ETF_file(uploaded_file)
            if fund_codes:
                # 获取基金数据
                fund_data = get_tracking_error(fund_codes, st.session_state.start_date, st.session_state.end_date)
                if not fund_data.empty:
                    # 使用封装的函数创建变量选择表单
                    create_variable_selection_form(fund_data, "variable_selection_form_uploaded", "上传文件中基金产品的")
                else:
                    st.warning("未能获取到有效的基金数据")

        # 页面运行完毕关闭万德终端
        w.stop()

    except URLError as e:
        st.error(
            """
            **请登录万德账号**
            Connection error: %s
        """
            % e.reason
        )

# ————————————————————————————————————————————侧边栏管理模块————————————————————————————————————————————

# 初始化session state
if 'index_codes' not in st.session_state:
    st.session_state.index_codes = []
if 'run_analysis' not in st.session_state:
    st.session_state.run_analysis = False
if 'input_error' not in st.session_state:
    st.session_state.input_error = None
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False

# 添加日期相关的session state
if 'start_date' not in st.session_state:
    # 开始日期默认为5年前
    st.session_state.start_date = FIVE_YEARS_AGO
if 'end_date' not in st.session_state:
    st.session_state.end_date = TODAY

# 指数代码合法性检查（用指数代码命名规则初筛）
def validate_index_codes(input_str):
    """验证输入的指数代码格式并返回标准化的代码列表"""
    if not input_str:
        return [], []
    
    # 分割输入字符串，支持中英文标点和空白字符
    raw_codes = [code.strip() for code in re.split(r'[,，;；\s\n]+', input_str) if code.strip()]
    
    validated_codes = []
    invalid_codes = []
    
    for code in raw_codes:
        # 检查基本格式：
        if re.match(r'^\d{6}$', code):
            validated_codes.append(f"{code}.SH")
        elif re.match(r'^[Hh]\d{5}$', code):
            # 支持以H开头的中证指数，如H30184
            validated_codes.append(f"{code.upper()}.CSI")
        elif re.match(r'^CN\d{4}$', code):
            # 支持以CN开头+4位数字的指数代码
            validated_codes.append(f"{code.upper()}.CNI")
        elif re.match(r'^\d{6}\.[A-Za-z]{2,3}$', code) or re.match(r'^[Hh]\d{5}\.[A-Za-z]{2,4}$', code) or re.match(r'^CN\d{4}\.[A-Za-z]{2,3}$', code):
            # 支持已有的格式以及新增的CN+4位数字+.WI或.CNI后缀
            validated_codes.append(code.upper())
        else:
            invalid_codes.append(code)
    
    return validated_codes, invalid_codes

# 指数代码合法性检查（用万德API二次复查）
def verify_index_codes_with_wind(codes):
    """使用万德接口验证指数代码的合法性"""
    if not codes:
        return [], []
    
    try:
        w.start()
        # 检查证券类型和指数类型
        error_code, df = w.wss(codes, "sec_type,windtype", usedf=True)
        
        if error_code != 0:
            st.error(f"万德接口调用失败：{error_code}")
            return [], codes
        
        valid_codes = []
        invalid_codes = []
        
        for code in codes:
            try:
                sec_type = df.loc[code, 'SEC_TYPE']
                wind_type = df.loc[code, 'WINDTYPE']
                
                # 验证是否是股票指数
                # 增加对None和空字符串的检查
                if (sec_type is not None and wind_type is not None and
                    isinstance(sec_type, str) and isinstance(wind_type, str) and
                    '指数' in sec_type and ('股票' in wind_type or 'A股' in wind_type)):
                    valid_codes.append(code)
                else:
                    invalid_codes.append(code)
            except (KeyError, AttributeError):
                invalid_codes.append(code)
                
        return valid_codes, invalid_codes
        
    except Exception as e:
        st.error(f"验证指数代码时发生错误: {str(e)}")
        return [], codes

# 处理表单提交的函数
def handle_form_submit():
    """处理表单提交"""
    st.session_state.input_error = None
    
    # 检查是否有上传的文件
    uploaded_file = st.session_state.get('fund_file_uploader', None)
    if uploaded_file is not None:
        # 保存上传的文件到session state
        st.session_state.uploaded_file = uploaded_file
        # 设置file_processed为True以触发主程序执行
        st.session_state.file_processed = True
        # 清空指数代码，因为我们使用上传的文件
        st.session_state.index_codes = []
        st.session_state.run_analysis = True
        return
    
    # 验证输入格式
    validated_codes, invalid_format = validate_index_codes(st.session_state.index_input)
    
    if invalid_format:
        st.session_state.input_error = f"以下代码格式无效 (应为6位数字+可选的交易所后缀): {', '.join(invalid_format)}"
        st.session_state.run_analysis = False
        return
    
    if not validated_codes:
        st.session_state.input_error = "请输入至少一个指数代码"
        st.session_state.run_analysis = False
        return
        
    # 验证指数有效性
    valid_codes, invalid_codes = verify_index_codes_with_wind(validated_codes)
    
    if invalid_codes:
        st.session_state.input_error = f"以下不是有效的股票指数代码: {', '.join(invalid_codes)}"
        st.session_state.run_analysis = False
        return
        
    if len(valid_codes) > 8:
        st.session_state.input_error = "最多只能同时分析8个指数"
        st.session_state.run_analysis = False
        return
        
    # 更新状态
    st.session_state.index_codes = valid_codes
    st.session_state.run_analysis = True

# TODO: 该函数实现用户上传一个文件，为包含基金代码的文件，文件中至少包括“证券代码”列和“基金类型”列
def handle_ETF_file(uploaded_file):
    """处理用户上传的基金文件"""
    try:
        # 读取上传的文件
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("不支持的文件格式，请上传CSV或Excel文件")
            return None
        
        # 检查必需的列
        required_columns = ['证券代码']
        if not all(col in df.columns for col in required_columns):
            st.error(f"文件中缺少必需的列: {', '.join(required_columns)}")
            return None
        
        # 返回基金代码列表
        fund_codes = df['证券代码'].tolist()
        
        return fund_codes
    except Exception as e:
        st.error(f"处理上传文件时出错: {str(e)}")
        return None, None



# 侧边栏UI
with st.sidebar:
    st.markdown("### 指数基金跟踪误差分析工具：")
    st.markdown("输入一个指数代码，可获取跟踪该指数的指数基金的跟踪误差和份额波动率；也可上传一个列名为“证券代码”，且包含指数基金代码的文件以供分析")
    
    with st.form(key="index_form"):
        # 添加文件上传组件
        st.markdown("#### 方式一：上传基金文件")
        st.file_uploader("上传包含基金代码的文件（可选）", type=['csv', 'xlsx', 'xls'], key="fund_file_uploader")
        
        st.markdown("#### 方式二：输入指数代码")
        st.text_area(
            "请输入要分析的指数代码（最多8个）",
            key="index_input",
            help="支持以下格式：\n"
                 "1. 纯数字6位（如：000300，将自动添加.SH后缀）\n"
                 "2. 以H开头的中证指数（如：H30184，将自动添加.CSI后缀）\n"
                 "3. 以CN开头+4位数字的国证指数（如：CN1098，将自动添加.CNI后缀）\n"
                 "4. 带后缀（如：000300.SH，399006.SZ，CN1098.WI，CN1098.CNI）\n"
                 "使用逗号、分号、空格或换行分隔多个代码",
            placeholder="例如：\n000300.SH\n399006.SZ\nH30184\nCN1098"
        )
        
        # 添加日期选择
        st.markdown("选择分析日期范围")
        st.session_state.start_date = st.date_input("起始日期", value='2025-01-01', min_value=datetime.date(2000, 1, 1)).strftime('%Y-%m-%d')
        st.session_state.end_date = st.date_input("结束日期", value=TODAY, max_value=datetime.date.today()).strftime('%Y-%m-%d')
        
        submit_button = st.form_submit_button(
            label="确定",
            on_click=handle_form_submit
        )

    # 显示错误信息
    if st.session_state.input_error:
        st.error(st.session_state.input_error)
    elif st.session_state.run_analysis:
        st.success(f"已选择 {len(st.session_state.index_codes)} 个指数")
        st.info(f"分析日期范围: {st.session_state.start_date} 至 {st.session_state.end_date}")
    w.stop()

# 主页面逻辑
if st.session_state.run_analysis or (st.session_state.uploaded_file and st.session_state.get('file_processed', False)):
    main(st.session_state.index_codes)
else:
    st.info("请在左侧侧边栏输入您要分析的指数代码或上传基金文件，并提交表单以开始分析。")
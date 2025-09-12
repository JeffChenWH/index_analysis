from calendar import c
import datetime
import re
import numpy as np
from WindPy import w

import streamlit as st
import pandas as pd
import altair as alt
from urllib.error import URLError
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="指数对比分析工具", page_icon="📊")

# ————————————————————————————————————————————初始配置模块————————————————————————————————————————————
# 全局时间配置：定义默认日期范围，默认起止日期为五年前和今天
FIVE_YEARS_AGO = (datetime.datetime.now() - datetime.timedelta(days=5*365)).date().strftime('%Y-%m-%d')
TODAY = datetime.datetime.now().date().strftime('%Y-%m-%d')

# 颜色配置：包括申万和中信一级行业的配色
# 申万一级行业配色方案
sw_industry_colors = {
    '农林牧渔': '#1f77b4',     # 深蓝
    '采掘': '#ff7f0e',         # 橙色
    '化工': '#2ca02c',         # 绿色
    '钢铁': '#d62728',         # 红色
    '有色金属': '#9467bd',     # 紫色
    '电子': '#8c564b',         # 棕色
    '家用电器': '#e377c2',     # 粉色
    '食品饮料': '#7f7f7f',     # 灰色
    '纺织服饰': '#bcbd22',     # 橄榄绿
    '轻工制造': '#17becf',     # 青色
    '医药生物': '#aec7e8',     # 浅蓝
    '公用事业': '#ffbb78',     # 浅橙
    '交通运输': '#98df8a',     # 浅绿
    '房地产': '#ff9896',       # 浅红
    '商业贸易': '#c5b0d5',     # 浅紫
    '社会服务': '#c49c94',     # 浅棕
    '综合': '#f7b6d2',         # 浅粉
    '建筑材料': '#c7c7c7',     # 浅灰
    '建筑装饰': '#dbdb8d',     # 卡其色
    '电力设备': '#17becf',     # 青色
    '机械设备': '#9467bd',     # 紫色
    '国防军工': '#bcbd22',     # 橄榄绿
    '计算机': '#2ca02c',       # 绿色
    '传媒': '#d62728',         # 红色
    '通信': '#ff7f0e',         # 橙色
    '汽车': '#1f77b4',         # 深蓝
    '非银金融': '#8c564b',     # 棕色
    '银行': '#e377c2',         # 粉色
    '美容护理': '#7f7f7f',     # 灰色
    '环保': '#ffbb78',         # 浅橙
    '煤炭': '#8dd3c7'          # 青绿色
}

# 中信一级行业配色方案
zx_industry_colors = {
    '机械': '#1f77b4',               # 深蓝
    '商贸': '#ff7f0e',               # 橙色
    '零售': '#2ca02c',               # 绿色
    '非银行金融': '#d62728',         # 红色
    '综合': '#9467bd',               # 紫色
    '银行': '#8c564b',               # 棕色
    '汽车': '#e377c2',               # 粉色
    '石油石化': '#7f7f7f',           # 灰色
    '煤炭': '#8dd3c7',                # 青绿色
    '电力及公用事业': '#bcbd22',       # 橄榄绿
    '房地产': '#17becf',             # 青色
    '钢铁': '#aec7e8',               # 浅蓝
    '通信': '#ffbb78',               # 浅橙
    '轻工制造': '#98df8a',           # 浅绿
    '交通运输': '#ff9896',           # 浅红
    '建筑': '#c5b0d5',               # 浅紫
    '建材': '#c49c94',               # 浅棕
    '基础化工': '#f7b6d2',           # 浅粉
    '医药': '#c7c7c7',               # 浅灰
    '纺织服装': '#dbdb8d',           # 卡其色
    '电力设备及新能源': '#17becf',   # 青色
    '食品饮料': '#9467bd',           # 紫色
    '农林牧渔': '#bcbd22',           # 橄榄绿
    '有色金属': '#2ca02c',           # 绿色
    '综合金融': '#d62728',           # 红色
    '家电': '#ff7f0e',               # 橙色
    '电子': '#8c564b',               # 棕色
    '消费者服务': '#e377c2',         # 粉色
    '国防军工': '#7f7f7f',           # 灰色
    '传媒': '#ffbb78',               # 浅橙
    '计算机': '#98df8a'              # 浅绿
}

# ————————————————————————————————————————————数据缓存模块————————————————————————————————————————————

# 缓存指数价格数据
@st.cache_data
def get_index_data(indexes):
    index_data = w.wsd(indexes, "close", f"{st.session_state.start_date}", f"{st.session_state.end_date}",usedf=True)[1]
    return index_data

# 缓存区间收益数据
@st.cache_data
def get_return_data(indexes):
    return_data = pd.DataFrame()
    curr_year = int(st.session_state.end_date[:4])
    years = sorted([curr_year - i for i in range(1,5)])
    for year in years:
        return_data[str(year)] = w.wss(indexes, "pct_chg_per",
        f"startDate={year}0101;endDate={year}1231",
        usedf=True)[1]
    return_data[f'{curr_year}年至今'] = w.wss(indexes, "pct_chg_per",
        f"startDate={curr_year}0101;endDate={st.session_state.end_date}",
        usedf=True)[1]
    return return_data.round(2)

# 缓存大类资产价格数据
@st.cache_data
def get_assets_data():
    assets = ['CBA08301.CS','AU9999.SGE','DCESMFI.DCE','IMCI.SHF','000201.CZC','H11014.CSI']
    assets_data = w.wsd(assets, "close", f"{st.session_state.start_date}", f"{st.session_state.end_date}", usedf=True)[1]
    return assets_data

# 缓存指数成分股数据
@st.cache_data
def get_index_component_data(_indexes):
    index_component_data = pd.DataFrame()

    # 获取指数成分股代码、名称与权重
    for index in _indexes:
        # 获取权重
        df = w.wset("indexconstituent",
                f"windcode={index};",
                "field=wind_code,sec_name,i_weight,industry",
                usedf=True)[1].set_index('wind_code')
        stocks=df.index.tolist()
        # 获取其他字段数据
        df_1 = w.wss(stocks, 
                     "ev,mkt_freeshares,netprofit_ttm2,val_dividendyield3",
                     f"unit=1;tradeDate={st.session_state.end_date};rptDate=20241231",
                     usedf=True)[1]
        df_2 = w.wss(stocks, 
                    "industry_sw_2021,industry_citic",
                    f"tradeDate={st.session_state.end_date};industryType=1",
                    usedf=True)[1].rename(
                    columns={'INDUSTRY_CITIC':'中信一级行业',
                            'INDUSTRY_SW_2021':'申万一级行业'})
        df_3 = w.wss(stocks, 
                    "industry_sw_2021,industry_citic",
                    f"tradeDate={st.session_state.end_date};industryType=2",
                    usedf=True)[1].rename(
                    columns={'INDUSTRY_CITIC':'中信二级行业',
                            'INDUSTRY_SW_2021':'申万二级行业'})
        df_4 = w.wss(stocks, 
                    "industry_sw_2021,industry_citic",
                    f"tradeDate={st.session_state.end_date};industryType=3",
                    usedf=True)[1].rename(
                    columns={'INDUSTRY_CITIC':'中信三级行业',
                            'INDUSTRY_SW_2021':'申万三级行业'})
        # 合并两个字段数据
        df = pd.concat([df, df_1, df_2, df_3, df_4], axis=1)
        # 重命名字段并输出
        df = df.reset_index().rename(columns={
            'index':'股票代码',
            'sec_name':'股票名称',
            'i_weight':'权重',
            'industry':'行业',
            'EV':'总市值',
            'MKT_FREESHARES':'自由流通市值',
            'NETPROFIT_TTM2':'归母净利润TTM',
            'VAL_DIVIDENDYIELD3':'股息率TTM'})
        df[['总市值', '自由流通市值', '归母净利润TTM']] = df[['总市值', '自由流通市值', '归母净利润TTM']].map(lambda x: round(x / 100000000, 2))

        # 合并指数代码和指数名
        df['指数代码'] = index
        index_name = get_information_data(_indexes)['指数名称']
        df = pd.merge(df,
                    index_name,
                    left_on='指数代码',
                    right_on=index_name.index,
                    how='left'  # 即使右表无对应代码，左表数据仍保留
                    )

        index_component_data = pd.concat([index_component_data, df], axis=0)
    
    return index_component_data

# 缓存指数基础信息数据
@st.cache_data
def get_information_data(indexes):
    """获取指数基本信息"""
    information_data = w.wss(indexes, 
                            "sec_name, basedate, launchdate, repo_briefing, numberofconstituents, officialstyle, crm_issuer, exchange_cn",
                            usedf=True)[1]
    information_data = information_data.rename(columns={
                    'SEC_NAME':'指数名称',
                    'BASEDATE':'基准日',
                    'LAUNCHDATE':'发布日期',
                    'REPO_BRIEFING':'指数简介',
                    'NUMBEROFCONSTITUENTS':'成分股个数',
                    'OFFICIALSTYLE':'指数类别',
                    'CRM_ISSUER':'编制公司',
                    'EXCHANGE_CN':'交易所'}
                    )
    return information_data

# 缓存指数收益风险数据
@st.cache_data
def get_risk_data(indexes, start_date=None, end_date=None):
    # 用户可用控制条选择计算的区间长度
    if start_date is None:
        end_date = st.session_state.start_date
    if end_date is None:
        end_date = st.session_state.end_date

    risk_table = w.wss(indexes, 
      "sec_name,pct_chg_per,turn_per,stdevry,sharpe,risk_calmar,risk_maxdownside2,risk_maxupside2",
      f"startDate={start_date};",
      f"endDate={end_date};",
      "bondPriceType=2;",
      "period=2;returnType=1",
      "yield=1",
      usedf=True)[1]

    beta_table = pd.DataFrame()
    for index in indexes:
        beta_table[f'Beta/弹性（以{index}为基准）'] = w.wss(indexes, 
        "beta",
        f"startDate={start_date};endDate={end_date};period=2;returnType=1;index={index}",
        usedf=True)[1]
    
    risk_table = risk_table.rename(columns={
    'SEC_NAME':'指数名称',
    'PCT_CHG_PER':'区间涨跌幅',
    'TURN_PER':'区间换手率',
    'RISK_MAXUPSIDE2':'锐度',
    'RISK_MAXDOWNSIDE2':'最大回撤',
    'SHARPE':'区间年化夏普比率',
    'STDEVRY':'区间年化波动率',
    'RISK_CALMAR':'区间年化卡玛比率',
    })

    return risk_table.round(2), beta_table.round(2)

# 缓存指数PB
@st.cache_data
def get_PB(indexes):
    """获取指数估值数据"""
    PB = w.wsd(indexes, 
                "pb_lf",
                f"{st.session_state.start_date}", f"{st.session_state.end_date}",
                usedf=True)[1]
    return PB

# 缓存指数PE
@st.cache_data
def get_PE(indexes):
    """获取指数估值数据"""
    PE = w.wsd(indexes, 
                "pe_ttm",
                f"{st.session_state.start_date}", f"{st.session_state.end_date}",
                usedf=True)[1]
    return PE

# 缓存指数PE/PB分位数
@st.cache_data
def get_PE_PB_percentile(indexes):
    """获取市盈率和市净率分位数"""
    PE_PB_percentile = w.wss(indexes, 
        "val_pb_percentile,val_pe_percentile",
        f"tradeDate={st.session_state.end_date};startDate={st.session_state.start_date};endDate={st.session_state.end_date}",
        usedf=True)[1]
    PE_PB_percentile.rename(columns={'VAL_PB_PERCENTILE':'市净率分位数',
                                     'VAL_PE_PERCENTILE':'市盈率分位数'},
                            inplace=True)
    return PE_PB_percentile

# 缓存指数盈利数据
@st.cache_data
def get_earning_data(indexes):
    """获取营收和净利润数据，以及一致预测数据"""
    # 首先获取当前年份，判断上一年年报出了没
    curr_year = st.session_state.end_date[:4]
    # 获取上一年度
    last_year = str(int(curr_year) - 1)
    # 实验获取去年年报预测数据，如果没有预测数据，那么就已经出去年的年报了，否则还没出
    last_year_return = w.wss(indexes,
        "est_netprofit",
        f"unit=1;year={last_year};tradeDate={st.session_state.end_date}",
        usedf=True)[1]  
    # 判断上一年度是否有年报,即所有数据是否都是NaN
    if last_year_return.isnull().all().all():
        # 获取年份时间序列，包括当年年份前五年和后三年
        years = [int(last_year) - i for i in range(-5,4)]
    else:
        # 上一年度年报出了，以当前年度为基准    
        years = [int(curr_year) - i for i in range(-5,4)]
    years.sort()

    # 初始化两个数据帧用于存放收入和利润数据
    income_data = pd.DataFrame()
    profit_data = pd.DataFrame()
    for year in years[:5]:
        # 获取过去五年历史数据
        df1 = w.wss(indexes,
            "oper_rev,np_belongto_parcomsh",
            f"unit=1;rptDate={year}1231;rptType=1",
            usedf=True)[1]
        # 合并数据
        income_data = pd.concat([income_data, df1['OPER_REV']], axis=1).rename(columns={'OPER_REV': year})
        profit_data = pd.concat([profit_data, df1['NP_BELONGTO_PARCOMSH']], axis=1).rename(columns={'NP_BELONGTO_PARCOMSH': year})
    for year in years[5:]:
        # 获取未来三年一致预期数据
        df2 = w.wss(indexes,
            "est_sales,est_netprofit",
            f"unit=1;year={year};tradeDate={st.session_state.end_date}",
            usedf=True)[1]
        # 合并数据
        income_data = pd.concat([income_data, df2['EST_SALES']], axis=1).rename(columns={'EST_SALES': f'{year}E'})
        profit_data = pd.concat([profit_data, df2['EST_NETPROFIT']], axis=1).rename(columns={'EST_NETPROFIT': f'{year}E'})
    
    # 单位处理，将单位从万元转换为亿元
    income_data = income_data / 100000000
    profit_data = profit_data / 100000000

    return income_data, profit_data

# 缓存指数前20大成分股数据
@st.cache_data
def get_top20_concentration(_indexes):
    """计算前20大成分股集中度"""
    # 获取成分股数据
    component_data = get_index_component_data(_indexes)
    
    # 计算每个指数的前20大成分股集中度
    concentration_data = {}
    stock_data = {}

    for index in _indexes:
        # 筛选出当前指数的成分股
        index_components = component_data[component_data['指数代码'] == index].copy()
        # 按权重排序
        index_components = index_components.sort_values('权重', ascending=False)
        # 取前20大成分股
        index_df_top20 = index_components.head(20)
        # 计算权重和
        concentration = index_df_top20['权重'].sum()
        concentration_data[index] = concentration

        # 获取前20只成分股近三个月股价信息
        stock_data[index] = w.wsd(index_df_top20.index.tolist(), "close", "ED-3M", f"{st.session_state.end_date}", usedf=True)[1]

    return pd.Series(concentration_data), stock_data

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
            'excessreturn':'过去一年超额收益',
            'establishmentday':'基金成立日',
            'fundmanager':'基金经理',
            'company':'基金公司',
            'unitnav':'单位净值',
            'managementrate':'管理费',
            'windavg':'Wind三年评级',
            'fundtype':'基金类型'}, inplace=True)
        tracking_funds_data[index]['基金规模（亿元）'] = tracking_funds_data[index]['基金规模（亿元）'].apply(lambda x: format(x/100000000, '.2%'))

        # 获取近三个月
    return tracking_funds_data

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

select = alt.selection_point(name="select", on="click", fields=['股票代码'])
highlight = alt.selection_point(name="highlight", on="pointerover", empty=False)
legend_selection = alt.selection_point(fields=['指数名称'])

# 高亮显示默认参数功能
def highlight_select():
    stroke_width = (
        alt.when(select).then(alt.value(2, empty=False))
        .when(highlight).then(alt.value(1))
        .otherwise(alt.value(0))
    )
    return stroke_width

# sigmoid标准化函数
def sigmoid(x):
    """
    Sigmoid函数
    将数据映射到(0,1)区间
    """
    # 处理溢出问题
    x = np.clip(x, -500, 500)
    return 1 / (1 + np.exp(-x))

# Z-Score标准化函数
def zscore_normalize(data):
    """
    Z-Score标准化函数
    将数据转换为均值为0，标准差为1的分布
    """
    mean = data.mean()
    std = data.std()
    if std != 0:
        return (data - mean) / std
    else:
        return pd.Series(0, index=data.index)

# ————————————————————————————————————————————绘图函数模块————————————————————————————————————————————

# 显示指数基本信息
def show_information(indexes):
    """绘制指数基本信息表格"""
    information_table = get_information_data(indexes)
    st.dataframe(information_table.T, use_container_width=True)

# 显示指数过去5年历史走势和收益率走势
def show_plot(indexes):
    """绘制指数走势折线图"""
    # 获取万德的宽格式数据
    wide_data = get_index_data(indexes)

    # 创建标签页，使用标签页切换功能显示
    tabs = st.tabs(["收益率走势", "价格走势"])

    # 获取指数名称
    index_name = get_information_data(indexes)['指数名称']
    
    with tabs[0]:  # 收益率走势
        # 确保索引（日期）是datetime类型
        wide_data.index = pd.to_datetime(wide_data.index)
        
        # 添加基期选择功能
        min_date = wide_data.index.min()
        max_date = wide_data.index.max()
        
        base_date, end_date = st.slider(
            "选择收益率时间范围", 
            min_value=min_date.to_pydatetime(), 
            max_value=max_date.to_pydatetime(), 
            value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
            format="YYYY-MM-DD"
        )
        
        # 直接获取基期之后，结束期之前的数据，舍弃之前的数据
        normalized_data = wide_data.loc[base_date:end_date]
        normalized_data = normalized_data/normalized_data.iloc[0] - 1
        
        # 使用melt转换为长格式数据
        long_data = normalized_data.reset_index().rename(columns={'index': 'date'}).melt(
            id_vars='date',         # 保留日期作为标识列
            var_name='order_book_id',      # 股票代码列的新名称
            value_name='return',      # 收益率列的新名称
            ignore_index=False       # 保留原始索引（可选）
        )

        # 确保value列是数值类型
        long_data['return'] = pd.to_numeric(long_data['return'], errors='coerce')

        long_data = pd.merge(long_data,
                            index_name,
                            left_on='order_book_id',
                            right_on=index_name.index,
                            how='left'  # 即使右表无对应代码，左表数据仍保留
                            )

        # --- 核心代码仅需一行 ---
        fig = px.line(
            long_data,
            x='date',
            y='return',
            color='指数名称',  # 使用 '指数名称' 列来区分不同线条
            title='指数收益率走势对比',
            labels={
                'date': '日期',
                'return': '累积收益率(%)',
                '指数名称': '指数名称'
            }
        )

        fig.update_xaxes(
        tickformat="%Y-%m-%d",  # 格式化为 YYYY-MM-DD
        title="日期"
        )

        # --- 定制悬停信息 (Tooltip) ---
        # 'xunified' 模式会在一个共享的框中显示同一x轴上所有线条的数据
        fig.update_traces(hovertemplate="%{y:.2f}%")
        fig.update_layout(
            hovermode='x unified',
            xaxis_title='日期',
            yaxis_title='累积收益率(%)',
            legend_title='指数名称'
        )

        st.plotly_chart(fig)
    
    with tabs[1]:
        # 确保索引（日期）是datetime类型
        wide_data.index = pd.to_datetime(wide_data.index)
        
        # 使用melt转换为长格式数据
        long_data = wide_data.reset_index().rename(columns={'index': 'date'}).melt(
            id_vars='date',         # 保留日期作为标识列
            var_name='order_book_id',      # 股票代码列的新名称
            value_name='close',      # 收盘价列的新名称
            ignore_index=False       # 保留原始索引（可选）
        )

        # 确保value列是数值类型
        long_data['close'] = pd.to_numeric(long_data['close'], errors='coerce')

        long_data = pd.merge(long_data,
                            index_name,
                            left_on='order_book_id',
                            right_on=index_name.index,
                            how='left'  # 即使右表无对应代码，左表数据仍保留
                            )

        # --- 核心代码仅需一行 ---
        fig = px.line(
            long_data,
            x='date',
            y='close',
            color='指数名称',  # 使用 '指数名称' 列来区分不同线条
            title='指数价格走势对比',
            labels={
                'date': '日期',
                'close': '收盘价',
                '指数名称': '指数名称'
            }
        )

        fig.update_xaxes(
        tickformat="%Y-%m-%d",  # 格式化为 YYYY-MM-DD
        title="日期"
        )

        # --- 定制悬停信息 (Tooltip) ---
        # 'xunified' 模式会在一个共享的框中显示同一x轴上所有线条的数据
        fig.update_traces(hovertemplate="%{y:.2f}")
        fig.update_layout(
            hovermode='x unified',
            xaxis_title='日期',
            yaxis_title='收盘价',
            legend_title='指数名称'
        )

        st.plotly_chart(fig)

# 显示指数估值图表
def show_valuation_chart(indexes):
    """绘制指数收益估值图表"""
    # 获取指数名称
    index_info = get_information_data(indexes)
    
    # 获取数据
    # 获取未来三年一致预期数据
    income_data, profit_data = get_earning_data(indexes)
    # 获取PE、PB和其分位数数据
    PE = get_PE(indexes)
    PB = get_PB(indexes)
    PE_PB_percentile = get_PE_PB_percentile(indexes)

    # 创建标签页
    tabs = st.tabs([name for name in index_info['指数名称']])

    for i, (index_code, name) in enumerate(zip(indexes, index_info['指数名称'])):
        with tabs[i]:
            col1, col2 = st.columns(2)
            with col1:
                # 修改后：
                selected_earning = st.radio("选择数据", ['营业收入','归母净利润'], key=f"earning_{i}")

                if selected_earning == '营业收入':
                    selected_data = income_data.loc[index_code]
                else:
                    selected_data = profit_data.loc[index_code]
                
                # 创建带有副坐标轴的子图
                fig1 = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 确定哪些是预测数据(以E结尾)
                is_forecast = [str(x).endswith('E') for x in selected_data.index]
                
                # 添加条形图
                fig1.add_trace(
                    go.Bar(
                        x=selected_data.index, 
                        y=selected_data.values, 
                        name=f'{selected_earning}',
                        marker_color=['orange' if f else 'blue' for f in is_forecast]
                    ),
                    secondary_y=False,
                )
                
                # 计算同比增速
                yoy_growth = selected_data.pct_change() * 100
                
                # 添加同比增速折线图
                fig1.add_trace(
                    go.Scatter(
                        x=yoy_growth.index, 
                        y=yoy_growth.values, 
                        name='同比增速(%)',
                        line=dict(color='red')
                    ),
                    secondary_y=True,
                )
                
                # 设置坐标轴标题
                fig1.update_xaxes(title_text="年份")
                fig1.update_yaxes(title_text=f"{selected_earning}(亿元)", secondary_y=False)
                fig1.update_yaxes(title_text="同比增速(%)", secondary_y=True)
                
                # 设置图表标题
                fig1.update_layout(title_text=f'{name}近五年和未来三年{selected_earning}一致预期')
                
                st.plotly_chart(fig1)

            with col2:
                selected_valuation = st.radio("选择数据", ['PE','PB'], key=f"valuation_{i}")
                if selected_valuation == 'PE':
                    selected_series = PE[index_code]
                    selected_percentile = PE_PB_percentile.loc[index_code,'市盈率分位数']
                else:
                    selected_series = PB[index_code]
                    selected_percentile = PE_PB_percentile.loc[index_code,'市净率分位数']
                
                # 创建带有副坐标轴的子图
                fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 添加估值折线图
                fig2.add_trace(
                    go.Scatter(
                        x=selected_series.index, 
                        y=selected_series.values, 
                        name=f'{selected_valuation}',
                        line=dict(color='blue')
                    ),
                    secondary_y=False,
                )
                
                # 添加分位数线
                fig2.add_trace(
                    go.Scatter(
                        x=[selected_series.index[0], selected_series.index[-1]],
                        y=[selected_percentile, selected_percentile],
                        name='分位数',
                        line=dict(color='red', dash='dash'),
                        text=[f'{selected_valuation}分位数: {selected_percentile:.2f}']
                    ),
                    secondary_y=True,
                )
                
                # 设置坐标轴标题
                fig2.update_xaxes(title_text="日期")
                fig2.update_yaxes(title_text=f"{selected_valuation}", secondary_y=False)
                fig2.update_yaxes(title_text="分位数", secondary_y=True)
                
                # 设置图表标题
                fig2.update_layout(title_text=f'{name}近五年{selected_valuation}走势和分位数')
                
                st.plotly_chart(fig2)

# 显示指数风险收益特征表格
def show_risk_table(index_codes):
    # 由用户在现有的指数中选定一个指数作为基准指数
    if len(index_codes) > 1:
        # 选择基准指数
        selected_index = st.selectbox("选择基准指数", index_codes)

        # 使用侧边栏中选择的日期
        risk_table_precise, beta_table = get_risk_data(index_codes, st.session_state.start_date, st.session_state.end_date)
        
        # 确保要访问的列存在于beta_table中
        beta_column_name = f'Beta/弹性（以{selected_index}为基准）'
        if beta_column_name in beta_table.columns:
            risk_table_precise = pd.concat([risk_table_precise, beta_table[beta_column_name]], axis=1)
        else:
            st.warning(f"未找到Beta列: {beta_column_name}")
            # 可以选择使用第一列或其他默认列
            if not beta_table.empty:
                first_column = beta_table.columns[0]
                risk_table_precise = pd.concat([risk_table_precise, beta_table[first_column]], axis=1)
                st.info(f"使用默认Beta列: {first_column}")

        # 确保DataFrame列类型与Arrow兼容
        for col in risk_table_precise.columns:
            if risk_table_precise[col].dtype == 'object':
                risk_table_precise[col] = risk_table_precise[col].astype(str)

        # 使用pandas.style添加热力图显示功能
        # 对数值列应用热力图样式
        numeric_columns = risk_table_precise.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            # 只对数值列进行百分比格式化
            styled_table = risk_table_precise.style.background_gradient(cmap='Oranges', subset=numeric_columns)
            # 分别设置数值列和非数值列的格式
            styled_table = styled_table.format({col: "{:.2f}" for col in numeric_columns})
            st.dataframe(styled_table, use_container_width=True, hide_index=True)
        else:
            st.dataframe(risk_table_precise, use_container_width=True, hide_index=True)

    else:
        st.info("当前仅选择了一个指数，如需对比相对指数，请添加更多指数。")

# 显示指数多维度信息对比雷达图
def show_radar_graph(index_codes):
    """使用plotly绘制指数风险指标雷达图"""
    if len(index_codes) < 2:
        st.info("至少需要选择两个指数才能生成雷达图")
        return
    
    # 创建两列布局，左边放图，右边放解释说明
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # 获取风险数据
        risk_table, beta_table = get_risk_data(
            index_codes, 
            st.session_state.start_date, 
            st.session_state.end_date
        )
        
        # 选择基准指数
        selected_index = st.selectbox("选择基准指数（雷达图）", index_codes, key="radar_index")
        
        # 准备雷达图数据
        # 初始化雷达图数据DataFrame
        radar_data = pd.DataFrame(index=index_codes)
        
        # 获取指数名称
        index_names = get_information_data(index_codes)
        if "指数名称" in index_names.columns:
            radar_data["指数名称"] = index_names["指数名称"]
        
        # 添加新的指标数据
        # 1. 锐度（从风险数据中获取）
        radar_data["锐度"] = risk_table["锐度"]
        
        # 2. Beta/弹性（以基准指数为基准）
        beta_column_name = f'Beta/弹性（以{selected_index}为基准）'
        if beta_column_name in beta_table.columns:
            radar_data["Beta/弹性（以基准指数为基准）"] = beta_table[beta_column_name]
        else:
            st.warning(f"未找到Beta列: {beta_column_name}，使用默认Beta列")
            if not beta_table.empty:
                first_column = beta_table.columns[0]
                radar_data["Beta/弹性（以基准指数为基准）"] = beta_table[first_column]
            else:
                # 添加默认Beta列为1
                radar_data["Beta/弹性（以基准指数为基准）"] = 1.0
        
        # 3. 归母净利润同比增速
        # 获取归母净利润数据
        _, profit_data = get_earning_data(index_codes)
        # 计算最近年度的同比增速
        radar_data["归母净利润同比增速"] = (profit_data.iloc[5] - profit_data.iloc[4]) / profit_data.iloc[4].abs() * 100
        
        # 4. 年内收益率
        return_data = get_return_data(index_codes)
        # 获取当前年份的收益率（最后一列）
        current_year = return_data.columns[-1]
        yearly_return_data = return_data[current_year]
        radar_data["年内收益率"] = yearly_return_data
        
        # 5. 前20大成分股集中度
        concentration_data, __ = get_top20_concentration(index_codes)
        radar_data["前20大成分股集中度"] = concentration_data
        
        # 6. PE分位数
        pe_pb_percentile = get_PE_PB_percentile(index_codes)
        radar_data["市盈率分位数"] = pe_pb_percentile["市盈率分位数"]
        
        # 7. 卡玛比率（从风险数据中获取）
        radar_data["卡玛比率"] = risk_table["区间年化卡玛比率"]
        
        # 定义要展示的指标列表
        all_metrics = ["锐度", "Beta/弹性（以基准指数为基准）", "归母净利润同比增速", "年内收益率", "前20大成分股集中度", "市盈率分位数", "卡玛比率"]
        
        # 数据标准化处理，使用Sigmoid函数
        normalized_data = radar_data[all_metrics].copy()
        
        # 对每个指标进行Sigmoid标准化
        for metric in all_metrics:
            if metric == "前20大成分股集中度":
                # 集中度越接近50%越好，偏离50%越远得分越低
                # 先转换为与50的偏差，然后进行Sigmoid标准化
                deviation_from_50 = abs(normalized_data[metric] - 50)
                # 对偏差取负值，使越接近50得分越高
                normalized_values = -deviation_from_50
                # 标准化到0-1区间
                min_val = normalized_values.min()
                max_val = normalized_values.max()
                if max_val > min_val:
                    normalized_values = (normalized_values - min_val) / (max_val - min_val)
                else:
                    normalized_values = pd.Series(0.5, index=normalized_values.index)
                # 应用Sigmoid函数
                normalized_data[metric] = sigmoid(normalized_values * 10 - 5) * 100  # 缩放以获得更好的区分度
            # elif metric in ["Beta/弹性（以基准指数为基准）"]:
            #     # Beta值越接近1越好，偏离1越远得分越低
            #     # 先转换为与1的偏差，然后进行Sigmoid标准化
            #     deviation_from_1 = abs(normalized_data[metric] - 1)
            #     # 对偏差取负值，使越接近1得分越高
            #     normalized_values = -deviation_from_1
            #     # 标准化到0-1区间
            #     min_val = normalized_values.min()
            #     max_val = normalized_values.max()
            #     if max_val > min_val:
            #         normalized_values = (normalized_values - min_val) / (max_val - min_val)
            #     else:
            #         normalized_values = pd.Series(0.5, index=normalized_values.index)
            #     # 应用Sigmoid函数
            #     normalized_data[metric] = sigmoid(normalized_values * 10 - 5) * 100  # 缩放以获得更好的区分度
            else:
                # 其他指标越大越好
                # 标准化到0-1区间
                metric_data = normalized_data[metric]
                min_val = metric_data.min()
                max_val = metric_data.max()
                if max_val > min_val:
                    normalized_values = (metric_data - min_val) / (max_val - min_val)
                else:
                    normalized_values = pd.Series(0.5, index=metric_data.index)
                # 应用Sigmoid函数
                normalized_data[metric] = sigmoid(normalized_values * 10 - 5) * 100  # 缩放以获得更好的区分度
        
        # 创建雷达图
        fig = go.Figure()
        
        # 为每个指数添加雷达图轨迹
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
        
        for i, index in enumerate(index_codes):
            # 获取指数名称
            index_name = radar_data.loc[index, '指数名称'] if '指数名称' in radar_data.columns else index
            
            # 获取该指数的数据
            values = normalized_data.loc[index].tolist()
            
            # 添加轨迹
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # 闭合图形
                theta=all_metrics + [all_metrics[0]],  # 闭合图形
                fill='toself',
                name=index_name,
                line=dict(color=colors[i % len(colors)]),
                opacity=0.7
            ))
        
        # 设置雷达图布局
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="指数风险指标雷达图对比",
            title_x=0.5,  # 居中标题
            width=800,
            height=600
        )

        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 右侧解释说明
        st.markdown("### 雷达图指标说明")
        st.markdown("""
        1. **锐度**：衡量收益率的稳定性，越大越好
        2. **Beta/弹性**：衡量指数相对于基准指数的敏感度，越接近1越好
        3. **归母净利润同比增速**：反映指数成分股整体盈利增长情况，越大越好
        4. **年内收益率**：反映指数当年的收益表现，越大越好
        5. **前20大成分股集中度**：反映指数前20大成分股的权重集中程度，越接近50%越好
        6. **市盈率分位数**：反映指数当前估值水平，需结合市场环境判断，越大越好
        7. **卡玛比率**：衡量单位回撤所能获得的收益，越大越好
        """)
        
        st.markdown("### 数据处理说明")
        st.markdown("""
        - 所有指标均已进行归一化处理，映射到0-100区间
        - 对于Beta值，越接近1得分越高
        - 对于前20大成分股集中度，越接近50%得分越高
        - 其他指标越大越好
        - 得分越高表示该指标在所选指数中的相对表现越好
        """)
   
    # 显示数据表
    st.subheader("雷达图数据详情")
    # 显示原始数据而非标准化数据，并使用指数名称作为索引
    display_data = radar_data[all_metrics].copy()
    # 如果有指数名称列，使用它作为索引
    if "指数名称" in radar_data.columns:
        display_data.index = radar_data["指数名称"]
    # 使用pandas.style添加热力图显示功能
    # 只对数值列进行百分比格式化
    styled_data = display_data.style.background_gradient(cmap='Oranges', axis=0)
    # 获取数值列并分别设置格式
    numeric_columns = display_data.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        styled_data = styled_data.format({col: "{:.2f}" for col in numeric_columns})
    st.dataframe(styled_data, use_container_width=True)

# 显示指数年度收益对比条形图和表格
def show_year_return(index_codes):
    # 获取年度收益数据
    return_data = get_return_data(index_codes)
    
    # 获取当前年份
    curr_year = int(st.session_state.end_date[:4])
    
    # 准备用于图表的数据
    chart_data = []
    for year in return_data.columns:
        for index_code in index_codes:
            if index_code in return_data.index:
                # 确保收益值有效
                value = return_data.loc[index_code, year]
                # 只添加非空值，并确保年份是字符串格式
                if pd.notna(value):  
                    chart_data.append({
                        '年份': str(year),
                        '指数代码': index_code,
                        '收益': float(value)  # 确保收益是浮点数格式
                    })
    
    # 转换为DataFrame
    chart_df = pd.DataFrame(chart_data)
    # 获取指数名称用于显示
    index_info = get_information_data(index_codes)
    chart_df['指数名称'] = chart_df['指数代码'].map(index_info['指数名称'])
    
    # 确保年份在图表中正确排序显示
    # 创建年份排序列表，将"年至今"放在最后
    numeric_years = [str(col) for col in return_data.columns if str(col).isdigit()]
    all_years = sorted(numeric_years, key=int)
    # 添加"年至今"列（如果存在）
    current_year_label = f'{curr_year}年至今'
    if current_year_label in return_data.columns:
        all_years.append(current_year_label)
    # 如果没有找到"年至今"列，检查是否有其他包含当前年份的列
    elif any(str(curr_year) in str(col) for col in return_data.columns):
        year_cols = [str(col) for col in return_data.columns if str(curr_year) in str(col)]
        # 确保"年至今"列在最后
        year_cols = [col for col in year_cols if col != current_year_label] + [col for col in year_cols if col == current_year_label]
        all_years.extend(year_cols)
        
    # 确保所有年份都在列表中（去重并保持顺序）
    unique_years = []
    for year in all_years:
        if year not in unique_years:
            unique_years.append(year)
    all_years = unique_years
    
    # 创建年度收益对比条形图
    fig = px.bar(
        chart_df, 
        x='年份', 
        y='收益', 
        color='指数名称',
        barmode='group',
        title='指数年度收益对比',
        labels={'收益': '收益 (%)'},
        text='收益',
        category_orders={"年份": all_years}
    )
    
    # 确保所有年份都显示在x轴上
    fig.update_xaxes(
        type='category',
        categoryorder='array',
        categoryarray=all_years,
        tickvals=all_years  # 确保所有年份都显示为刻度值
    )
    
    # 更新文本格式
    fig.update_traces(
        texttemplate='%{text:.2f}%', 
        textposition='outside'
    )
    
    # 更新布局
    fig.update_layout(
        xaxis_title='年份',
        yaxis_title='收益 (%)',
        legend_title='指数',
        title_x=0.5,
        width=800,
        height=600
    )
    
    # 显示图表
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示数据表并添加热力图样式
    st.subheader("年度收益数据表")
    
    # 重新组织数据表格式，使年份为列，指数为行
    table_data = chart_df.pivot(index='指数名称', columns='年份', values='收益')
    
    # 确保列的顺序与图表一致
    if all(year in table_data.columns for year in all_years):
        table_data = table_data[all_years]
    
    # 使用dataframe.style添加热力图显示功能，色阶采用"Oranges"
    # 先创建热力图样式，再对数值应用百分比格式化
    styled_table = table_data.style.background_gradient(cmap='Oranges', axis=None)
    # 只对数值列进行百分比格式化
    numeric_columns = table_data.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        styled_table = styled_table.format({col: "{:.2f}%" for col in numeric_columns})
    st.dataframe(styled_table, use_container_width=True)

# 显示指数成分股表格
def show_table(df):
    data_dict = {}
    # 获取指数名称
    index_info = get_information_data(list(df['指数代码'].unique()))
    
    # 创建标签页
    tabs = st.tabs([name for name in index_info['指数名称']])

    # 获取指数前20大股票数据
    __, stock_data = get_top20_concentration(index_info.index)

    for i, (index_code, name) in enumerate(zip(index_info.index, index_info['指数名称'])):
        with tabs[i]:
            # 使用.loc创建一个完整的副本
            index_df = df.loc[df['指数代码'] == index_code].copy()

            # 处理数据
            index_df = index_df.set_index('股票代码').sort_values(by='权重', ascending=False)
            index_df_top20 = index_df.iloc[:,:8].head(20)

            # 删除列
            index_df_top20.drop('行业', axis=1, inplace=True)
            
            # 计算指数前20大成分股累积权重，并插入到权重列后面
            index_df_top20.insert(loc=2, column='累积权重', value=index_df_top20['权重'].cumsum().apply(lambda x: format(x/ 100, '.2%') ))
            index_df_top20['权重'] = index_df_top20['权重'].apply(lambda x: format(float(x)/ 100, '.2%'))

            # 从缓存中获取指数前20大成分股数据
            stock_prices = stock_data[index_code]

            # 先转换为长格式
            stock_prices = stock_prices.reset_index().melt(id_vars='index', var_name='股票代码', value_name='close')

            # 直接将价格数据通过groupby转换为列表
            index_df_top20.loc[:, '近三个月股价走势'] = [
                group['close'].tolist() 
                for _, group in stock_prices.groupby('股票代码')
            ]

            index_df_top20.rename(columns=
                            {'总市值': '总市值（亿元）', 
                            '自由流通市值': '自由流通市值（亿元）', 
                            '归母净利润TTM': '归母净利润TTM（亿元）', 
                            '股息率TTM': '股息率TTM（%）'}, inplace=True)

            st.dataframe(
                index_df_top20.style.background_gradient(
                    cmap='Oranges', 
                    subset=['总市值（亿元）', '自由流通市值（亿元）', '归母净利润TTM（亿元）', '股息率TTM（%）']
                    ).format({
                        '总市值（亿元）': "{:.2f}",
                        '自由流通市值（亿元）': "{:.2f}",
                        '归母净利润TTM（亿元）': "{:.2f}",
                        '股息率TTM（%）': "{:.2f}"
                    }),
                column_config={
                    '近三个月股价走势': st.column_config.AreaChartColumn("近三个月股价走势"),
                },
            )
            
        # 将原始数据储存在字典里备用
        data_dict[index_code] = index_df

    # 5.显示详细的dataframe信息，默认隐藏
    st.divider()
    st.subheader("指数原始数据")
    
    if len(index_info) > 8:
        st.error("最多只能选择8个指数进行对比")
    else:
        # 默认隐藏原始数据
        with st.expander("点击查看原始数据"):
            tabs = st.tabs([name for name in index_info['指数名称']])
            for i, (index_code, name) in enumerate(zip(index_info.index, index_info['指数名称'])):
                with tabs[i]:
                    st.dataframe(data_dict[index_code])

# 显示指数成分股市值分布条形图
def show_bar(df):
    # 复制df以免数据污染
    value_df = df.copy().sort_values(by='权重', ascending=False)

    # 获取所有唯一的指数代码
    all_indexes = list(value_df['指数代码'].unique())
    
    # 创建multi_select用于选择要对比的指数（最多两个）
    selected_indexes = st.multiselect(
        "选择要对比的指数（最多两个）:",
        options=all_indexes,
        default=all_indexes[:2] if len(all_indexes) >= 2 else all_indexes
    )
    
    # 检查选择的指数数量
    if len(selected_indexes) > 2:
        st.error("最多只能选择两个指数进行对比")
        return
    
    def bar_chart(y_axis_option):
        # 创建排序选择器
        col1, col2 = st.columns([3, 2])
        with col1:
            # 添加图例说明
            st.markdown("""
            **图表说明：**
            - **橙色柱状图**表示该股票在多个指数中同时出现
            - **蓝色柱状图**表示该股票仅在当前指数中出现
            - 点击柱状图可跨指数高亮显示该成分股
            - 将鼠标悬停在柱状图上可查看详细信息
            """)
        with col2:
            sort_option = st.radio("排序方式:", 
                                ['按权重排序',f'按{y_axis_option}降序', f'按{y_axis_option}升序'])

        # 根据选择动态生成排序参数
        if sort_option == f'按{y_axis_option}降序':
            sort_field = '-x'
        elif sort_option == f'按{y_axis_option}升序':
            sort_field = 'x'
        else:
            sort_field = None

        # 计算选中指数中的重复股票
        if len(selected_indexes) > 1:
            # 先筛选出选中指数的数据
            filtered_df = value_df[value_df['指数代码'].isin(selected_indexes)].copy()
            # 标记重复股票
            filtered_df['is_duplicate'] = filtered_df['股票代码'].duplicated(keep=False)
            # 使用iloc和布尔索引来更新原DataFrame，避免索引重复问题
            mask = value_df['指数代码'].isin(selected_indexes)
            value_df.loc[mask, 'is_duplicate'] = filtered_df['is_duplicate'].values
        else:
            value_df['is_duplicate'] = False

        price_charts = {}
        # 创建市值比对图表
        for index in selected_indexes:
            index_df = value_df[value_df['指数代码'] == index].head(50).copy()
            
            # 设置Y轴数据
            y_field = "自由流通市值" if y_axis_option == "自由流通市值" else "总市值"
            
            base = alt.Chart(index_df).encode(
                y=alt.Y("股票名称:N", sort=sort_field),  # 改为竖排条形图
                x=alt.X(f"{y_field}:Q", title=y_axis_option),
                tooltip=[
                    alt.Tooltip("股票代码:N", title="股票代码"),
                    alt.Tooltip("股票名称:N", title="股票名称"),
                    alt.Tooltip("总市值:Q", title="总市值(亿元)", format=",.2f"),
                    alt.Tooltip("自由流通市值:Q", title="自由流通市值(亿元)", format=",.2f"),
                    alt.Tooltip("权重:Q", title="权重(%)", format=",.2f")
                ]
            )

            bars = base.mark_bar(
                cursor="pointer",
                stroke="#000000"  # 使用 mark_bar 参数设置边框颜色
            ).encode(
                color=alt.condition(
                    alt.datum.is_duplicate,
                    alt.value("#FF7F50"),  # 重复股票用橙色
                    alt.value("#4C78A8")   # 非重复股票用蓝色
                ),
                fillOpacity=alt.condition(select, alt.value(1), alt.value(0.3)),
                strokeWidth=highlight_select()
            )

            chart = bars.add_params(
                select, highlight
            ).properties(
                title=f"{index_df['指数名称'].values[0]}前50支成分股{y_axis_option}",
                width=400,
                height=800  # 增加高度以适应竖排条形图
            )

            price_charts[index] = chart

        # 合并图表
        if price_charts:
            agg_chart = alt.hconcat(*price_charts.values()).configure_scale(bandPaddingInner=0.2)
            # 显示图表
            st.altair_chart(agg_chart, use_container_width=True)
        else:
            st.warning("请选择至少一个指数进行对比")

    # 创建标签页，使用标签页切换功能显示
    tabs = st.tabs(["自由流通市值", "总市值"])
    with tabs[0]:
        bar_chart("自由流通市值")
    with tabs[1]:
        bar_chart("总市值")
    
# 显示指数成分股分布饼图
def show_chart(index_codes, df):
    # 行业分类选择改为st.selectbox
    industry_standard = st.selectbox("选择行业分类标准", ["申万一级行业", "中信一级行业", "申万二级行业", "中信二级行业", "申万三级行业", "中信三级行业"])

    # 使用st.columns将页面分为两列
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 使用说明
        1. 选择行业分类标准：在下拉框中选择申万或中信行业，每种行业分类共有三个层级，共六个选项
        2. 选择饼图大小标准：在右侧单选框中选择按成分股数量计算或按成分股权重计算
        3. 饼图显示条件：当选取的指数数量不超过4个时，会显示各指数的行业分布饼图
        4. 饼图显示备注：饼图只显示申万或中信一级行业分布，无论选择哪个行业级别
        5. 数据表格：展开"查看详细数据"可查看各指数的行业分布详细数据，按所选行业级别显示
        """)
    
    with col2:
        # 将另一个st.radio放到页面右边
        size_standard = st.radio("选择饼图大小标准", ["按成分股数量计算", "按成分股权重计算"], horizontal=True)
    
    # 确定用于饼图的一级行业列
    if "申万" in industry_standard:
        pie_industry_column = "申万一级行业"
        selected_colors = sw_industry_colors
    else:  # 中信行业
        pie_industry_column = "中信一级行业"
        selected_colors = zx_industry_colors
    
    # 创建行业分布饼图
    industry_charts = {}
    industry_dataframes = {}  # 用于存储每个指数的行业数据
    
    for index in index_codes:
        # 获取该指数的数据
        index_df = df[df['指数代码'] == index].copy()
        index_name = get_information_data([index]).loc[index, '指数名称']
        
        # 根据选择的行业标准确定数据表使用的行业列
        data_table_column = industry_standard
        
        # 用于饼图的一级行业数据
        if size_standard == "按成分股数量计算":
            # 统计一级行业分布
            pie_industry_counts = index_df[pie_industry_column].value_counts().reset_index()
            pie_industry_counts.columns = ['行业', '数量']
            pie_industry_counts['占比'] = pie_industry_counts['数量'] / pie_industry_counts['数量'].sum() * 100
            
            # 为数据表准备所选级别的行业数据
            data_table_counts = index_df[data_table_column].value_counts().reset_index()
            data_table_counts.columns = ['行业', '数量']
            data_table_counts['占比(%)'] = (data_table_counts['数量'] / data_table_counts['数量'].sum() * 100).round(2)
            
        else:  # 按成分股权重计算
            # 对每一个一级行业groupby，然后对其"权重"求和
            pie_industry_weights = index_df.groupby(pie_industry_column)['权重'].sum().reset_index()
            pie_industry_weights.columns = ['行业', '权重']
            pie_industry_weights['占比'] = pie_industry_weights['权重'] / pie_industry_weights['权重'].sum() * 100
            
            # 为数据表准备所选级别的行业数据
            data_table_weights = index_df.groupby(data_table_column)['权重'].sum().reset_index()
            data_table_weights.columns = ['行业', '权重']
            data_table_weights['占比(%)'] = data_table_weights['占比(%)'].round(2)
            
            # 为数据表准备数据
            data_table_counts = data_table_weights.copy()
            data_table_counts.columns = ['行业', '权重', '占比(%)']
            data_table_counts['占比(%)'] = data_table_counts['占比(%)'].round(2)
        
        # 为饼图准备数据，并按占比降序排列
        pie_data = pie_industry_counts.copy() if size_standard == "按成分股数量计算" else pie_industry_weights.copy()
        if size_standard == "按成分股数量计算":
            pie_data = pie_data.rename(columns={'数量': '值'})
        else:
            pie_data = pie_data.rename(columns={'权重': '值'})
        
        # 按占比降序排列
        pie_data = pie_data.sort_values('值', ascending=True)
        
        # 修改hovertemplate中的"数量"为动态显示
        value_label = "数量" if size_standard == "按成分股数量计算" else "权重"
        
        # 创建plotly饼图，使用固定的颜色映射
        fig = go.Figure(data=[go.Pie(
            labels=pie_data['行业'],
            values=pie_data['值'],
            hole=0.3,  # 创建环形图
            marker_colors=[selected_colors.get(industry, '#808080') for industry in pie_data['行业']],  # 使用配色方案
            textinfo='label+percent',
            textposition='inside',
            direction='clockwise',
            hovertemplate=f'<b>%{{label}}</b><br>{value_label}: %{{value}}<br>占比: %{{percent}}<extra></extra>'
        )])
        
        fig.update_layout(
            title=f"{index_name}一级行业分布",
            showlegend=False,  # 去掉图例
            width=400,
            height=400
        )
        
        industry_charts[index] = fig
        industry_dataframes[index] = data_table_counts  # 使用所选级别的数据用于数据表
    
    # 设置一个限制条件，当选定指数超过4个时，不显示饼图
    if len(index_codes) <= 4:
        # 创建多列布局
        cols = st.columns(len(index_codes))
        for i, (index, chart) in enumerate(industry_charts.items()):
            with cols[i]:
                st.plotly_chart(chart, use_container_width=True)
    else:
        st.warning("当选取的指数数量超过4个时，为保证页面显示效果，不显示饼图。")
    
    # 显示行业分布数据表，使用热力图样式

    # 创建一个index为行业列表，columns为选中的指数的dataframe
    # 获取所有行业列表（基于所选的行业级别）
    all_industries = set()
    for df_temp in industry_dataframes.values():
        all_industries.update(df_temp['行业'].tolist())
    all_industries = sorted(list(all_industries))
    
    # 根据选择的标准（数量或权重）创建dataframe
    if size_standard == "按成分股数量计算":
        # 创建以行业为index，指数为columns的dataframe
        heatmap_data = pd.DataFrame(index=all_industries, columns=index_codes)
        for index, df_temp in industry_dataframes.items():
            for _, row in df_temp.iterrows():
                heatmap_data.loc[row['行业'], index] = row['数量']
        heatmap_data = heatmap_data.fillna(0)
    else:  # 按成分股权重计算
        # 创建以行业为index，指数为columns的dataframe
        heatmap_data = pd.DataFrame(index=all_industries, columns=index_codes)
        for index, df_temp in industry_dataframes.items():
            for _, row in df_temp.iterrows():
                heatmap_data.loc[row['行业'], index] = row['权重']
        heatmap_data = heatmap_data.fillna(0)
    
    # 将列名从指数代码改为指数名称
    index_name_mapping = {index: get_information_data([index]).loc[index, '指数名称'] for index in index_codes}
    heatmap_data = heatmap_data.rename(columns=index_name_mapping)
    
    # 创建两个标签页
    tab1, tab2 = st.tabs([size_standard[4:6], "占比"])
    
    with tab1:
        # 显示权重/数量数据
        # 限制浮点数位数显示为.1f
        st.dataframe(
            heatmap_data.style.background_gradient(cmap='Oranges'), 
            hide_index=False
        )
    
    with tab2:
        # 显示占比数据
        percentage_data = heatmap_data.div(heatmap_data.sum(axis=0), axis=1) *100
        st.dataframe(
            percentage_data.style.background_gradient(cmap='Oranges').format("{:.2f}%"), 
            hide_index=False
        )

# 显示大类资产相关系数矩阵热力图
def show_assets_heatmap(indexes):
    """绘制选定指数与大类资产的相关性热力图"""
    # 获取指数数据
    df = get_index_data(indexes)
    # 获取其他大类资产数据
    asset_df = get_assets_data()
    # 合并数据
    df = pd.concat([df, asset_df], axis=1)
    
    # 获取资产名称映射
    asset_names = {
        'CBA08301.CS': '1-5 年国开债指数',
        'AU9999.SGE': 'SGE 黄金',
        'DCESMFI.DCE': '大商所豆粕期货价格',
        'IMCI.SHF': '上期有色金属',
        '000201.CZC': '易盛能化 A',
        'H11014.CSI': '中证短融'
    }
    # 获取指数名称
    index_names = get_information_data(indexes)['指数名称'].to_dict()
    names_dict = {**index_names, **asset_names}
    
    # 计算相关性矩阵
    corr = df.corr()
    
    # 将相关系数矩阵转换为长格式
    corr_df = corr.reset_index()
    corr_df = corr_df.melt(id_vars=['index'], var_name='variable', value_name='correlation')
    corr_df.columns = ['资产1', '资产2', '相关系数']
    
    # 替换代码为名称
    corr_df['资产1'] = corr_df['资产1'].map(names_dict)
    corr_df['资产2'] = corr_df['资产2'].map(names_dict)

    # 创建交互式热力图
    selection = alt.selection_point(
        fields=['资产1', '资产2'],
        bind='legend'
    )

    base = alt.Chart(corr_df).encode(
        x=alt.X('资产1:N', title='', sort=list(names_dict.values())),
        y=alt.Y('资产2:N', title='', sort=list(names_dict.values()))
    )

    # 创建热力图主体
    heatmap = base.mark_rect().encode(
        color=alt.Color(
            '相关系数:Q',
            # scale=alt.Scale(
            #     domain=[-1, 0, 1],
            #     range=['#c41e3a', '#white', '#1e90ff'],
            #     scheme='redblue'
            # ),
            legend=alt.Legend(format='.2f')
        ),
        opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        tooltip=[
            alt.Tooltip('资产1:N', title='资产1'),
            alt.Tooltip('资产2:N', title='资产2'),
            alt.Tooltip('相关系数:Q', title='相关系数', format='.2f')
        ]
    )

    # 添加相关系数文本标签
    text = base.mark_text(baseline='middle').encode(
        text=alt.Text('相关系数:Q', format='.2f'),
        color=alt.condition(
            abs(alt.datum.相关系数) > 0.5,
            alt.value('white'),
            alt.value('black')
        )
    )

    # 组合图层并设置属性
    chart = (heatmap + text).properties(
        title=f"指数与主要大类资产相关系数热力图",
        width=600,
        height=600
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        anchor='middle'
    ).add_params(selection)

    return chart

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
            # 获取当前指数的基金数据
            fund_df = tracking_funds_data[index_code].copy()
            
            # 删除第一列（通常是索引列）
            if not fund_df.empty:
                fund_df = fund_df.iloc[:, 1:]
            
            # 使用正则表达式筛选基金代码，只保留以OF、SZ、SH、HK结尾的基金
            if '基金代码' in fund_df.columns:
                fund_df = fund_df[fund_df['基金代码'].astype(str).str.match(r'.*\.(OF|SZ|SH|HK)$')]
            
            # 只显示前30大基金
            fund_df_top30 = fund_df.head(30)
            
            # 显示处理后的数据
            st.dataframe(fund_df_top30, use_container_width=True)
            
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
                    st.dataframe(data_dict[index_code], use_container_width=True)

# ————————————————————————————————————————————主程序模块——————————————————————————————————————————————

def main(index_codes):
    try:
        # 在主程序头部执行一次万德终端启动
        w.start()

        st.subheader("指数基本信息对比")
        if len(index_codes) > 8:
            st.error("最多只能选择8个指数进行对比")
            st.stop()
        else:
            # 获取成分股数据
            index_component_data = get_index_component_data(index_codes)
            # 显示基本信息表格
            show_information(index_codes)
        
        # 1.显示指数价格走势图
        st.divider()
        st.subheader("指数价格走势和累积收益走势")
        show_plot(index_codes)

        # 2.显示指数估值分位对比
        st.divider()
        st.subheader("指数收益和估值情况")
        show_valuation_chart(index_codes)

        # 2.绘制收益风险表格
        st.divider()
        st.subheader("指数收益风险情况对比")
        show_risk_table(index_codes)

        # 4.显示指数前50支成分股市值大小
        st.divider()
        st.subheader("指数成分股市值分布情况")
        show_bar(index_component_data)
       
        # 5.统计并显示每个指数的行业分布情况
        st.divider()
        st.subheader("指数行业分布情况对比")
        show_chart(index_codes, index_component_data)

        # 6.按照指数权重排序，获取前20个成分股，分别获取其近三个月股价信息并显示
        st.divider()
        st.subheader("指数前20大成分股对比")
        show_table(index_component_data)

        # 7.显示指数风险指标雷达图
        st.divider()
        st.subheader("指数风险指标雷达图")
        show_radar_graph(index_codes)

        # 8.显示指数年度收益对比
        st.divider()
        st.subheader("指数年度收益对比")
        show_year_return(index_codes)

        # 3.显示指数大类资产相关性热力图
        st.divider()
        st.altair_chart(show_assets_heatmap(index_codes), use_container_width=True)

        # 9.显示跟踪各指数的基金竞争格局
        st.divider()
        st.subheader("跟踪各指数的基金竞争格局")
        show_tracking_funds(index_codes)

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

# 侧边栏UI
with st.sidebar:
    st.markdown("### 指数对比分析工具：")
    st.markdown("可从指数基本信息、成分股信息、行业分布、近期表现等多维度进行对比分析")
    
    with st.form(key="index_form"):
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
        st.session_state.start_date = st.date_input("起始日期", value=FIVE_YEARS_AGO, min_value=datetime.date(2000, 1, 1)).strftime('%Y-%m-%d')
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
if st.session_state.run_analysis:
    main(st.session_state.index_codes)
else:
    st.info("请在左侧侧边栏输入您要分析的指数代码。")
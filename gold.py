import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import winsound
import time                    # 新增
refresh_interval = 3           # 新增：每3秒刷新一次



# -------------------- 全局设置 --------------------
st.set_page_config(page_title="📊 实时行情监控", layout="wide")

# 监控商品（新浪财经代码）
COMMODITIES = {
    "黄金": "hf_XAU",    # 国际黄金
    "白银": "hf_XAG",    # 国际白银
    "原油": "hf_CL",     # 美原油
    "铜": "hf_CAD",      # 伦铜
}

# 初始化 session_state
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["时间"] + list(COMMODITIES.keys()))
if "alert_triggered" not in st.session_state:
    st.session_state.alert_triggered = {k: False for k in COMMODITIES.keys()}


# -------------------- 获取实时价格 --------------------
def get_price_sina(symbol):
    """
    从新浪财经接口获取实时行情（万能版）
    返回：当前价, 涨跌幅(%)
    """
    url = f"https://hq.sinajs.cn/list={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn"
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.encoding = 'gbk'
        text = r.text.strip()
        if '=' not in text:
            return None, None
        data = text.split('=', 1)[1].strip('";\n').split(',')
        if len(data) < 3 or data[0] == '':
            return None, None
        price = float(data[0])          # 当前价
        change_pct = float(data[2])     # 涨跌幅
        return price, change_pct
    except Exception as e:
        st.sidebar.error(f"{symbol} 获取失败")
        return None, None

# -------------------- 汇总所有价格 --------------------
def fetch_all_prices():
    prices = {}
    changes = {}
    for name, symbol in COMMODITIES.items():
        price, change = get_price_sina(symbol)
        prices[name] = price
        changes[name] = change
    return prices, changes


# -------------------- 报警功能 --------------------
def trigger_alert(name, price, target):
    """触发声音或微信推送"""
    st.warning(f"⚠️ {name} 当前价 {price:.2f} 已触发报警阈值 {target}")
    winsound.Beep(1000, 800)  # 声音提示


# -------------------- 主程序 --------------------
st.title("📈 实时商品行情监控（新浪财经接口）")
st.markdown("数据源：新浪财经（国内可访问）")

# 报警设置
st.sidebar.header("⚙️ 报警设置")
price_alerts = {}
for name in COMMODITIES.keys():
    price_alerts[name] = st.sidebar.number_input(f"{name} 报警价", value=0.0, format="%.2f")

# 获取行情
prices, changes = fetch_all_prices()

# 更新时间
now = datetime.now().strftime("%H:%M:%S")

# 写入历史
row = {"时间": now}
row.update(prices)
st.session_state.history = pd.concat(
    [st.session_state.history, pd.DataFrame([row])], ignore_index=True
)

# -------------------- 表格展示 --------------------
st.subheader("💰 实时价格表")
table_data = []
for name in COMMODITIES.keys():
    price = prices.get(name)
    change = changes.get(name)
    alert_price = price_alerts[name]

    # 判断涨跌色
    color = "red" if change and change > 0 else "green"
    price_text = f"<span style='color:{color}'>{price if price else '-'}</span>"

    table_data.append(
        {
            "品种": name,
            "价格": price_text,
            "涨跌幅(%)": f"<span style='color:{color}'>{change if change else '-'}</span>",
            "报警价": alert_price if alert_price > 0 else "-",
        }
    )

# 显示 HTML 表格
df_display = pd.DataFrame(table_data)
st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

# -------------------- 绘制趋势图 --------------------
hist = st.session_state.history.copy()
for col in COMMODITIES.keys():
    hist[col] = pd.to_numeric(hist[col], errors="coerce")

fig, ax = plt.subplots(figsize=(10, 4))
for col in COMMODITIES.keys():
    ax.plot(hist["时间"], hist[col], label=col)
ax.legend()
ax.set_title("实时价格趋势")
ax.set_xlabel("时间")
ax.set_ylabel("价格")
st.pyplot(fig)

# -------------------- 报警检测 --------------------
for name in COMMODITIES.keys():
    current_price = prices.get(name)
    alert_target = price_alerts[name]
    if current_price and alert_target > 0:
        if current_price >= alert_target and not st.session_state.alert_triggered[name]:
            trigger_alert(name, current_price, alert_target)
            st.session_state.alert_triggered[name] = True
        elif current_price < alert_target:
            st.session_state.alert_triggered[name] = False

# ==================== 实时刷新倒计时 + 自动刷新 ====================
st.markdown("---")
st.caption(f"数据更新时间：{now}　|　每 {refresh_interval} 秒自动刷新一次")

# 倒计时（不闪屏）
placeholder = st.empty()
for i in range(refresh_interval, 0, -1):
    placeholder.info(f"实时监控中... {i} 秒后刷新")
    time.sleep(1)
placeholder.empty()

# 强制刷新页面
st.rerun()
# ==================================================================
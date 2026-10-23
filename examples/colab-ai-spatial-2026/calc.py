import streamlit as st

st.title("計算アプリ")

# 输入两个数字，再从侧栏选择计算方式
a = st.number_input("数字１")
b = st.number_input("数字２")
method = st.sidebar.selectbox("計算方法", ["足し算", "掛け算"])

# 根据选择执行对应的计算
if method == "足し算":
    c = a + b
elif method == "掛け算":
    c = a * b

# f 字符串会把计算方式填入标题
st.title(f"{method}結果")
st.text(c)

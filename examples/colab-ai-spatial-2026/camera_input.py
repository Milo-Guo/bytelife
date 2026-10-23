import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO

st.set_page_config(
    page_title="カメラによる物体検知",
    layout="centered"
)

st.title("カメラによる物体検知")

model = YOLO('yolov8s.pt')

# Input
camera_img = st.camera_input(label='インカメラ画像')

# Process
if camera_img is not None:
    bytes_data = camera_img.getvalue()
    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    if cv2_img is None:
        st.error("画像を読み込めませんでした。もう一度撮影してください。")
        st.stop()

    results = model(cv2_img, conf=0.4)
    output_img = results[0].plot(labels=True, conf=True)
    # OpenCV 和网页使用的颜色顺序不同，显示前需要转换
    output_img = cv2.cvtColor(output_img, cv2.COLOR_BGR2RGB)

    # Output
    st.image(output_img, caption='出力画像')

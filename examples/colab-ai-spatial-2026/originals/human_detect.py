import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import tempfile
import subprocess

st.set_page_config(
    page_title="カメラによる人物検出",
    layout="centered"
)

st.title("カメラによる人物検出")


model = YOLO('yolov8s.pt')

# Input
upload_file = st.file_uploader("動画アップロード", type='mp4')

# Process
if upload_file is not None:

    # 処理中表示
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    status_text.text("現在、処理動作中…")

    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(upload_file.read())

    cap = cv2.VideoCapture(temp_file.name)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    writer = cv2.VideoWriter('./object_detection_app_results.mp4',
                            cv2.VideoWriter_fourcc(*'mp4v',),fps,
                            frameSize=(int(width),int(height)))
    if not writer.isOpened():
        status_text.empty()
        st.error("VideoWriterのオープンに失敗しました")
        cap.release()
        writer.release()
        st.stop()

    num = 0
    while cap.isOpened():
        ret, img = cap.read()

        if ret:
            results = model(img,conf=0.4 )
            img = results[0].plot(labels=False,conf=True)
            writer.write(img)

            progress = min(int((num + 1) / count * 100), 100)
            progress_bar.progress(progress)            
        else:
            break

        num = num + 1

    cap.release()
    writer.release() 
    progress_bar.empty()

    # ブラウザ再生用にH.264へ変換
    status_text.empty()
    status_text.text(f'動画表示の準備をしています…')
    input_video = './object_detection_app_results.mp4'
    output_video = './object_detection_app_results_h264.mp4'

    subprocess.run([
        'ffmpeg', '-y',
        '-i', input_video,
        '-vcodec', 'libx264',
        '-acodec', 'aac',
        '-pix_fmt', 'yuv420p',
        output_video
    ], check=True)

    status_text.empty()

# Output
    st.text(f'検出結果の動画を表示しました。')
    st.video(
        './object_detection_app_results_h264.mp4',
        autoplay=True
    )

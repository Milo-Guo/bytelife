import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import tempfile
import subprocess
import pandas as pd

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

    # 写入后关闭临时文件，确保 OpenCV 能读到完整的视频
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_file.write(upload_file.getvalue())

    cap = cv2.VideoCapture(temp_file.name)
    if not cap.isOpened():
        status_text.empty()
        st.error("動画を開けませんでした。MP4ファイルを確認してください。")
        cap.release()
        st.stop()

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    if width <= 0 or height <= 0 or count <= 0 or fps <= 0:
        status_text.empty()
        st.error("動画のサイズ・フレーム数・FPSを取得できませんでした。")
        cap.release()
        st.stop()

    writer = cv2.VideoWriter('./object_detection_app_results.mp4',
                            cv2.VideoWriter_fourcc(*'mp4v',), fps,
                            frameSize=(int(width), int(height)))
    if not writer.isOpened():
        status_text.empty()
        st.error("VideoWriterのオープンに失敗しました")
        cap.release()
        writer.release()
        st.stop()

    num = 0
    nums = []
    persons = []
    while cap.isOpened():
        ret, img = cap.read()

        if ret:
            # YOLO 的类别 0 是人，限定类别后只统计人数
            results = model(img, conf=0.5, classes=[0])
            categories = results[0].boxes.cls
            person_num = len(categories)
            nums.append(num)
            persons.append(person_num)

            img = results[0].plot(labels=False, conf=True)
            writer.write(img)

            progress = min(int((num + 1) / count * 100), 100)
            progress_bar.progress(progress)
        else:
            break

        num = num + 1

    cap.release()
    writer.release()
    progress_bar.empty()

    if not nums:
        status_text.empty()
        st.error("動画からフレームを読み込めませんでした。")
        st.stop()

    # 将帧序号换算成秒，得到每个时刻对应的人数
    person_data = pd.DataFrame({'フレーム': nums, '人数': persons})
    person_data['時間(秒)'] = person_data['フレーム'] / fps
    person_data = person_data[['時間(秒)', '人数']]

    # ブラウザ再生用にH.264へ変換
    status_text.empty()
    status_text.text('動画表示の準備をしています…')
    input_video = './object_detection_app_results.mp4'
    output_video = './object_detection_app_results_h264.mp4'

    try:
        subprocess.run([
            'ffmpeg', '-y',
            '-i', input_video,
            '-vcodec', 'libx264',
            '-acodec', 'aac',
            '-pix_fmt', 'yuv420p',
            output_video
        ], check=True)
    except FileNotFoundError:
        status_text.empty()
        st.error("ffmpegが見つかりません。Colabの環境を確認してください。")
        st.stop()
    except subprocess.CalledProcessError:
        status_text.empty()
        st.error("動画の変換に失敗しました。Colabのログを確認してください。")
        st.stop()

    status_text.empty()

    # Output
    st.text('検出結果の動画を表示しました。')
    st.video(
        output_video,
        autoplay=True
    )
    st.text('以下は検出された人数の時系列グラフです。')
    st.line_chart(person_data, x="時間(秒)", y="人数")

import streamlit as st
import numpy as np
import trimesh
import plotly.graph_objects as go
import tempfile
import os


# ============================================================
# Streamlit設定
# ============================================================

st.set_page_config(
    page_title="3D点群・床面検出",
    layout="wide"
)

st.title("3D点群表示・床面検出")


# ============================================================
# ボタンのデザイン
# ============================================================

st.markdown(
    """
    <style>

    /* 通常のボタン */
    div.stButton > button {
        background-color: #1f4e79;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        padding: 0.6em 1em;
        min-height: 50px;
    }

    /* マウスを乗せたとき */
    div.stButton > button:hover {
        background-color: #163a5c;
        color: white;
        border: none;
    }

    /* ボタンを押している間 */
    div.stButton > button:active {
        background-color: #102a43;
        color: white;
    }

    /* 無効化されたボタン */
    div.stButton > button:disabled {
        background-color: #b0b0b0;
        color: #eeeeee;
        border: none;
        cursor: not-allowed;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# Session State
# ============================================================

if "step" not in st.session_state:
    st.session_state.step = 1

if "display_points" not in st.session_state:
    st.session_state.display_points = None

if "display_colors" not in st.session_state:
    st.session_state.display_colors = None

if "floor_mask" not in st.session_state:
    st.session_state.floor_mask = None

if "floor_result" not in st.session_state:
    st.session_state.floor_result = None

if "floor_detected" not in st.session_state:
    st.session_state.floor_detected = False

if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None


# ============================================================
# ファイル変更時のSession Stateリセット
# ============================================================

def reset_session_state():

    st.session_state.step = 1

    st.session_state.display_points = None

    st.session_state.display_colors = None

    st.session_state.floor_mask = None

    st.session_state.floor_result = None

    st.session_state.floor_detected = False


# ============================================================
# Poisson Disk Sampling
# ============================================================

def poisson_disk_sampling(points, target_count):

    n = len(points)

    if target_count >= n:
        return np.arange(n)

    if target_count <= 0:
        return np.array([], dtype=int)

    pmin = points.min(axis=0)
    pmax = points.max(axis=0)

    extent = pmax - pmin

    volume = np.prod(extent)

    if volume <= 0:

        return np.random.choice(
            n,
            size=target_count,
            replace=False
        )

    # --------------------------------------------------------
    # サンプリング半径を推定
    # --------------------------------------------------------

    radius = (
        volume / target_count
    ) ** (1.0 / 3.0)

    radius *= 0.8

    if radius <= 0:
        radius = 1e-6

    # --------------------------------------------------------
    # 空間ハッシュ
    # --------------------------------------------------------

    cell_size = radius

    grid = {}

    def grid_coord(p):

        return tuple(
            np.floor(
                (p - pmin) / cell_size
            ).astype(int)
        )

    def is_far_enough(p):

        gc = grid_coord(p)

        for dx in [-1, 0, 1]:

            for dy in [-1, 0, 1]:

                for dz in [-1, 0, 1]:

                    key = (
                        gc[0] + dx,
                        gc[1] + dy,
                        gc[2] + dz
                    )

                    if key not in grid:
                        continue

                    for idx in grid[key]:

                        q = points[idx]

                        distance_sq = np.sum(
                            (p - q) ** 2
                        )

                        if distance_sq < radius ** 2:

                            return False

        return True

    # --------------------------------------------------------
    # ランダムな順番で探索
    # --------------------------------------------------------

    order = np.random.permutation(n)

    selected = []

    max_attempts = target_count * 30

    attempts = 0

    for idx in order:

        if len(selected) >= target_count:
            break

        attempts += 1

        if attempts > max_attempts:
            break

        p = points[idx]

        if is_far_enough(p):

            selected.append(idx)

            gc = grid_coord(p)

            if gc not in grid:
                grid[gc] = []

            grid[gc].append(idx)

    # --------------------------------------------------------
    # PDSだけで目標点数に届かなかった場合
    # --------------------------------------------------------

    if len(selected) < target_count:

        selected_set = set(selected)

        remaining = [
            i
            for i in range(n)
            if i not in selected_set
        ]

        needed = target_count - len(selected)

        if len(remaining) > 0:

            additional = np.random.choice(
                remaining,
                size=min(
                    needed,
                    len(remaining)
                ),
                replace=False
            )

            selected.extend(
                additional.tolist()
            )

    return np.array(
        selected,
        dtype=int
    )


# ============================================================
# RANSACによる床面検出
#
# Scaniverseの座標系：
#
#     +Z = 上
#
# 床面の法線：
#
#     (0, 0, 1)
# ============================================================

def detect_floor_ransac(
    points,
    iterations=1000,
    distance_threshold=0.01,
    angle_threshold_deg=10.0,
    min_inliers=100
):

    if len(points) < 3:
        return None

    # --------------------------------------------------------
    # 床面の基準法線
    # --------------------------------------------------------

    reference_normal = np.array(
        [0.0, 0.0, 1.0]
    )

    # --------------------------------------------------------
    # 許容角度
    # --------------------------------------------------------

    angle_threshold = np.deg2rad(
        angle_threshold_deg
    )

    cos_threshold = np.cos(
        angle_threshold
    )

    best_count = 0

    best_inliers = None

    best_plane = None

    n = len(points)

    # ========================================================
    # RANSAC
    # ========================================================

    for _ in range(iterations):

        # ----------------------------------------------------
        # ランダムに3点選択
        # ----------------------------------------------------

        ids = np.random.choice(
            n,
            size=3,
            replace=False
        )

        p1 = points[ids[0]]

        p2 = points[ids[1]]

        p3 = points[ids[2]]

        # ----------------------------------------------------
        # 2本のベクトル
        # ----------------------------------------------------

        v1 = p2 - p1

        v2 = p3 - p1

        # ----------------------------------------------------
        # 法線
        # ----------------------------------------------------

        normal = np.cross(
            v1,
            v2
        )

        norm = np.linalg.norm(
            normal
        )

        if norm < 1e-8:
            continue

        normal = normal / norm

        # ----------------------------------------------------
        # 法線を +Z方向に統一
        # ----------------------------------------------------

        if normal[2] < 0:

            normal = -normal

        # ----------------------------------------------------
        # +Z軸との角度
        # ----------------------------------------------------

        cos_angle = np.dot(
            normal,
            reference_normal
        )

        # ----------------------------------------------------
        # 許容角度外なら除外
        # ----------------------------------------------------

        if cos_angle < cos_threshold:

            continue

        # ----------------------------------------------------
        # 平面方程式
        #
        # ax + by + cz + d = 0
        # ----------------------------------------------------

        d = -np.dot(
            normal,
            p1
        )

        # ----------------------------------------------------
        # 全点との距離
        # ----------------------------------------------------

        distances = np.abs(
            points @ normal + d
        )

        # ----------------------------------------------------
        # インライア
        # ----------------------------------------------------

        inliers = (
            distances
            <=
            distance_threshold
        )

        count = np.sum(
            inliers
        )

        # ----------------------------------------------------
        # 最大インライア数の平面を保存
        # ----------------------------------------------------

        if count > best_count:

            best_count = count

            best_inliers = inliers

            best_plane = (
                normal.copy(),
                d
            )

    # ========================================================
    # RANSAC失敗
    # ========================================================

    if best_plane is None:

        return None

    if best_count < min_inliers:

        return None

    # ========================================================
    # SVDによる平面精密化
    # ========================================================

    inlier_points = points[
        best_inliers
    ]

    center = np.mean(
        inlier_points,
        axis=0
    )

    centered = (
        inlier_points - center
    )

    try:

        _, _, vh = np.linalg.svd(
            centered,
            full_matrices=False
        )

        refined_normal = vh[-1]

        refined_normal = (
            refined_normal
            /
            np.linalg.norm(
                refined_normal
            )
        )

        # ----------------------------------------------------
        # 法線を +Z方向に統一
        # ----------------------------------------------------

        if refined_normal[2] < 0:

            refined_normal = -refined_normal

    except Exception:

        refined_normal = best_plane[0]

    # ========================================================
    # +Z軸との角度
    # ========================================================

    cos_angle = np.clip(
        np.dot(
            refined_normal,
            reference_normal
        ),
        -1.0,
        1.0
    )

    angle_deg = np.degrees(
        np.arccos(
            cos_angle
        )
    )

    # ========================================================
    # 平面方程式
    # ========================================================

    d = -np.dot(
        refined_normal,
        center
    )

    # ========================================================
    # 最終的な床面インライア
    # ========================================================

    distances = np.abs(
        points @ refined_normal + d
    )

    final_mask = (
        distances
        <=
        distance_threshold
    )

    return {

        "normal": refined_normal,

        "d": d,

        "mask": final_mask,

        "count": int(
            np.sum(final_mask)
        ),

        "center": center,

        "angle_deg": angle_deg
    }


# ============================================================
# Plotly 3D表示
#
# point_size：
# Web画面から変更可能
#
# Scaniverse：
#     +Z = 上
# ============================================================

def create_figure(
    points,
    colors,
    floor_mask=None,
    point_size=2
):

    display_colors = np.array(
        colors,
        copy=True
    )

    # ========================================================
    # 床面を赤色にする
    # ========================================================

    if floor_mask is not None:

        display_colors[
            floor_mask
        ] = [255, 0, 0]

    # ========================================================
    # RGB文字列
    # ========================================================

    rgb_strings = [

        f"rgb("
        f"{int(c[0])},"
        f"{int(c[1])},"
        f"{int(c[2])}"
        f")"

        for c in display_colors
    ]

    # ========================================================
    # 3D Scatter
    # ========================================================

    fig = go.Figure(

        data=[

            go.Scatter3d(

                x=points[:, 0],

                y=points[:, 1],

                z=points[:, 2],

                mode="markers",

                marker=dict(

                    size=point_size,

                    color=rgb_strings,

                    opacity=0.8
                )
            )
        ]
    )

    # ========================================================
    # 初期カメラ
    #
    # Z軸を上方向として表示
    #
    # eyeの距離を近くして約2倍ズーム
    # ========================================================

    camera = dict(

        eye=dict(

            x=-1.0,

            y=-1.0,

            z=0.6
        ),

        up=dict(

            x=0,

            y=0,

            z=1
        ),

        center=dict(

            x=0,

            y=0,

            z=0
        )
    )

    # ========================================================
    # レイアウト
    # ========================================================

    fig.update_layout(

        scene=dict(

            xaxis_title="X",

            yaxis_title="Y",

            zaxis_title="Z",

            aspectmode="data",

            camera=camera
        ),

        height=700,

        margin=dict(

            l=0,

            r=0,

            b=0,

            t=0
        )
    )

    return fig


# ============================================================
# PLYファイル選択
# ============================================================

uploaded_file = st.file_uploader(
    "PLYファイルを選択してください",
    type=["ply"]
)


# ============================================================
# PLYファイル選択後
# ============================================================

if uploaded_file is not None:

    # ========================================================
    # ファイル変更を検出
    # ========================================================

    file_id = (
        uploaded_file.name,
        uploaded_file.size
    )

    if (
        st.session_state.uploaded_file_id
        !=
        file_id
    ):

        reset_session_state()

        st.session_state.uploaded_file_id = file_id

    # ========================================================
    # 一時ファイル
    # ========================================================

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".ply"
    ) as tmp:

        tmp.write(
            uploaded_file.getbuffer()
        )

        tmp_path = tmp.name

    try:

        # ====================================================
        # PLY読み込み
        # ====================================================

        cloud = trimesh.load(
            tmp_path,
            process=False
        )

        # ====================================================
        # PointCloud
        # ====================================================

        if isinstance(
            cloud,
            trimesh.points.PointCloud
        ):

            points = np.asarray(
                cloud.vertices
            )

            # ------------------------------------------------
            # RGB取得
            # ------------------------------------------------

            try:

                colors = np.asarray(
                    cloud.colors
                )

                if (
                    colors.ndim != 2
                    or
                    colors.shape[0]
                    !=
                    len(points)
                ):

                    raise ValueError

                colors = colors[:, :3]

            except Exception:

                # ------------------------------------------------
                # RGBがない場合
                # ------------------------------------------------

                colors = np.zeros(
                    (len(points), 3),
                    dtype=np.uint8
                )

                z = points[:, 2]

                zmin = z.min()

                zmax = z.max()

                if zmax > zmin:

                    normalized = (
                        (z - zmin)
                        /
                        (zmax - zmin)
                    )

                    colors[:, 0] = (
                        normalized * 255
                    ).astype(
                        np.uint8
                    )

                    colors[:, 1] = (
                        (1.0 - normalized)
                        * 255
                    ).astype(
                        np.uint8
                    )

                    colors[:, 2] = 100

        # ====================================================
        # Trimesh
        # ====================================================

        elif isinstance(
            cloud,
            trimesh.Trimesh
        ):

            points = np.asarray(
                cloud.vertices
            )

            try:

                colors = np.asarray(
                    cloud.visual
                    .vertex_colors
                )[:, :3]

            except Exception:

                colors = np.ones(
                    (len(points), 3),
                    dtype=np.uint8
                ) * 180

        # ====================================================
        # 読み込み失敗
        # ====================================================

        else:

            st.error(
                "PLYファイルから点群を読み込めませんでした。"
            )

            st.stop()

        # ====================================================
        # 読み込み完了
        # ====================================================

        st.success(
            f"PLY読み込み完了："
            f"{len(points):,} 点"
        )

        # ====================================================
        # ① 3D点群表示設定
        # ====================================================

        st.subheader(
            "① 3D点群表示設定"
        )

        # ----------------------------------------------------
        # 表示点数
        #
        # デフォルト：10,000点
        # ----------------------------------------------------

        max_points = len(points)

        default_points = min(
            10000,
            max_points
        )

        display_count = st.number_input(
            "表示する点数",
            min_value=1000,
            max_value=max_points,
            value=default_points,
            step=1000,
            key="display_count_input"
        )

        # ----------------------------------------------------
        # 点の大きさ
        # ----------------------------------------------------

        point_size = st.slider(
            "点の大きさ",
            min_value=1,
            max_value=8,
            value=2,
            step=1,
            help="3D点群を画面上に表示するときの点の大きさです。",
            key="point_size_slider"
        )

        # ----------------------------------------------------
        # ① 3D点群を表示
        #
        # 最初だけ必須。
        # 一度①を実行した後は、何度でも押せる。
        # ----------------------------------------------------

        display_button = st.button(
            "① 3D点群を表示",
            use_container_width=True,
            disabled=(
                st.session_state.display_points is None
                and
                st.session_state.step != 1
            ),
            key="display_button"
        )

        # ====================================================
        # ② 床面検出設定
        # ====================================================

        st.subheader(
            "② 床面検出設定"
        )

        col_a, col_b, col_c = st.columns(3)

        # ----------------------------------------------------
        # RANSAC反復回数
        # ----------------------------------------------------

        with col_a:

            ransac_iterations = st.number_input(
                "RANSAC反復回数",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100,
                key="ransac_iterations_input"
            )

        # ----------------------------------------------------
        # 平面距離しきい値
        # ----------------------------------------------------

        with col_b:

            distance_threshold = st.number_input(
                "平面距離しきい値",
                min_value=0.001,
                max_value=0.1,
                value=0.01,
                step=0.001,
                format="%.3f",
                key="distance_threshold_input"
            )

        # ----------------------------------------------------
        # Z軸からの許容角度
        # ----------------------------------------------------

        with col_c:

            angle_threshold = st.number_input(
                "Z軸からの許容角度（度）",
                min_value=1.0,
                max_value=45.0,
                value=10.0,
                step=1.0,
                key="angle_threshold_input"
            )

        # ----------------------------------------------------
        # ② 床を検出して赤色表示
        #
        # ①を一度も実行していない場合は押せない。
        # ①実行後は何度でも押せる。
        # ----------------------------------------------------

        floor_button = st.button(
            "② 床を検出して赤色表示",
            use_container_width=True,
            disabled=(
                st.session_state.display_points is None
            ),
            key="floor_button"
        )

        # ====================================================
        # 現在の状態表示
        # ====================================================

        if st.session_state.display_points is None:

            st.info(
                "まず①「3D点群を表示」を実行してください。"
            )

        else:

            st.info(
                "①で点数・点の大きさを変更して再表示できます。"
                " ②では現在表示中の点群に対して床面検出を行います。"
            )

        # ====================================================
        # ① 3D点群を表示
        # ====================================================

        if display_button:

            with st.spinner(
                "PDSによるサンプリングを実行しています..."
            ):

                # ------------------------------------------------
                # PDS
                # ------------------------------------------------

                indices = poisson_disk_sampling(
                    points,
                    int(display_count)
                )

                # ------------------------------------------------
                # 表示点群
                # ------------------------------------------------

                display_points = points[
                    indices
                ]

                display_colors = colors[
                    indices
                ]

                # ------------------------------------------------
                # Session Stateに保存
                # ------------------------------------------------

                st.session_state.display_points = (
                    display_points
                )

                st.session_state.display_colors = (
                    display_colors
                )

                # ------------------------------------------------
                # ①を再実行した場合も、
                # 以前の床面検出結果はリセット
                # ------------------------------------------------

                st.session_state.floor_mask = None

                st.session_state.floor_result = None

                st.session_state.floor_detected = False

                # ------------------------------------------------
                # 一度①を実行したら、
                # 以後①②の両方を使用可能
                # ------------------------------------------------

                st.session_state.step = 2

            st.success(
                f"PDS完了："
                f"{len(display_points):,} 点"
            )

            st.rerun()

        # ====================================================
        # ② 床面検出
        # ====================================================

        if floor_button:

            with st.spinner(
                "RANSACによる床面検出を実行しています..."
            ):

                # ------------------------------------------------
                # ①で作成した点群をそのまま使用
                #
                # ここでは再サンプリングしない
                # ------------------------------------------------

                display_points = (
                    st.session_state.display_points
                )

                # ------------------------------------------------
                # RANSAC
                # ------------------------------------------------

                result = detect_floor_ransac(
                    display_points,
                    iterations=int(
                        ransac_iterations
                    ),
                    distance_threshold=float(
                        distance_threshold
                    ),
                    angle_threshold_deg=float(
                        angle_threshold
                    )
                )

                # ------------------------------------------------
                # 検出成功
                # ------------------------------------------------

                if result is not None:

                    st.session_state.floor_mask = (
                        result["mask"]
                    )

                    st.session_state.floor_result = (
                        result
                    )

                    st.session_state.floor_detected = True

                    st.success(
                        "床面を検出しました。"
                    )

                # ------------------------------------------------
                # 検出失敗
                # ------------------------------------------------

                else:

                    st.session_state.floor_mask = None

                    st.session_state.floor_result = None

                    st.session_state.floor_detected = False

                    st.error(
                        "床面を検出できませんでした。"
                    )

                # ------------------------------------------------
                # 重要：
                # ここではstepを1に戻さない
                #
                # ①②ともに引き続き使用可能
                # ------------------------------------------------

            st.rerun()

    finally:

        # ========================================================
        # 一時ファイル削除
        # ========================================================

        if os.path.exists(tmp_path):

            os.remove(tmp_path)


# ============================================================
# 3D点群表示
# ============================================================

if st.session_state.display_points is not None:

    st.subheader(
        "3D点群"
    )

    points_to_display = (
        st.session_state.display_points
    )

    colors_to_display = (
        st.session_state.display_colors
    )

    # --------------------------------------------------------
    # 床面検出済み
    # --------------------------------------------------------

    if (
        st.session_state.floor_detected
        and
        st.session_state.floor_mask is not None
    ):

        fig = create_figure(
            points_to_display,
            colors_to_display,
            st.session_state.floor_mask,
            point_size
        )

    # --------------------------------------------------------
    # 通常表示
    # --------------------------------------------------------

    else:

        fig = create_figure(
            points_to_display,
            colors_to_display,
            point_size=point_size
        )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
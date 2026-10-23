"""验证复现包：只运行文件检查与点云数值函数，不启动网页、不下载模型。"""
from pathlib import Path
import ast
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parent


def load_point_functions():
    """仅取纯数值函数，避免导入原文件时执行 Streamlit 界面。"""
    tree = ast.parse((ROOT / 'pointcloud.py').read_text(encoding='utf-8-sig'))
    names = {'poisson_disk_sampling', 'detect_floor_ransac'}
    module = ast.Module(body=[node for node in tree.body
                             if isinstance(node, ast.FunctionDef) and node.name in names],
                        type_ignores=[])
    namespace = {'np': np}
    exec(compile(module, 'pointcloud-functions', 'exec'), namespace)
    return namespace['poisson_disk_sampling'], namespace['detect_floor_ransac']


def check_files():
    for line in (ROOT / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, relative = line.split('  ', 1)
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise AssertionError(f'文件哈希不同：{relative}')
    for path in ROOT.rglob('*.py'):
        compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')
    notebooks = list(ROOT.rglob('*.ipynb'))
    assert len(notebooks) == 8, '应有四份复现笔记本、四份清理后的原版'
    for path in notebooks:
        notebook = json.loads(path.read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            assert cell.get('outputs', []) == [], f'笔记本存在输出：{path.name}'
            assert cell.get('execution_count') is None, f'笔记本存在执行记录：{path.name}'
            text = ''.join(cell.get('source', []))
            # 原版认证调用只允许空字符串；复现版使用启动器隐藏输入
            for line in text.splitlines():
                if 'ngrok.set_auth_token(' in line:
                    assert line.lstrip('# ').strip() == 'ngrok.set_auth_token("")'
    print('文件完整性、Python 语法、笔记本清理检查通过。')


def check_sampling_and_plane():
    sample, detect = load_point_functions()
    np.random.seed(42)
    cloud = np.random.uniform(-2, 2, size=(1000, 3))
    ids = sample(cloud, 100)
    assert len(ids) == 100 and len(set(ids.tolist())) == 100
    assert np.all((ids >= 0) & (ids < len(cloud)))
    assert len(sample(cloud, 0)) == 0
    assert np.array_equal(sample(cloud, 1000), np.arange(1000))
    flat = np.column_stack([np.random.random((200, 2)), np.zeros(200)])
    assert len(np.unique(sample(flat, 80))) == 80
    assert detect(np.zeros((2, 3))) is None

    # 合成地面带少量测量噪声，另加竖直墙面和离散噪声，验证角度过滤与内点召回
    xy = np.random.uniform(-3, 3, size=(500, 2))
    floor = np.column_stack([xy, np.random.normal(0, 0.001, size=500)])
    wall = np.column_stack([np.full(250, 4.0), np.random.uniform(-3, 3, 250),
                            np.random.uniform(0.2, 3, 250)])
    noise = np.random.uniform(-3, 3, size=(100, 3))
    points = np.vstack([floor, wall, noise])
    result = detect(points, iterations=500, distance_threshold=0.01)
    assert result is not None and result['angle_deg'] < 1
    recall = np.mean(result['mask'][:500])
    precision = np.sum(result['mask'][:500]) / result['count']
    assert recall >= 0.95 and precision >= 0.9
    print(f'采样边界、合成平面检查通过：召回 {recall:.3f}，精确率 {precision:.3f}。')

    path = ROOT / 'building1_garden.ply'
    with path.open('rb') as stream:
        header = []
        while True:
            line = stream.readline()
            if not line:
                raise ValueError('PLY 文件头不完整')
            header.append(line.decode('ascii').strip())
            if line.strip() == b'end_header':
                break
        assert 'format binary_little_endian 1.0' in header
        assert 'element vertex 651990' in header
        expected_properties = ['property float x', 'property float y', 'property float z',
                               'property uchar red', 'property uchar green', 'property uchar blue']
        assert [line for line in header if line.startswith('property ')] == expected_properties
        dtype = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'),
                          ('r', 'u1'), ('g', 'u1'), ('b', 'u1')])
        payload = stream.read()
    assert len(payload) == 651990 * dtype.itemsize
    records = np.frombuffer(payload, dtype=dtype)
    vertices = np.column_stack([records['x'], records['y'], records['z']])
    assert np.isfinite(vertices).all()
    np.random.seed(42)
    # 这里用随机子集做快速数值检查；不是声称重跑了网页的十万点 PDS 参数实验
    subset = vertices[np.random.choice(len(vertices), 20000, replace=False)]
    result = detect(subset, iterations=1000, distance_threshold=0.01)
    assert result is not None and result['count'] >= 100
    assert result['angle_deg'] <= 10
    print(f'样例 PLY 格式与真实点云检查通过：{len(vertices):,} 点；'
          f'测试子集内点 {result["count"]}，角度 {result["angle_deg"]:.3f}°。')


if __name__ == '__main__':
    check_files()
    check_sampling_and_plane()
    print('全部检查通过。完整网页、相机权限和 YOLO/FFmpeg 请按 README 另行验证。')

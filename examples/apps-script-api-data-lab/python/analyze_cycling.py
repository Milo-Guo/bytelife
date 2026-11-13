"""读取课堂Excel，输出汇总JSON和4张图；不修改原Excel，不导出用户明细。"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def require(condition, message):
    """条件不成立就停止，避免带着不完整数据继续计算。"""
    if not condition:
        raise ValueError(message)


def analyze(path):
    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    rides = pd.read_excel(path, sheet_name='藤沢市のみ')
    rain = pd.read_excel(path, sheet_name='降水量')
    require(len(rides) == 4918, '本练习预期4918条利用记录，请检查文件和工作表')
    start = pd.to_datetime(rides['利用開始日時'], errors='raise')
    require(start.notna().all(), '利用開始日時存在空值')
    require(((start >= '2026-03-01') & (start < '2026-04-01')).all(), '利用记录不全属于2026年3月')
    rides['日付'] = start.dt.date
    rides['開始時'] = start.dt.hour
    require(set(rides['平日・休日']) == {'平日', '休日'}, '原始平日休日分类存在空值或其他值')
    require(rides.groupby('日付')['平日・休日'].nunique().eq(1).all(), '同一天存在冲突分类')
    require(rides['日付'].nunique() == 31, '本月存在无记录日期，不能仅从利用记录推算完整日数')

    # size数行，nunique数不同日期；使用源文件分类，不按祝日历重新分组。
    day = rides.groupby('平日・休日').agg(
        records=('NO.', 'size'), days=('日付', 'nunique')
    ).reindex(['平日', '休日'])
    day['average'] = day['records'] / day['days']
    hours = rides.groupby('開始時').size().reindex(range(24), fill_value=0)
    require(int(day['records'].sum()) == 4918, '日别汇总合计不一致')
    require(int(hours.sum()) == 4918, '小时汇总合计不一致')

    station_results = {}
    for label in ['貸出', '返却']:
        id_column = label + 'ステーション番号'
        name_column = label + 'ステーション'
        require(rides[id_column].notna().all(), '站点编号存在空值')
        require(rides.groupby(id_column)[name_column].nunique().eq(1).all(), '同一站点编号对应多个名称')
        stations = rides.groupby(id_column).agg(name=(name_column, 'first'), records=('NO.', 'size'))
        stations = stations.sort_values('records', ascending=False)
        stations['rank'] = stations['records'].rank(method='min', ascending=False).astype(int)
        require(int(stations['records'].sum()) == 4918, '站点汇总合计不一致')
        top = stations.loc[stations['rank'] <= 10].sort_values(['rank', 'name'])
        station_results[label] = {
            'distinct_stations': len(stations),
            'top4_records': int(stations.head(4)['records'].sum()),
            'top10_including_ties': [
                {'id': int(index), 'name': row['name'], 'records': int(row['records']), 'rank': int(row['rank'])}
                for index, row in top.iterrows()
            ]
        }

    rain['hour'] = pd.to_datetime(rain['年月日時'], errors='raise')
    rain = rain.loc[(rain['hour'] >= '2026-03-01') & (rain['hour'] < '2026-04-01')].copy()
    rain['mm'] = pd.to_numeric(rain['降水量(mm)'], errors='raise')
    grid = pd.date_range('2026-03-01', '2026-04-01', freq='h', inclusive='left')
    require(rain['hour'].is_unique, '降水时间有重复，合并会重复计算利用记录')
    require(pd.DatetimeIndex(rain['hour'].sort_values()).equals(grid), '降水数据没有覆盖完整744小时')
    require(rain['mm'].notna().all() and rain['mm'].ge(0).all(), '降水量存在空值或负数')
    counts = start.dt.floor('h').value_counts().rename_axis('hour').rename('records').reset_index()
    merged = rain[['hour', 'mm']].merge(counts, on='hour', how='left', validate='one_to_one')
    # 只把确实没有利用记录的小时填0，不把未知降水量当成0。
    merged['records'] = merged['records'].fillna(0).astype(int)
    merged['rain_group'] = merged['mm'].gt(0).map({False: '无降雨', True: '有降雨'})
    weather = merged.groupby('rain_group').agg(hours=('hour', 'size'), records=('records', 'sum'))
    weather = weather.reindex(['无降雨', '有降雨'])
    weather['average'] = weather['records'] / weather['hours']
    require(len(merged) == 744 and int(merged['records'].sum()) == 4918, '降水合并后的合计不一致')

    # 本文件的利用時間读取为datetime.time；转成字符串后按时长解析。
    duration = pd.to_timedelta(rides['利用時間'].astype(str), errors='raise')
    require(duration.notna().all() and duration.ge(pd.Timedelta(0)).all(), '利用时间存在缺失或负值')
    rides['利用分'] = duration.dt.total_seconds() / 60
    duration_hours = rides.groupby('開始時')['利用分'].agg(['size', 'mean', 'median']).reindex(range(24))
    weekday_order = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
    duration_days = rides.groupby('曜日')['利用分'].agg(['size', 'mean', 'median']).reindex(weekday_order)
    require(int(duration_days['size'].sum()) == 4918, '星期字段汇总合计不一致')

    result = {
        'source': path.name,
        'rows': len(rides),
        'month': '2026-03',
        'day_type': {name: {'records': int(row['records']), 'days': int(row['days']), 'average': float(row['average'])}
                     for name, row in day.iterrows()},
        'hour_counts': {str(hour): int(count) for hour, count in hours.items()},
        'stations': station_results,
        'rain': {name: {'hours': int(row['hours']), 'records': int(row['records']), 'average': float(row['average'])}
                 for name, row in weather.iterrows()},
        'total_hours': len(merged),
        'zero_usage_hours': int(merged['records'].eq(0).sum()),
        'duration_minutes': {
            'overall_mean': float(rides['利用分'].mean()),
            'overall_median': float(rides['利用分'].median()),
            'by_hour': {str(h): {'records': int(row['size']), 'mean': float(row['mean']), 'median': float(row['median'])}
                        for h, row in duration_hours.iterrows()},
            'by_weekday': {name: {'records': int(row['size']), 'mean': float(row['mean']), 'median': float(row['median'])}
                           for name, row in duration_days.iterrows()}
        },
        'source_sha256': before_hash
    }
    require(hashlib.sha256(path.read_bytes()).hexdigest() == before_hash, '原文件发生变化，请重新核对')
    return result


def draw_charts(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # Windows常见中日文字体。其他系统可安装Noto Sans CJK。
    for font_path in [Path('C:/Windows/Fonts/msyh.ttc'), Path('C:/Windows/Fonts/meiryo.ttc')]:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ['Microsoft YaHei', 'Noto Sans CJK SC', 'Meiryo', 'Noto Sans CJK JP']
    chosen = next((name for name in candidates if name in available), None)
    if chosen:
        plt.rcParams['font.family'] = chosen
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.size'] = 11

    plots = [
        ('day-type', ['平日', '休日'], [v['average'] for v in result['day_type'].values()], '平日与休日：每天平均利用次数', '次／天', 1),
        ('hour-counts', list(range(24)), list(result['hour_counts'].values()), '各开始时段的利用次数', '次', 0),
        ('rain', ['无降雨（0mm）', '有降雨（大于0mm）'], [v['average'] for v in result['rain'].values()], '降雨与每小时平均利用次数', '次／小时', 2),
        ('hour-duration', list(range(24)), [v['mean'] for v in result['duration_minutes']['by_hour'].values()], '各开始时段的每次平均利用时长', '分钟／次', 1)
    ]
    for name, labels, values, title, unit, digits in plots:
        fig, ax = plt.subplots(figsize=(10, 4.4), layout='constrained')
        positions = list(range(len(labels)))
        bars = ax.bar(positions, values, color='#246b8e', width=0.65, zorder=3)
        ax.set_xticks(positions, labels)
        ax.set_ylim(0, max(values) * 1.2)
        ax.set_title(title, pad=14)
        ax.set_ylabel(unit)
        if len(labels) == 24:
            ax.set_xlabel('利用开始时刻（0至23时）')
            ax.tick_params(axis='x', labelsize=9)
        ax.bar_label(bars, labels=[f'{value:.{digits}f}' for value in values], fontsize=8 if len(labels) == 24 else 13, padding=3)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=0.2, zorder=0)
        fig.savefig(output / (name + '.png'), dpi=160)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('excel', type=Path, help='课堂原始Excel的路径')
    parser.add_argument('--out', type=Path, default=Path('cycling_results'))
    args = parser.parse_args()
    if not args.excel.is_file():
        parser.error('找不到输入文件，请检查完整路径')
    result = analyze(args.excel)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    draw_charts(result, args.out)
    print('核对通过：4918条利用记录；744个小时；原Excel未修改。')
    print('结果目录：', args.out.resolve())


if __name__ == '__main__':
    main()

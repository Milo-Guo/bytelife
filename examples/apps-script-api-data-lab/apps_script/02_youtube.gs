// 先在 Apps Script 左侧「サービス」中添加 YouTube Data API v3。
function getChannelData2() {
  const channelIds = [
    'UC35OgsYuLuq8cNTAm_5GvWA',
    'UCl9sQNYTYHS-h_yrwBOQBIw'
  ];

  for (let i = 0; i < channelIds.length; i++) {
    // 同一次请求同时取名称与统计，便于看清它们属于同一个频道。
    const result = YouTube.Channels.list('snippet,statistics', { id: channelIds[i] });
    if (!result.items || result.items.length === 0) {
      Logger.log('没有找到频道：%s', channelIds[i]);
      continue;
    }

    const channel = result.items[0];
    const stats = channel.statistics;
    Logger.log(channel.snippet.title);
    Logger.log('登録者数：%s', stats.hiddenSubscriberCount ? '非公開' : stats.subscriberCount);
    Logger.log('動画数：%s', stats.videoCount);
    Logger.log('視聴回数：%s', stats.viewCount);
  }
}

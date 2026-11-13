function getPlacesReviewsNew() {
  const apiKey = PropertiesService.getScriptProperties().getProperty('PLACES_API_KEY');
  if (!apiKey) throw new Error('请先在脚本属性中配置 PLACES_API_KEY');
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) throw new Error('请从 Google Sheets 的扩展程序菜单打开此项目');

  const response = UrlFetchApp.fetch('https://places.googleapis.com/v1/places:searchText', {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'X-Goog-Api-Key': apiKey,
      'X-Goog-FieldMask': 'places.displayName,places.rating,places.userRatingCount,places.reviews,places.id,places.googleMapsUri'
    },
    payload: JSON.stringify({ textQuery: '渋谷 焼肉', languageCode: 'ja', pageSize: 5 }),
    muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error('Places 请求失败，HTTP ' + status + '；检查API启用、密钥限制、结算及配额');
  }
  const data = JSON.parse(response.getContentText());
  const places = data.places || [];
  if (places.length === 0) {
    spreadsheet.toast('没有找到店铺，请调整搜索词');
    return;
  }

  const rows = [['店舗名', '評価', 'レビュー総数', 'レビュー本文・著者・リンク', 'Place ID', 'Google Maps']];
  for (let i = 0; i < places.length; i++) {
    const place = places[i];
    const reviewTexts = [];
    const reviews = place.reviews || [];
    for (let j = 0; j < reviews.length; j++) {
      const review = reviews[j];
      if (!review.text || !review.text.text) continue;
      const author = review.authorAttribution || {};
      reviewTexts.push((author.displayName || '著者名なし') + '：' + review.text.text +
        '\n' + (author.uri || '') + '\n' + (review.googleMapsUri || ''));
    }
    rows.push([
      place.displayName ? place.displayName.text : '名称不明',
      place.rating == null ? 'N/A' : place.rating,
      place.userRatingCount == null ? 0 : place.userRatingCount,
      reviewTexts.join('\n\n'),
      place.id || '',
      place.googleMapsUri || ''
    ]);
  }
  // 每次新建结果页，避免清掉当前工作表里的既有内容。
  const name = 'Places_' + new Date().getTime();
  const sheet = spreadsheet.insertSheet(name);
  // 外部文本以等号开头时按普通文字写入，不当成公式执行。
  const safeRows = rows.map(function(row) {
    return row.map(function(value) {
      return typeof value === 'string' && value.startsWith('=') ? "'" + value : value;
    });
  });
  sheet.getRange(1, 1, safeRows.length, safeRows[0].length).setValues(safeRows);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, 6).setFontWeight('bold');
  sheet.getRange(1, 1, safeRows.length, 6).setWrap(true);
  spreadsheet.toast('已写入 ' + places.length + ' 家店铺：' + name);
}

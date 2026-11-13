/**
 * 把一个日本邮政编码转换为地址。在 Sheets 中使用 =ZIP_ADDRESS(A1)。
 * A列先设置为纯文本，避免邮编开头的0丢失。
 * @customfunction
 */
function ZIP_ADDRESS(zip) {
  const code = String(zip == null ? '' : zip).trim().replace(/-/g, '');
  if (code === '') return '';
  if (!/^\d{7}$/.test(code)) return '请输入7位邮政编码';

  const url = 'https://zipcloud.ibsnet.co.jp/api/search?zipcode=' + encodeURIComponent(code);
  const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (response.getResponseCode() !== 200) return '地址服务暂时不可用';

  const data = JSON.parse(response.getContentText());
  if (data.status !== 200) return data.message || '查询失败';
  if (!data.results || data.results.length === 0) return '没有找到地址';

  // 一个邮编可能对应多个地区，逐个拼接后放在同一个单元格里。
  const addresses = [];
  for (let i = 0; i < data.results.length; i++) {
    const item = data.results[i];
    addresses.push(item.address1 + item.address2 + item.address3);
  }
  return addresses.join(' / ');
}

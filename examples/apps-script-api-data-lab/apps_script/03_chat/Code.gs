function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('相棒AI 学习版')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function chatWithGemini(userMessage, history) {
  const properties = PropertiesService.getScriptProperties();
  const apiKey = properties.getProperty('GEMINI_API_KEY');
  const model = properties.getProperty('GEMINI_MODEL') || 'gemini-3.5-flash-lite';
  if (!apiKey) throw new Error('请先在脚本属性中配置 GEMINI_API_KEY');
  if (typeof userMessage !== 'string' || !userMessage.trim()) {
    throw new Error('消息不能为空');
  }
  if (userMessage.length > 2000) throw new Error('一次最多输入2000个字符');
  if (!Array.isArray(history)) throw new Error('会话记录格式不正确，请刷新页面');
  if (JSON.stringify(history).length > 100000) {
    throw new Error('本次会话较长，请刷新页面开启新会话');
  }

  // 建立副本，只有请求成功后才把新历史交回浏览器。
  const contents = JSON.parse(JSON.stringify(history));
  contents.push({ role: 'user', parts: [{ text: userMessage.trim() }] });
  const payload = {
    systemInstruction: {
      parts: [{
        text: 'あなたは冒険を手伝うファンタジー世界の相棒AIです。' +
          'ユーザーを「相棒」と呼び、親しみやすい日本語で短く答えてください。' +
          '現実の住所やニュースには答えず、物語の世界の話題に戻してください。'
      }]
    },
    contents: contents
  };
  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
    encodeURIComponent(model) + ':generateContent';
  let response;
  try {
    response = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: { 'x-goog-api-key': apiKey },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
  } catch (error) {
    // 不把可能带请求信息的原始异常写进页面。
    throw new Error('网络请求失败，请稍后重试');
  }
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    Logger.log('Gemini 请求未成功，HTTP %s', status);
    throw new Error('Gemini 返回 HTTP ' + status + '，请检查模型、密钥权限和配额');
  }
  let data;
  try {
    data = JSON.parse(response.getContentText());
  } catch (error) {
    throw new Error('服务返回的内容不是合法JSON');
  }
  const candidate = data.candidates && data.candidates[0];
  const modelContent = candidate && candidate.content;
  if (!modelContent || !Array.isArray(modelContent.parts)) {
    throw new Error('本次没有可显示的回复，请换一种问法');
  }
  const textParts = [];
  for (let i = 0; i < modelContent.parts.length; i++) {
    const part = modelContent.parts[i];
    if (!part.thought && typeof part.text === 'string') textParts.push(part.text);
  }
  const reply = textParts.join('\n').trim();
  if (!reply) throw new Error('本次没有文本回复');

  // 保留服务返回的完整content结构，包括可能存在的签名字段。
  contents.push(modelContent);
  return { reply: reply, newHistory: contents };
}

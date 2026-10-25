/* 首页工具：使用本机浏览器处理输入，不发送内容，也不写入阅读记录。 */
(() => {
  'use strict';
  const dialog = document.getElementById('utility-dialog');
  if (!dialog) return;
  const status = document.getElementById('utility-status');
  const jsonInput = document.getElementById('json-input');
  const jsonOutput = document.getElementById('json-output');
  let opener = null;

  for (const button of document.querySelectorAll('[data-open-tool]')) button.addEventListener('click', () => {
    opener = button;
    const json = button.dataset.openTool === 'json';
    document.getElementById('utility-title').textContent = json ? 'JSON 格式化' : '时间戳转换';
    document.getElementById('json-tool').hidden = !json;
    document.getElementById('timestamp-tool').hidden = json;
    status.textContent = '';
    dialog.showModal();
    (json ? jsonInput : document.getElementById('unix-input')).focus();
  });
  dialog.querySelector('[data-close-tool]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => opener?.focus({ preventScroll: true }));
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });

  function formatJson(text, pretty) {
    JSON.parse(text);
    // 保留原始数字文本，避免长整数标识在 parse/stringify 往返时丢失精度。
    const tokens = text.match(/"(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\]:,]/g);
    if (!pretty) return tokens.join('');
    let output = '', depth = 0;
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      if (token === '{' || token === '[') {
        output += token;
        if (tokens[i + 1] !== (token === '{' ? '}' : ']')) {
          depth++;
          if (depth > 100) throw new RangeError('嵌套层级超过 100，请分段格式化。');
          output += '\n' + '  '.repeat(depth);
        }
      } else if (token === '}' || token === ']') {
        if (tokens[i - 1] !== (token === '}' ? '{' : '[')) { depth--; output += '\n' + '  '.repeat(depth); }
        output += token;
      } else if (token === ',') output += ',\n' + '  '.repeat(depth);
      else output += token === ':' ? ': ' : token;
      if (output.length > 4_000_000) throw new RangeError('格式化结果超过 4 MB，请分段处理。');
    }
    return output;
  }

  for (const button of dialog.querySelectorAll('[data-json-action]')) button.addEventListener('click', () => {
    if (!jsonInput.value.trim()) { status.textContent = '先粘贴需要处理的 JSON 内容。'; jsonInput.focus(); return; }
    if (jsonInput.value.length > 2_000_000) { status.textContent = '内容超过 2 MB，请分段处理。'; return; }
    try {
      jsonOutput.value = formatJson(jsonInput.value, button.dataset.jsonAction === 'format');
      status.textContent = button.dataset.jsonAction === 'format' ? '已格式化。' : '已压缩。';
    } catch (error) {
      jsonOutput.value = '';
      status.textContent = error instanceof SyntaxError ? `JSON 格式有误：${error.message}` : error.message;
    }
  });
  dialog.querySelector('[data-copy-json]').addEventListener('click', async () => {
    if (!jsonOutput.value) { status.textContent = '先格式化或压缩，再复制结果。'; return; }
    try { await navigator.clipboard.writeText(jsonOutput.value); status.textContent = '已复制结果。'; }
    catch { jsonOutput.focus(); jsonOutput.select(); status.textContent = '浏览器未允许自动复制，结果已选中，可手动复制。'; }
  });

  const unixInput = document.getElementById('unix-input');
  const dateInput = document.getElementById('date-input');
  const timestampOutput = document.getElementById('timestamp-output');
  const two = number => String(number).padStart(2, '0');
  function localDate(date) {
    return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}T${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`;
  }
  dateInput.value = localDate(new Date());
  dialog.querySelector('[data-convert-unix]').addEventListener('click', () => {
    const raw = unixInput.value.trim();
    if (!/^-?\d{1,13}$/.test(raw)) { status.textContent = '请输入有效的整数时间戳，秒最多 10 位，毫秒为 13 位。'; return; }
    const digits = raw.replace('-', '').length;
    if (digits === 11 || digits === 12) { status.textContent = '无法确定单位，请输入秒（最多 10 位）或毫秒（13 位）。'; return; }
    const date = new Date(Number(raw) * (digits <= 10 ? 1000 : 1));
    if (!Number.isFinite(date.getTime()) || date.getFullYear() < 1 || date.getFullYear() > 9999) { status.textContent = '这个时间戳超出了可转换的日期范围。'; return; }
    dateInput.value = localDate(date);
    timestampOutput.textContent = `本地时间：${date.toLocaleString()}\nUTC：${date.toISOString()}`;
    status.textContent = '转换完成。';
  });
  dialog.querySelector('[data-convert-date]').addEventListener('click', () => {
    if (!dateInput.value || !dateInput.validity.valid) { status.textContent = '先选择有效的日期和时间。'; return; }
    const date = new Date(dateInput.value);
    if (!Number.isFinite(date.getTime())) { status.textContent = '日期格式无效，请重新选择。'; return; }
    unixInput.value = String(Math.floor(date.getTime() / 1000));
    timestampOutput.textContent = `秒：${Math.floor(date.getTime() / 1000)}\n毫秒：${date.getTime()}\nUTC：${date.toISOString()}`;
    status.textContent = '转换完成。';
  });

  // 桌面保持侧栏展开，手机首次进入收起；尺寸切换不重置同一尺寸下的用户选择。
  const toolbox = document.querySelector('.home-toolbox');
  const compact = matchMedia('(width < 768px)');
  const syncToolbox = () => { toolbox.open = !compact.matches; };
  compact.addEventListener('change', syncToolbox);
  syncToolbox();
})();

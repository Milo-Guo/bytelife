/* 私人后台使用同源接口；登录、GitHub 授权和权限续期由服务端处理。 */
(() => {
  'use strict';
  const KEY = 'bytelife-studio:last-save';
  let watchId = 0;
  async function request(path, body) {
    let response;
    try {
      response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
        headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'X-ByteLife-Request': '1' },
        body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(60000) });
    } catch { throw new Error('网络暂时没有响应。草稿已保留，联网后点“保存”重试。'); }
    let data;
    try { data = await response.json(); } catch { throw new Error('登录可能已过期，请打开“同步设置”重新登录；草稿已保留。'); }
    if (!response.ok) { const error = new Error(data.error || '暂时无法保存，请稍后重试。'); error.status = response.status; throw error; }
    return data;
  }
  function watch(sha, report) {
    const id = ++watchId;
    if (!/^[a-f0-9]{40}$/.test(sha || '')) return;
    try { localStorage.setItem(KEY, sha); } catch {}
    let attempts = 0;
    const poll = async () => {
      if (id !== watchId) return;
      try {
        const result = await request('/api/deployment?sha=' + sha);
        if (id !== watchId) return;
        if (result.state === 'published') { report('已同步 · 网站已更新', 'clean'); return; }
        if (result.state === 'failed') { report('已保存 · 网站更新失败，请稍后重试或查看发布记录', 'error'); return; }
        report('已保存 · 网站更新中，可继续编辑', 'clean');
      } catch { if (id === watchId) report('已保存 · 暂时无法确认网站更新进度', 'clean'); }
      if (++attempts < 60 && id === watchId) setTimeout(poll, 10000);
    };
    report('已保存 · 网站更新中，可继续编辑', 'clean'); poll();
  }
  function resume(report) { try { watch(localStorage.getItem(KEY), report); } catch {} }
  globalThis.ByteLifeStudio = Object.freeze({ request, watch, resume });
})();

let editingId = null;
let currentProducts = [];
const byId = (id) => document.getElementById(id);

function showMessage(message, isError = false) {
  byId('message').textContent = message;
  byId('message').className = isError ? 'error' : '';
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); } catch { throw new Error('服务没有返回 JSON，请检查后端和访问地址。'); }
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join('；') : data.detail;
    throw new Error(detail || `请求失败：HTTP ${response.status}`);
  }
  return data;
}

async function loadProducts() {
  try {
    const data = await request(`/api/products?page=1&page_size=50&search=${encodeURIComponent(byId('search').value)}`);
    currentProducts = data.data.items;
    const body = byId('products');
    body.replaceChildren();
    // 接口返回的文字通过 textContent 展示，避免把输入当成网页代码执行。
    for (const product of currentProducts) {
      const row = document.createElement('tr');
      for (const value of [product.id, product.name, `¥${(product.price_cents / 100).toFixed(2)}`, product.stock, product.is_published ? '已上架' : '未上架']) {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      }
      const actions = document.createElement('td');
      const edit = document.createElement('button');
      edit.className = 'secondary';
      edit.textContent = '编辑';
      edit.addEventListener('click', () => editProduct(product));
      actions.append(edit);
      row.append(actions);
      body.append(row);
    }
    if (!currentProducts.length) {
      const row = body.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 6;
      cell.textContent = '没有找到符合条件的商品。';
    }
    byId('total').textContent = `共 ${data.data.total} 条；本次数据来自 ${data.source}。`;
    byId('response').textContent = JSON.stringify(data, null, 2);
  } catch (error) { showMessage(error.message, true); }
}

function editProduct(product) {
  editingId = product.id;
  byId('name').value = product.name;
  byId('price').value = (product.price_cents / 100).toFixed(2);
  byId('stock').value = product.stock;
  byId('published').checked = product.is_published;
  byId('editor-title').textContent = `编辑商品 #${product.id}`;
  byId('name').focus();
  showMessage('修改字段后，点击“保存商品”。');
}

function resetEditor() {
  editingId = null;
  byId('name').value = '';
  byId('price').value = '29.90';
  byId('stock').value = '50';
  byId('published').checked = true;
  byId('editor-title').textContent = '新增商品';
}

byId('product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  byId('save').disabled = true;
  try {
    const input = { name: byId('name').value, price_cents: Math.round(Number(byId('price').value) * 100),
      stock: Number(byId('stock').value), is_published: byId('published').checked };
    const result = await request(editingId ? `/api/products/${editingId}` : '/api/products', {
      method: editingId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Key': byId('admin-key').value },
      body: JSON.stringify(input),
    });
    resetEditor();
    await loadProducts();
    showMessage(`${result.message}。刷新页面后可再次查询。`);
  } catch (error) { showMessage(error.message, true); }
  finally { byId('save').disabled = false; }
});
byId('search-form').addEventListener('submit', (event) => { event.preventDefault(); loadProducts(); });
byId('refresh').addEventListener('click', loadProducts);
byId('cancel').addEventListener('click', () => { resetEditor(); showMessage('表单已清空，数据库记录未改动。'); });

request('/api/health').then(data => {
  byId('connection').textContent = `后端连接正常 · 数据库：${data.database} · Redis：${data.redis}`;
}).catch(error => { byId('connection').textContent = error.message; });
loadProducts();

/**
 * StockFlow Frontend Application Controller
 * Handles REST API interactions, live telemetry polling, and state rendering.
 */

// Global Application State
const state = {
  activeTab: 'tab-inventory',
  products: [],
  categories: [],
  stats: {},
  selectedProduct: null,
  activeTestPollInterval: null,
  logsPollInterval: null,
  isTestRunning: false
};

// DOM Elements
const el = {
  // Navigation
  tabs: document.querySelectorAll('.nav-tab'),
  tabContents: document.querySelectorAll('.tab-content'),
  logCountBadge: document.getElementById('log-count-badge'),

  // KPI Stats
  statTotalProducts: document.getElementById('stat-total-products'),
  statCategoryCount: document.getElementById('stat-category-count'),
  statTotalQuantity: document.getElementById('stat-total-quantity'),
  statTotalValuation: document.getElementById('stat-total-valuation'),
  statInStock: document.getElementById('stat-in-stock'),
  statLowStock: document.getElementById('stat-low-stock'),
  statOutStock: document.getElementById('stat-out-stock'),

  // Inventory Table & Filters
  inventoryTbody: document.getElementById('inventory-tbody'),
  searchInput: document.getElementById('inventory-search'),
  filterCategory: document.getElementById('filter-category'),
  filterStatus: document.getElementById('filter-status'),
  sortBy: document.getElementById('sort-by'),
  btnRefreshInventory: document.getElementById('btn-refresh-inventory'),
  btnAddProduct: document.getElementById('btn-add-product'),

  // Test Lab
  testForm: document.getElementById('test-form'),
  testSkuSelect: document.getElementById('test-sku'),
  testSkuInfo: document.getElementById('test-sku-info'),
  testThreadsRange: document.getElementById('test-threads-range'),
  testThreadsInput: document.getElementById('test-threads'),
  testAmountInput: document.getElementById('test-amount'),
  testDelayRange: document.getElementById('test-delay-range'),
  delayDisplay: document.getElementById('delay-display'),
  btnStartTest: document.getElementById('btn-start-test'),
  testStatusPill: document.getElementById('test-status-pill'),
  telemetryProgressText: document.getElementById('telemetry-progress-text'),
  telemetryTime: document.getElementById('telemetry-time'),
  telemetryProgressBar: document.getElementById('telemetry-progress-bar'),
  telemTotal: document.getElementById('telem-total'),
  telemSuccess: document.getElementById('telem-success'),
  telemFailed: document.getElementById('telem-failed'),
  telemStock: document.getElementById('telem-stock'),
  testSummaryMsg: document.getElementById('test-summary-message'),
  testHistoryTbody: document.getElementById('test-history-tbody'),

  // Logs
  terminalLogs: document.getElementById('terminal-logs'),
  logFilterLevel: document.getElementById('log-filter-level'),
  logSearch: document.getElementById('log-search'),
  logAutoscroll: document.getElementById('log-autoscroll'),
  btnRefreshLogs: document.getElementById('btn-refresh-logs'),

  // Modals
  modalProductDetails: document.getElementById('modal-product-details'),
  modalAddProduct: document.getElementById('modal-add-product'),
  formAddProduct: document.getElementById('form-add-product'),
  formEditProduct: document.getElementById('form-edit-product'),

  // Detail Modal Elements
  modalProductName: document.getElementById('modal-product-name'),
  modalProductSku: document.getElementById('modal-product-sku'),
  detailCategory: document.getElementById('detail-category'),
  detailStatus: document.getElementById('detail-status'),
  detailPrice: document.getElementById('detail-price'),
  detailQty: document.getElementById('detail-qty'),
  detailTotalVal: document.getElementById('detail-total-val'),
  detailDesc: document.getElementById('detail-desc'),
  quickSellAmount: document.getElementById('quick-sell-amount'),
  btnQuickSell: document.getElementById('btn-quick-sell'),
  quickRestockAmount: document.getElementById('quick-restock-amount'),
  btnQuickRestock: document.getElementById('btn-quick-restock'),
  editName: document.getElementById('edit-name'),
  editPrice: document.getElementById('edit-price'),
  editCategory: document.getElementById('edit-category'),
  editDesc: document.getElementById('edit-desc'),
  btnDeleteProduct: document.getElementById('btn-delete-product'),

  toastContainer: document.getElementById('toast-container')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupFilterListeners();
  setupTestLabControls();
  setupModalListeners();
  setupLogControls();

  // Initial Data Load
  loadDashboardStats();
  loadInventory();
  loadLogs();
  checkActiveTestStatus();

  // Background auto-refresh for logs (every 3 seconds)
  state.logsPollInterval = setInterval(loadLogs, 3000);
});

// --- Tab Navigation ---
function setupNavigation() {
  el.tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      el.tabs.forEach(t => t.classList.remove('active'));
      el.tabContents.forEach(tc => tc.classList.remove('active'));

      tab.classList.add('active');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
      state.activeTab = targetId;

      if (targetId === 'tab-logs') {
        loadLogs();
      } else if (targetId === 'tab-tests') {
        checkActiveTestStatus();
      }
    });
  });
}

// --- Currency Formatter (Indian Rupee - INR) ---
function formatINR(amount) {
  const num = Number(amount) || 0;
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// --- Toast Notifications ---
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ'}</span> <span>${message}</span>`;
  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// --- REST API: Dashboard Stats ---
async function loadDashboardStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.stats = data;

    // Render KPIs
    el.statTotalProducts.textContent = data.total_products.toLocaleString('en-IN');
    el.statTotalQuantity.textContent = data.total_quantity.toLocaleString('en-IN');
    el.statTotalValuation.textContent = formatINR(data.total_valuation);
    el.statInStock.textContent = data.in_stock;
    el.statLowStock.textContent = data.low_stock;
    el.statOutStock.textContent = data.out_of_stock;

    if (data.categories) {
      el.statCategoryCount.textContent = `${data.categories.length} unique categories`;
      updateCategoryDropdown(data.categories);
    }
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

function updateCategoryDropdown(categories) {
  const currentVal = el.filterCategory.value;
  // Preserve "All" option
  el.filterCategory.innerHTML = '<option value="All">All Categories</option>';
  categories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = cat;
    el.filterCategory.appendChild(opt);
  });
  if (categories.includes(currentVal)) {
    el.filterCategory.value = currentVal;
  }
}

// --- REST API: Inventory List ---
async function loadInventory() {
  try {
    const query = el.searchInput.value.trim();
    const category = el.filterCategory.value;
    const status = el.filterStatus.value;
    const [sortBy, sortOrder] = el.sortBy.value.split('_');

    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (category && category !== 'All') params.append('category', category);
    if (status && status !== 'All') params.append('stock_status', status);
    if (sortBy) params.append('sort_by', sortBy);
    if (sortOrder) params.append('order', sortOrder);

    const res = await fetch(`/api/products?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.products = data.products || [];

    renderInventoryTable(state.products);
    updateTestSkuDropdown(state.products);
  } catch (err) {
    console.error('Failed to load inventory:', err);
    el.inventoryTbody.innerHTML = `<tr><td colspan="8" class="text-center py-8" style="color:var(--danger)">Failed to load inventory. Please verify backend is running.</td></tr>`;
  }
}

function renderInventoryTable(products) {
  if (products.length === 0) {
    el.inventoryTbody.innerHTML = `<tr><td colspan="8" class="text-center py-8" style="color:var(--text-muted)">No matching products found.</td></tr>`;
    return;
  }

  el.inventoryTbody.innerHTML = products.map(p => {
    const statusClass = p.stock_status.toLowerCase().replace(/\s+/g, '-');
    return `
      <tr data-sku="${p.sku}">
        <td><span class="sku-code">${p.sku}</span></td>
        <td>
          <div class="product-cell">
            <span class="product-name">${escapeHtml(p.name)}</span>
            <span class="product-desc-hint">${escapeHtml(p.description || '')}</span>
          </div>
        </td>
        <td><span class="badge-category">${escapeHtml(p.category || 'General')}</span></td>
        <td><strong>${formatINR(p.price)}</strong></td>
        <td><strong>${Number(p.quantity).toLocaleString('en-IN')}</strong> units</td>
        <td>${formatINR(p.total_value)}</td>
        <td>
          <span class="badge-status ${statusClass}">
            <span class="dot ${statusClass === 'in-stock' ? 'green' : statusClass === 'low-stock' ? 'yellow' : 'red'}"></span>
            ${p.stock_status}
          </span>
        </td>
        <td class="text-right">
          <div class="btn-group">
            <button class="btn btn-secondary btn-sm btn-view-prod" data-sku="${p.sku}" title="Inspect Details & Edit">View</button>
            <button class="btn btn-warning btn-sm btn-sell-prod" data-sku="${p.sku}" title="Sell 1 unit">Sell</button>
            <button class="btn btn-success btn-sm btn-restock-prod" data-sku="${p.sku}" title="Restock 10 units">+10</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  // Row click listener to open detail modal
  el.inventoryTbody.querySelectorAll('tr').forEach(row => {
    row.addEventListener('click', (e) => {
      // Ignore if an action button was clicked directly
      if (e.target.closest('button')) return;
      const sku = row.dataset.sku;
      openProductDetails(sku);
    });
  });

  // Action button listeners
  el.inventoryTbody.querySelectorAll('.btn-view-prod').forEach(btn => {
    btn.addEventListener('click', () => openProductDetails(btn.dataset.sku));
  });

  el.inventoryTbody.querySelectorAll('.btn-sell-prod').forEach(btn => {
    btn.addEventListener('click', async () => {
      await quickSell(btn.dataset.sku, 1);
    });
  });

  el.inventoryTbody.querySelectorAll('.btn-restock-prod').forEach(btn => {
    btn.addEventListener('click', async () => {
      await quickRestock(btn.dataset.sku, 10);
    });
  });
}

function updateTestSkuDropdown(products) {
  const currentVal = el.testSkuSelect.value;
  el.testSkuSelect.innerHTML = products.map(p => 
    `<option value="${p.sku}" data-stock="${p.quantity}" data-price="${p.price}">
      ${p.sku} - ${escapeHtml(p.name)} (${p.quantity} in stock)
    </option>`
  ).join('');

  if (currentVal && products.some(p => p.sku === currentVal)) {
    el.testSkuSelect.value = currentVal;
  } else if (products.some(p => p.sku === 'PROD-1002')) {
    el.testSkuSelect.value = 'PROD-1002'; // default to match original stress test
  }
  updateTestSkuInfo();
}

function updateTestSkuInfo() {
  const selectedOpt = el.testSkuSelect.options[el.testSkuSelect.selectedIndex];
  if (selectedOpt) {
    const stock = Number(selectedOpt.dataset.stock).toLocaleString('en-IN');
    const price = selectedOpt.dataset.price;
    el.testSkuInfo.textContent = `Available Stock: ${stock} units | Price: ${formatINR(price)}`;
  }
}

// --- Product Details Modal ---
async function openProductDetails(sku) {
  try {
    const res = await fetch(`/api/products/${sku}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const prod = await res.json();
    state.selectedProduct = prod;

    el.modalProductName.textContent = prod.name;
    el.modalProductSku.textContent = prod.sku;
    el.detailCategory.textContent = prod.category;
    el.detailPrice.textContent = formatINR(prod.price);
    el.detailQty.textContent = `${Number(prod.quantity).toLocaleString('en-IN')} units`;
    el.detailTotalVal.textContent = formatINR(prod.total_value);
    el.detailDesc.textContent = prod.description || 'No description entered.';

    const statusClass = prod.stock_status.toLowerCase().replace(/\s+/g, '-');
    el.detailStatus.innerHTML = `
      <span class="badge-status ${statusClass}">
        <span class="dot ${statusClass === 'in-stock' ? 'green' : statusClass === 'low-stock' ? 'yellow' : 'red'}"></span>
        ${prod.stock_status}
      </span>
    `;

    // Populate Edit Form fields
    el.editName.value = prod.name;
    el.editPrice.value = prod.price;
    el.editCategory.value = prod.category;
    el.editDesc.value = prod.description || '';

    el.modalProductDetails.classList.remove('hidden');
  } catch (err) {
    showToast(`Failed to load product details: ${err.message}`, 'error');
  }
}

// --- API Mutations: Quick Sell & Restock ---
async function quickSell(sku, amount) {
  try {
    const res = await fetch(`/api/products/${sku}/sell`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

    showToast(`Sold ${amount} of ${data.name}. Remaining: ${data.quantity}`, 'success');
    refreshAllData();
    if (state.selectedProduct && state.selectedProduct.sku === sku) {
      openProductDetails(sku);
    }
  } catch (err) {
    showToast(`Sale failed: ${err.message}`, 'error');
  }
}

async function quickRestock(sku, amount) {
  try {
    const res = await fetch(`/api/products/${sku}/restock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

    showToast(`Restocked ${amount} units for ${data.name}. New total: ${data.quantity}`, 'success');
    refreshAllData();
    if (state.selectedProduct && state.selectedProduct.sku === sku) {
      openProductDetails(sku);
    }
  } catch (err) {
    showToast(`Restock failed: ${err.message}`, 'error');
  }
}

function refreshAllData() {
  loadDashboardStats();
  loadInventory();
  loadLogs();
}

// --- Filter & Search Listeners ---
function setupFilterListeners() {
  let debounceTimeout;
  el.searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(loadInventory, 250);
  });

  el.filterCategory.addEventListener('change', loadInventory);
  el.filterStatus.addEventListener('change', loadInventory);
  el.sortBy.addEventListener('change', loadInventory);
  el.btnRefreshInventory.addEventListener('click', () => {
    refreshAllData();
    showToast('Inventory refreshed', 'info');
  });

  el.testSkuSelect.addEventListener('change', updateTestSkuInfo);
}

// --- Test Lab Controls ---
function setupTestLabControls() {
  // Sync slider and number inputs
  el.testThreadsRange.addEventListener('input', () => {
    el.testThreadsInput.value = el.testThreadsRange.value;
  });
  el.testThreadsInput.addEventListener('input', () => {
    el.testThreadsRange.value = el.testThreadsInput.value;
  });

  el.testDelayRange.addEventListener('input', () => {
    el.delayDisplay.textContent = `${el.testDelayRange.value} ms`;
  });

  // Launch test form
  el.testForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (state.isTestRunning) return;

    const sku = el.testSkuSelect.value;
    const threads = parseInt(el.testThreadsInput.value);
    const amount = parseInt(el.testAmountInput.value);
    const delay_ms = parseInt(el.testDelayRange.value);

    try {
      el.btnStartTest.disabled = true;
      el.btnStartTest.innerHTML = '<span>⏳ Starting simulation...</span>';

      const res = await fetch('/api/tests/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku, threads, amount, delay_ms })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

      state.isTestRunning = true;
      showToast(`Concurrency test launched with ${threads} customer threads!`, 'info');
      startTestStatusPolling();
    } catch (err) {
      showToast(`Could not launch test: ${err.message}`, 'error');
      el.btnStartTest.disabled = false;
      el.btnStartTest.innerHTML = '<span>🚀 Launch Concurrency Test</span>';
    }
  });
}

function startTestStatusPolling() {
  if (state.activeTestPollInterval) clearInterval(state.activeTestPollInterval);

  state.activeTestPollInterval = setInterval(async () => {
    const isStillRunning = await checkActiveTestStatus();
    if (!isStillRunning) {
      clearInterval(state.activeTestPollInterval);
      state.activeTestPollInterval = null;
      state.isTestRunning = false;
      el.btnStartTest.disabled = false;
      el.btnStartTest.innerHTML = '<span>🚀 Launch Concurrency Test</span>';
      refreshAllData();
    }
  }, 250);
}

async function checkActiveTestStatus() {
  try {
    const res = await fetch('/api/tests/status');
    if (!res.ok) return false;
    const data = await res.json();

    const active = data.active_test;
    renderTestHistory(data.history || []);

    if (!active) {
      el.testStatusPill.className = 'badge-status idle';
      el.testStatusPill.textContent = 'Idle';
      return false;
    }

    const isRunning = active.status === 'running';

    // Status Pill
    el.testStatusPill.className = `badge-status ${active.status}`;
    el.testStatusPill.textContent = isRunning ? '⚡ Running...' : active.status === 'completed' ? '✓ Completed' : 'Failed';

    // Telemetry Progress
    const progress = active.progress_percent || 0;
    el.telemetryProgressBar.style.width = `${progress}%`;
    el.telemetryProgressText.textContent = `${progress}%`;
    el.telemetryTime.textContent = isRunning ? `Elapsed: ${active.elapsed_ms || 0}ms` : `Duration: ${active.duration_ms}ms`;

    // Counters
    el.telemTotal.textContent = `${active.completed_threads} / ${active.total_threads}`;
    el.telemSuccess.textContent = active.successful_sales;
    el.telemFailed.textContent = active.out_of_stock_failures;
    el.telemStock.textContent = `${active.initial_stock} → ${active.final_stock !== null ? active.final_stock : '...'}`;

    // Summary alert when done
    if (!isRunning && active.status === 'completed') {
      el.testSummaryMsg.classList.remove('hidden');
      el.testSummaryMsg.innerHTML = `
        <strong>Simulation Report:</strong> Ran ${active.total_threads} concurrent sales threads on <code>${active.sku}</code> (${active.product_name}).<br>
        ✓ <strong>${active.successful_sales}</strong> sales completed safely under mutex lock.<br>
        ⚠ <strong>${active.out_of_stock_failures}</strong> requests rejected due to insufficient stock (race condition prevented!).<br>
        ⏱ Finished in <strong>${active.duration_ms}ms</strong>. Final stock: <strong>${active.final_stock} units</strong>.
      `;
    }

    return isRunning;
  } catch (err) {
    console.error('Error checking test status:', err);
    return false;
  }
}

function renderTestHistory(history) {
  if (history.length === 0) {
    el.testHistoryTbody.innerHTML = '<tr><td colspan="6" class="text-center">No tests executed yet.</td></tr>';
    return;
  }

  el.testHistoryTbody.innerHTML = history.map(item => `
    <tr>
      <td><span class="sku-code">${item.sku}</span></td>
      <td>${item.total_threads}</td>
      <td style="color:var(--success)">${item.successful_sales}</td>
      <td style="color:var(--warning)">${item.out_of_stock_failures}</td>
      <td>${item.duration_ms}ms</td>
      <td><span class="badge-status ${item.status}">${item.status}</span></td>
    </tr>
  `).join('');
}

// --- System Logs Controls ---
function setupLogControls() {
  el.logFilterLevel.addEventListener('change', loadLogs);
  let searchDebounce;
  el.logSearch.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(loadLogs, 300);
  });
  el.btnRefreshLogs.addEventListener('click', () => {
    loadLogs();
    showToast('Logs refreshed', 'info');
  });
}

async function loadLogs() {
  try {
    const level = el.logFilterLevel.value;
    const query = el.logSearch.value.trim();

    const params = new URLSearchParams({ limit: '150' });
    if (level && level !== 'ALL') params.append('level', level);
    if (query) params.append('q', query);

    const res = await fetch(`/api/logs?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    const logs = data.logs || [];

    el.logCountBadge.textContent = logs.length;

    if (logs.length === 0) {
      el.terminalLogs.innerHTML = '<div class="terminal-placeholder">No log entries matching criteria.</div>';
      return;
    }

    el.terminalLogs.innerHTML = logs.map(l => `
      <div class="terminal-line">
        <span class="log-ts">${l.timestamp || ''}</span>
        <span class="log-level ${l.level}">${l.level || 'INFO'}</span>
        <span class="log-msg">${escapeHtml(l.message)}</span>
      </div>
    `).join('');

    if (el.logAutoscroll.checked) {
      el.terminalLogs.scrollTop = el.terminalLogs.scrollHeight;
    }
  } catch (err) {
    console.error('Failed to load logs:', err);
  }
}

// --- Modals Setup ---
function setupModalListeners() {
  // Add product modal trigger
  el.btnAddProduct.addEventListener('click', () => {
    el.formAddProduct.reset();
    el.modalAddProduct.classList.remove('hidden');
  });

  // Close modals
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      el.modalProductDetails.classList.add('hidden');
      el.modalAddProduct.classList.add('hidden');
    });
  });

  // Close when clicking modal backdrop
  [el.modalProductDetails, el.modalAddProduct].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });
  });

  // Add Product Form Submit
  el.formAddProduct.addEventListener('submit', async (e) => {
    e.preventDefault();
    const sku = document.getElementById('add-sku').value.trim().toUpperCase();
    const name = document.getElementById('add-name').value.trim();
    const price = parseFloat(document.getElementById('add-price').value);
    const quantity = parseInt(document.getElementById('add-quantity').value);
    const category = document.getElementById('add-category').value.trim();
    const description = document.getElementById('add-description').value.trim();

    try {
      const res = await fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku, name, price, quantity, category, description })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

      showToast(`Product ${data.name} (${data.sku}) created!`, 'success');
      el.modalAddProduct.classList.add('hidden');
      refreshAllData();
    } catch (err) {
      showToast(`Failed to add product: ${err.message}`, 'error');
    }
  });

  // Quick Action: Sell in modal
  el.btnQuickSell.addEventListener('click', async () => {
    if (!state.selectedProduct) return;
    const amount = parseInt(el.quickSellAmount.value) || 1;
    await quickSell(state.selectedProduct.sku, amount);
  });

  // Quick Action: Restock in modal
  el.btnQuickRestock.addEventListener('click', async () => {
    if (!state.selectedProduct) return;
    const amount = parseInt(el.quickRestockAmount.value) || 10;
    await quickRestock(state.selectedProduct.sku, amount);
  });

  // Edit Product Form Submit
  el.formEditProduct.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!state.selectedProduct) return;

    const sku = state.selectedProduct.sku;
    const name = el.editName.value.trim();
    const price = parseFloat(el.editPrice.value);
    const category = el.editCategory.value.trim();
    const description = el.editDesc.value.trim();

    try {
      const res = await fetch(`/api/products/${sku}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, price, category, description })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

      showToast(`Updated product attributes for ${sku}`, 'success');
      openProductDetails(sku);
      refreshAllData();
    } catch (err) {
      showToast(`Update failed: ${err.message}`, 'error');
    }
  });

  // Delete Product
  el.btnDeleteProduct.addEventListener('click', async () => {
    if (!state.selectedProduct) return;
    const sku = state.selectedProduct.sku;
    const confirmDelete = confirm(`Are you sure you want to permanently delete product '${state.selectedProduct.name}' (${sku})?`);
    if (!confirmDelete) return;

    try {
      const res = await fetch(`/api/products/${sku}`, { method: 'DELETE' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);

      showToast(`Product ${sku} deleted.`, 'success');
      el.modalProductDetails.classList.add('hidden');
      state.selectedProduct = null;
      refreshAllData();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, 'error');
    }
  });
}

// Utility: Escape HTML for security against XSS
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

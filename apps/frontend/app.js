const trendChart = echarts.init(document.getElementById("trendChart"));
const heatmapChart = echarts.init(document.getElementById("heatmapChart"));
const funnelChart = echarts.init(document.getElementById("funnelChart"));
const sentimentChart = echarts.init(document.getElementById("sentimentChart"));

const liveIdSelect = document.getElementById("liveId");
const refreshBtn = document.getElementById("refreshBtn");
const realtimeToggle = document.getElementById("realtimeToggle");
const realtimeStatus = document.getElementById("realtimeStatus");

const navItems = Array.from(document.querySelectorAll(".nav-item[data-page]"));
const pages = {
  overview: document.getElementById("page-overview"),
  operation: document.getElementById("page-operation"),
  data: document.getElementById("page-data"),
  setting: document.getElementById("page-setting"),
};

const globalSearch = document.getElementById("globalSearch");

const ovLiveCount = document.getElementById("ovLiveCount");
const ovTaskCount = document.getElementById("ovTaskCount");
const ovLag = document.getElementById("ovLag");
const ovHealth = document.getElementById("ovHealth");
const ovNoticeList = document.getElementById("ovNoticeList");

const opPlanBody = document.getElementById("opPlanBody");
const opSchedule = document.getElementById("opSchedule");
const opAddPlanBtn = document.getElementById("opAddPlanBtn");

const setDefaultPage = document.getElementById("setDefaultPage");
const setDensity = document.getElementById("setDensity");
const setAutoRealtime = document.getElementById("setAutoRealtime");
const setSaveBtn = document.getElementById("setSaveBtn");

const toastContainer = document.getElementById("toastContainer");

const state = {
  currentPage: "data",
  realtimeOn: false,
  source: null,
  autoRealtimeOnEnterData: false,
  settings: {
    defaultPage: "data",
    density: "normal",
  },
};

const operationPlans = [
  { id: 1, name: "春季美妆专场", owner: "运营-李晴", startAt: "2026-03-10 20:00", budget: 30000, status: "待执行" },
  { id: 2, name: "零食节限时秒杀", owner: "运营-周洋", startAt: "2026-03-11 19:30", budget: 42000, status: "进行中" },
  { id: 3, name: "数码新品日", owner: "运营-王晨", startAt: "2026-03-12 21:00", budget: 38000, status: "待执行" },
];

const scheduleItems = [
  { slot: "10:00-12:00", suggestion: "低频维护场，安排 1 名值班运营" },
  { slot: "14:00-18:00", suggestion: "日常转化场，安排 2 名运营 + 1 名客服" },
  { slot: "20:00-24:00", suggestion: "黄金高峰场，安排 3 名运营 + 2 名客服" },
];

function fmtNum(v) {
  return Number(v || 0).toLocaleString();
}

function showToast(text, ms = 2200) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  toastContainer.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

function setRealtimeStatus(text, cls) {
  realtimeStatus.textContent = text;
  realtimeStatus.className = `rt-status ${cls}`;
}

async function getJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`请求失败: ${url}`);
  }
  return resp.json();
}

function switchPage(page) {
  state.currentPage = page;
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.page === page));
  Object.entries(pages).forEach(([name, el]) => {
    if (!el) return;
    el.classList.toggle("hidden", name !== page);
  });

  if (page !== "data") {
    stopRealtime();
    setRealtimeStatus("实时未开启", "rt-off");
    realtimeToggle.textContent = "开启实时";
    state.realtimeOn = false;
  } else {
    refreshStatic().catch((err) => showToast(err.message));
    window.dispatchEvent(new Event("resize"));
    if (state.autoRealtimeOnEnterData) {
      toggleRealtime(true);
    }
  }
}

function renderOverview() {
  ovLiveCount.textContent = `${Math.floor(8 + Math.random() * 4)}`;
  ovTaskCount.textContent = `${Math.floor(5 + Math.random() * 6)}`;
  ovLag.textContent = `${Math.floor(30 + Math.random() * 80)} 条`;
  ovHealth.textContent = `${(96 + Math.random() * 3).toFixed(1)}%`;

  const notices = [
    "今日 20:00-22:00 为高峰时段，建议提前排班。",
    "检测到 live_002 弹幕增速提升，建议同步投放加购券。",
    "昨晚活动转化率较前日提升 8.2%，建议复用话术。",
  ];

  ovNoticeList.innerHTML = "";
  notices.forEach((n) => {
    const li = document.createElement("li");
    li.textContent = n;
    ovNoticeList.appendChild(li);
  });
}

function renderOperation() {
  opPlanBody.innerHTML = "";
  operationPlans.forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.name}</td>
      <td>${p.owner}</td>
      <td>${p.startAt}</td>
      <td>¥ ${fmtNum(p.budget)}</td>
      <td>${p.status}</td>
      <td><button class="op-toggle" data-id="${p.id}">${p.status === "进行中" ? "结束" : "启动"}</button></td>
    `;
    opPlanBody.appendChild(tr);
  });

  opSchedule.innerHTML = "";
  scheduleItems.forEach((s) => {
    const card = document.createElement("div");
    card.className = "schedule-card";
    card.innerHTML = `<h4>${s.slot}</h4><p>${s.suggestion}</p>`;
    opSchedule.appendChild(card);
  });
}

function renderSetting() {
  setDefaultPage.value = state.settings.defaultPage;
  setDensity.value = state.settings.density;
  setAutoRealtime.checked = state.autoRealtimeOnEnterData;
  document.body.classList.toggle("compact", state.settings.density === "compact");
}

function bindSettingActions() {
  setSaveBtn.addEventListener("click", () => {
    state.settings.defaultPage = setDefaultPage.value;
    state.settings.density = setDensity.value;
    state.autoRealtimeOnEnterData = setAutoRealtime.checked;
    renderSetting();
    showToast("设置已保存");
  });
}

function bindOperationActions() {
  opAddPlanBtn.addEventListener("click", () => {
    const id = operationPlans.length + 1;
    operationPlans.push({
      id,
      name: `新增活动-${id}`,
      owner: "运营-新建",
      startAt: "2026-03-13 20:00",
      budget: 28000,
      status: "待执行",
    });
    renderOperation();
    showToast("已新增活动计划");
  });

  opPlanBody.addEventListener("click", (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (!target.classList.contains("op-toggle")) return;
    const id = Number(target.dataset.id);
    const plan = operationPlans.find((p) => p.id === id);
    if (!plan) return;
    plan.status = plan.status === "进行中" ? "已结束" : "进行中";
    renderOperation();
    showToast(`活动状态已更新：${plan.status}`);
  });
}

function bindPageNav() {
  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      switchPage(item.dataset.page);
    });
  });

  document.querySelectorAll(".quick-btn[data-jump]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const page = btn.dataset.jump;
      switchPage(page);
    });
  });
}

function bindGlobalSearch() {
  globalSearch.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const q = globalSearch.value.trim().toLowerCase();
    if (!q) return;

    const match = ["live_001", "live_002", "live_003"].find((id) => id.includes(q));
    if (match) {
      switchPage("data");
      liveIdSelect.value = match;
      refreshStatic().catch((err) => showToast(err.message));
      showToast(`已定位到 ${match}`);
    } else {
      showToast("未命中直播间ID，试试 live_001 / live_002 / live_003");
    }
  });
}

function renderKpi({ online, likes, gifts, gmv }) {
  document.getElementById("kpiOnline").textContent = fmtNum(online);
  document.getElementById("kpiLikes").textContent = fmtNum(likes);
  document.getElementById("kpiGifts").textContent = fmtNum(gifts);
  document.getElementById("kpiGmv").textContent = `¥ ${fmtNum(gmv)}`;
}

function renderTrendFromPoints(points, xField, yField) {
  const x = points.map((p) => String(p[xField] || "").slice(11, 16));
  const y = points.map((p) => Number(p[yField] || 0));
  trendChart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: x, axisLabel: { showMaxLabel: true } },
    yAxis: { type: "value" },
    series: [{ type: "line", smooth: true, areaStyle: {}, data: y }],
  });
}

function renderHeatmapFromPairs(xData, yData) {
  heatmapChart.setOption({
    tooltip: {},
    xAxis: { type: "category", data: xData },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: yData }],
  });
}

async function loadOverview(liveId) {
  const data = await getJSON(`/api/overview/${liveId}`);
  renderKpi({
    online: data.online_users,
    likes: data.likes,
    gifts: data.gifts,
    gmv: data.gmv,
  });
}

async function loadTrend(liveId) {
  const data = await getJSON(`/api/trend/${liveId}?metric=online_users`);
  renderTrendFromPoints(data.points, "ts", "value");
}

async function loadHeatmap(liveId) {
  const data = await getJSON(`/api/heatmap/${liveId}`);
  renderHeatmapFromPairs(
    data.items.map((i) => i.minute_slot),
    data.items.map((i) => i.interaction_count)
  );
}

async function loadFunnel(liveId) {
  const data = await getJSON(`/api/funnel/${liveId}`);
  const f = data.funnel;
  funnelChart.setOption({
    tooltip: { trigger: "item", formatter: "{b}: {c}" },
    series: [
      {
        type: "funnel",
        left: "10%",
        top: 20,
        bottom: 20,
        width: "80%",
        data: [
          { value: f.exposure, name: "曝光" },
          { value: f.click, name: "点击" },
          { value: f.add_cart, name: "加购" },
          { value: f.purchase, name: "购买" },
        ],
      },
    ],
  });
}

async function loadSentiment(liveId) {
  const data = await getJSON(`/api/sentiment/${liveId}`);
  sentimentChart.setOption({
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: "60%",
        data: [
          { name: "正向", value: data.summary.positive },
          { name: "中性", value: data.summary.neutral },
          { name: "负向", value: data.summary.negative },
        ],
      },
    ],
  });
}

async function loadTopUsers(liveId) {
  const data = await getJSON(`/api/interaction/top-users/${liveId}`);
  const body = document.getElementById("topUsersBody");
  body.innerHTML = "";
  data.users.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.user_id}</td>
      <td>${u.comments}</td>
      <td>${u.likes}</td>
      <td>${u.gifts}</td>
      <td>${u.score}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadRecommend() {
  const data = await getJSON("/api/recommend/u0001?top_n=5");
  const list = document.getElementById("recommendList");
  list.innerHTML = "";
  data.items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.name}（${item.reason}，匹配分=${Number(item.score).toFixed(3)}）`;
    list.appendChild(li);
  });
}

async function refreshStatic() {
  const liveId = liveIdSelect.value;
  await Promise.all([
    loadOverview(liveId),
    loadTrend(liveId),
    loadHeatmap(liveId),
    loadFunnel(liveId),
    loadSentiment(liveId),
    loadTopUsers(liveId),
    loadRecommend(),
  ]);
}

function applyRealtimePayload(payload) {
  if (!payload || !payload.latest) {
    return;
  }

  const latest = payload.latest;
  const points = payload.points || [];

  renderKpi({
    online: latest.avg_online_users,
    likes: latest.like_events,
    gifts: latest.gift_events,
    gmv: latest.gift_value_sum,
  });

  renderTrendFromPoints(points, "window_end", "avg_online_users");
  renderHeatmapFromPairs(
    points.map((p) => String(p.window_end || "").slice(11, 16)),
    points.map((p) => Number(p.interaction_events || 0))
  );
}

function stopRealtime() {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
}

function startRealtime() {
  stopRealtime();
  const liveId = liveIdSelect.value;
  const url = `/api/realtime/stream/${liveId}?interval=1&limit=60`;
  state.source = new EventSource(url);

  setRealtimeStatus("实时连接中...", "rt-warn");

  state.source.onmessage = (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.latest) {
        applyRealtimePayload(payload);
        setRealtimeStatus("实时已连接", "rt-on");
      } else {
        setRealtimeStatus("已连接，等待实时数据", "rt-warn");
      }
    } catch (_e) {
      setRealtimeStatus("实时数据解析失败", "rt-err");
    }
  };

  state.source.onerror = () => {
    setRealtimeStatus("实时连接异常，自动重连中", "rt-err");
  };
}

function toggleRealtime(forceOn = null) {
  if (typeof forceOn === "boolean") {
    state.realtimeOn = forceOn;
  } else {
    state.realtimeOn = !state.realtimeOn;
  }

  if (state.realtimeOn) {
    realtimeToggle.textContent = "关闭实时";
    startRealtime();
  } else {
    realtimeToggle.textContent = "开启实时";
    stopRealtime();
    setRealtimeStatus("实时未开启", "rt-off");
  }
}

function bindDataActions() {
  refreshBtn.addEventListener("click", () => {
    refreshStatic().catch((err) => showToast(err.message));
  });

  realtimeToggle.addEventListener("click", () => {
    toggleRealtime();
  });

  liveIdSelect.addEventListener("change", () => {
    refreshStatic().catch((err) => showToast(err.message));
    if (state.realtimeOn) {
      startRealtime();
    }
  });
}

window.addEventListener("resize", () => {
  trendChart.resize();
  heatmapChart.resize();
  funnelChart.resize();
  sentimentChart.resize();
});

function init() {
  bindPageNav();
  bindGlobalSearch();
  bindOperationActions();
  bindSettingActions();
  bindDataActions();

  renderOverview();
  renderOperation();
  renderSetting();

  setInterval(renderOverview, 5000);

  setRealtimeStatus("实时未开启", "rt-off");
  refreshStatic().catch((err) => showToast(err.message));

  switchPage(state.settings.defaultPage);
}

init();

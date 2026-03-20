const trendChart = echarts.init(document.getElementById("trendChart"));
const heatmapChart = echarts.init(document.getElementById("heatmapChart"));
const funnelChart = echarts.init(document.getElementById("funnelChart"));
const sentimentChart = echarts.init(document.getElementById("sentimentChart"));

const liveIdSelect = document.getElementById("liveId");
const refreshBtn = document.getElementById("refreshBtn");
const realtimeToggle = document.getElementById("realtimeToggle");
const realtimeStatus = document.getElementById("realtimeStatus");
const collectorStatus = document.getElementById("collectorStatus");
const collectorPipelineLiveId = document.getElementById("collectorPipelineLiveId");
const collectorWebRid = document.getElementById("collectorWebRid");
const collectorAnchorId = document.getElementById("collectorAnchorId");
const collectorInspectBtn = document.getElementById("collectorInspectBtn");
const collectorAudienceBtn = document.getElementById("collectorAudienceBtn");
const collectorStartBtn = document.getElementById("collectorStartBtn");
const collectorStopBtn = document.getElementById("collectorStopBtn");
const collectorRuntimeText = document.getElementById("collectorRuntimeText");
const collectorRoomId = document.getElementById("collectorRoomId");
const collectorAnchorText = document.getElementById("collectorAnchorText");
const collectorEventTotal = document.getElementById("collectorEventTotal");
const collectorCurrentOnline = document.getElementById("collectorCurrentOnline");
const collectorLogList = document.getElementById("collectorLogList");
const collectorAudienceBody = document.getElementById("collectorAudienceBody");
const collectorEventBody = document.getElementById("collectorEventBody");
const dashboardSourceHint = document.getElementById("dashboardSourceHint");
const trendCardTitle = document.getElementById("trendCardTitle");
const heatmapCardTitle = document.getElementById("heatmapCardTitle");
const funnelCardTitle = document.getElementById("funnelCardTitle");
const sentimentCardTitle = document.getElementById("sentimentCardTitle");
const topUsersCardTitle = document.getElementById("topUsersCardTitle");
const secondaryListTitle = document.getElementById("secondaryListTitle");

const topNavItems = Array.from(document.querySelectorAll(".top-nav-item[data-top-page]"));
const topPages = {
  data: document.getElementById("top-page-data"),
  ability: document.getElementById("top-page-ability"),
  docs: document.getElementById("top-page-docs"),
  market: document.getElementById("top-page-market"),
};

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
  currentTopPage: "data",
  currentPage: "data",
  realtimeOn: false,
  source: null,
  collectorPollTimer: null,
  autoRealtimeOnEnterData: false,
  dashboardSource: "demo",
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

const COLLECTOR_AUDIENCE_LIMIT = 30;

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
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(data.error || `请求失败: ${url}`);
    err.status = resp.status;
    throw err;
  }
  return data;
}

async function postJSON(url, body = {}) {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok || data.ok === false) {
    const err = new Error(data.error || `请求失败: ${url}`);
    err.status = resp.status;
    throw err;
  }
  return data;
}

function switchTopPage(topPage) {
  if (!topPages[topPage]) return;

  state.currentTopPage = topPage;
  topNavItems.forEach((item) => item.classList.toggle("active", item.dataset.topPage === topPage));

  Object.entries(topPages).forEach(([name, el]) => {
    if (!el) return;
    el.classList.toggle("hidden", name !== topPage);
  });

  if (topPage !== "data" && state.realtimeOn) {
    toggleRealtime(false);
  }

  if (topPage === "data") {
    window.dispatchEvent(new Event("resize"));
  }
}

function bindTopNav() {
  topNavItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      switchTopPage(item.dataset.topPage);
    });
  });
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
      switchTopPage("data");
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

function setDashboardMode(mode, meta = {}) {
  state.dashboardSource = mode;
  if (mode === "collector") {
    const detail = [];
    if (meta.anchor_nickname) detail.push(meta.anchor_nickname);
    if (meta.room_id) detail.push(`room_id ${meta.room_id}`);
    if (meta.updated_at) detail.push(`更新于 ${fmtCollectorTime(meta.updated_at)}`);
    dashboardSourceHint.textContent = `数据来源：网页采集事件${detail.length ? `，${detail.join(" · ")}` : ""}`;
    trendCardTitle.textContent = "在线变化";
    heatmapCardTitle.textContent = "互动热度";
    funnelCardTitle.textContent = "直播互动漏斗";
    sentimentCardTitle.textContent = "评论情感分布";
    topUsersCardTitle.textContent = "关键互动用户";
    secondaryListTitle.textContent = "采集洞察";
    return;
  }

  dashboardSourceHint.textContent = "按当前直播间显示";
  trendCardTitle.textContent = "流量趋势";
  heatmapCardTitle.textContent = "互动趋势";
  funnelCardTitle.textContent = "电商转化漏斗";
  sentimentCardTitle.textContent = "情感占比";
  topUsersCardTitle.textContent = "关键互动用户";
  secondaryListTitle.textContent = "推荐结果示例（u0001）";
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

function renderFunnelStages(stages) {
  funnelChart.setOption({
    tooltip: { trigger: "item", formatter: "{b}: {c}" },
    series: [
      {
        type: "funnel",
        left: "10%",
        top: 20,
        bottom: 20,
        width: "80%",
        data: stages.map((item) => ({
          value: Number(item.value || 0),
          name: item.name || "-",
        })),
      },
    ],
  });
}

function renderSentimentSummary(summary = {}, commentCount = 0) {
  const positive = Number(summary.positive || 0);
  const neutral = Number(summary.neutral || 0);
  const negative = Number(summary.negative || 0);
  const total = positive + neutral + negative;
  const data = total
    ? [
        { name: "正向", value: positive },
        { name: "中性", value: neutral },
        { name: "负向", value: negative },
      ]
    : [{ name: commentCount ? "未命中词典" : "暂无评论", value: 1 }];

  sentimentChart.setOption({
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: "60%",
        data,
      },
    ],
  });
}

function renderTopUsers(users) {
  const body = document.getElementById("topUsersBody");
  body.innerHTML = "";
  if (!users.length) {
    body.innerHTML = '<tr><td colspan="5" class="collector-empty-cell">暂无数据</td></tr>';
    return;
  }
  users.forEach((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.user_id || "-"}</td>
      <td>${fmtNum(u.comments)}</td>
      <td>${fmtNum(u.likes)}</td>
      <td>${fmtNum(u.gifts)}</td>
      <td>${fmtNum(u.score)}</td>
    `;
    body.appendChild(tr);
  });
}

function renderInsightList(items) {
  const list = document.getElementById("recommendList");
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = "<li>暂无数据</li>";
    return;
  }
  items.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
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
  renderFunnelStages([
    { value: f.exposure, name: "曝光" },
    { value: f.click, name: "点击" },
    { value: f.add_cart, name: "加购" },
    { value: f.purchase, name: "购买" },
  ]);
}

async function loadSentiment(liveId) {
  const data = await getJSON(`/api/sentiment/${liveId}`);
  renderSentimentSummary(data.summary || {}, 0);
}

async function loadTopUsers(liveId) {
  const data = await getJSON(`/api/interaction/top-users/${liveId}`);
  renderTopUsers(data.users || []);
}

async function loadRecommend() {
  const data = await getJSON("/api/recommend/u0001?top_n=5");
  renderInsightList(
    (data.items || []).map(
      (item) => `${item.name}（${item.reason}，匹配分=${Number(item.score).toFixed(3)}）`
    )
  );
}

function renderCollectorAnalytics(data) {
  const overview = data.overview || {};
  const trend = data.trend || {};
  const heatmap = data.heatmap || {};
  const funnel = data.funnel || {};
  const sentiment = data.sentiment || {};
  const topUsers = data.top_users || {};
  const insights = data.insights || {};

  renderKpi({
    online: overview.online_users,
    likes: overview.likes,
    gifts: overview.gifts,
    gmv: overview.gift_value,
  });
  renderTrendFromPoints(trend.points || [], "ts", "online_users");
  renderHeatmapFromPairs(
    (heatmap.items || []).map((item) => item.minute_slot),
    (heatmap.items || []).map((item) => item.interaction_count)
  );
  renderFunnelStages(funnel.stages || []);
  renderSentimentSummary(sentiment.summary || {}, sentiment.comment_count || 0);
  renderTopUsers(topUsers.users || []);
  renderInsightList(insights.items || []);
  setDashboardMode("collector", data.meta || {});
}

async function tryLoadCollectorAnalytics(liveId) {
  try {
    const data = await getJSON(`/api/collector/web/analytics/${liveId}?limit=30`);
    renderCollectorAnalytics(data);
    return true;
  } catch (err) {
    if (err.status === 404) {
      return false;
    }
    throw err;
  }
}

async function loadDemoDashboard(liveId) {
  await Promise.all([
    loadOverview(liveId),
    loadTrend(liveId),
    loadHeatmap(liveId),
    loadFunnel(liveId),
    loadSentiment(liveId),
    loadTopUsers(liveId),
    loadRecommend(),
  ]);
  setDashboardMode("demo");
}

async function refreshStatic() {
  const liveId = liveIdSelect.value;
  const usedCollector = await tryLoadCollectorAnalytics(liveId);
  if (usedCollector) {
    return;
  }
  await loadDemoDashboard(liveId);
}

function applyRealtimePayload(payload) {
  if (state.dashboardSource === "collector") {
    return;
  }
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
    collectorPipelineLiveId.textContent = liveIdSelect.value;
    refreshStatic().catch((err) => showToast(err.message));
    if (state.realtimeOn) {
      startRealtime();
    }
  });
}

function fmtCollectorTime(value) {
  const raw = String(value || "");
  if (!raw) return "-";
  if (raw.includes("T")) {
    return raw.slice(11, 19);
  }
  return raw.slice(0, 19);
}

function setCollectorStatus(text, cls) {
  collectorStatus.textContent = text;
  collectorStatus.className = `rt-status ${cls}`;
}

function getCollectorEventText(item) {
  if (!item) return "-";
  if (item.comment) return item.comment;
  if (Number(item.gift_value || 0) > 0) {
    const label = item.gift_name || "礼物";
    return `${label} ¥${Number(item.gift_value).toFixed(2)}`;
  }
  if (Number(item.like_count || 0) > 0) {
    return `点赞 x${fmtNum(item.like_count)}`;
  }
  if (item.stats_text) return item.stats_text;
  if (Number(item.online_users || 0) > 0 && item.event_type === "room_stats") {
    return `在线 ${fmtNum(item.online_users)}`;
  }
  if (item.action_description) return item.action_description;
  if (item.status_code) return `状态码 ${item.status_code}`;
  return "-";
}

function renderCollectorLogs(items) {
  collectorLogList.innerHTML = "";
  if (!items.length) {
    collectorLogList.innerHTML = '<li class="collector-empty">暂无日志</li>';
    return;
  }
  items
    .slice()
    .reverse()
    .forEach((item) => {
      const li = document.createElement("li");
      li.className = "collector-log-item";
      li.innerHTML = `
        <span class="collector-log-meta">${fmtCollectorTime(item.ts)} · ${item.type}</span>
        <span class="collector-log-text">${item.message}</span>
      `;
      collectorLogList.appendChild(li);
    });
}

function renderCollectorAudience(items) {
  collectorAudienceBody.innerHTML = "";
  if (!items.length) {
    collectorAudienceBody.innerHTML = '<tr><td colspan="4" class="collector-empty-cell">暂无数据</td></tr>';
    return;
  }
  items.slice(0, COLLECTOR_AUDIENCE_LIMIT).forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.rank ?? "-"}</td>
      <td>${item.user_id || "-"}</td>
      <td>${item.nickname || "-"}</td>
      <td>${item.display_id || "-"}</td>
    `;
    collectorAudienceBody.appendChild(tr);
  });
}

function renderCollectorEvents(items) {
  collectorEventBody.innerHTML = "";
  if (!items.length) {
    collectorEventBody.innerHTML = '<tr><td colspan="4" class="collector-empty-cell">暂无事件</td></tr>';
    return;
  }
  items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${fmtCollectorTime(item.event_time)}</td>
      <td>${item.event_type || "-"}</td>
      <td>${item.user_name || item.user_id || "-"}</td>
      <td>${getCollectorEventText(item)}</td>
    `;
    collectorEventBody.appendChild(tr);
  });
}

function renderCollectorSnapshot(data) {
  const runtime = data.runtime || {};
  const collector = data.collector || {};
  const missingParts = [
    ...(runtime.missing_dependencies || []),
    ...(runtime.missing_files || []),
  ];

  collectorPipelineLiveId.textContent = collector.live_id || liveIdSelect.value;
  collectorRuntimeText.textContent = runtime.available ? "已就绪" : `待补齐：${missingParts.join(", ") || "环境不可用"}`;
  collectorRoomId.textContent = collector.room_id || "-";
  collectorAnchorText.textContent =
    collector.anchor_nickname || collector.status_text
      ? `${collector.anchor_nickname || "未知主播"} / ${collector.status_text || "未知状态"}`
      : "-";
  collectorEventTotal.textContent = fmtNum(collector.total_events || 0);
  collectorCurrentOnline.textContent = fmtNum(collector.current_online_users || 0);

  if (collector.running) {
    setCollectorStatus("采集中", "rt-on");
  } else if (collector.last_error) {
    setCollectorStatus("采集异常", "rt-err");
  } else if (!runtime.available) {
    setCollectorStatus("依赖未就绪", "rt-warn");
  } else if (collector.web_rid) {
    setCollectorStatus("已连接配置", "rt-warn");
  } else {
    setCollectorStatus("未启动", "rt-off");
  }

  renderCollectorLogs(data.recent_logs || []);
  renderCollectorAudience(data.audience || []);
  renderCollectorEvents(data.recent_events || []);
}

async function loadCollectorSnapshot(silent = false) {
  try {
    const data = await getJSON("/api/collector/web/snapshot?limit_events=12&limit_logs=16");
    renderCollectorSnapshot(data);
    const collector = data.collector || {};
    const selectedLiveId = liveIdSelect.value;
    const shouldSyncDashboard =
      collector.live_id === selectedLiveId &&
      (collector.total_events > 0 || collector.running || collector.room_id);
    const shouldResetDashboard = state.dashboardSource === "collector" && collector.live_id !== selectedLiveId;
    if (shouldSyncDashboard || shouldResetDashboard) {
      refreshStatic().catch((err) => {
        if (!silent) {
          showToast(err.message);
        }
      });
    }
  } catch (err) {
    setCollectorStatus("采集状态获取失败", "rt-err");
    if (!silent) {
      showToast(err.message);
    }
  }
}

async function inspectCollectorRoom() {
  const webRid = collectorWebRid.value.trim();
  if (!webRid) {
    showToast("请先输入抖音 Web RID");
    return;
  }
  try {
    const url = `/api/collector/web/inspect?live_id=${encodeURIComponent(liveIdSelect.value)}&web_rid=${encodeURIComponent(webRid)}`;
    const data = await getJSON(url);
    renderCollectorSnapshot(data.snapshot || {});
    const room = data.room || {};
    showToast(`直播状态：${room.status_text || "已查询"}`);
  } catch (err) {
    showToast(err.message);
    loadCollectorSnapshot(true);
  }
}

async function fetchCollectorAudience() {
  const webRid = collectorWebRid.value.trim();
  const anchorId = collectorAnchorId.value.trim();
  if (!webRid || !anchorId) {
    showToast("请先输入 Web RID 和主播 ID");
    return;
  }
  try {
    const url = `/api/collector/web/audience?live_id=${encodeURIComponent(liveIdSelect.value)}&web_rid=${encodeURIComponent(webRid)}&anchor_id=${encodeURIComponent(anchorId)}`;
    const data = await getJSON(url);
    renderCollectorSnapshot(data.snapshot || {});
    const total = data.items?.length || 0;
    const shown = Math.min(total, COLLECTOR_AUDIENCE_LIMIT);
    showToast(`已获取观众榜，共 ${total} 条，页面显示前 ${shown} 条`);
  } catch (err) {
    showToast(err.message);
    loadCollectorSnapshot(true);
  }
}

async function startCollector() {
  const webRid = collectorWebRid.value.trim();
  const anchorId = collectorAnchorId.value.trim();
  if (!webRid) {
    showToast("请先输入抖音 Web RID");
    return;
  }
  try {
    const data = await postJSON("/api/collector/web/start", {
      live_id: liveIdSelect.value,
      web_rid: webRid,
      anchor_id: anchorId,
    });
    renderCollectorSnapshot(data.snapshot || {});
    refreshStatic().catch(() => {});
    showToast(`已启动网页采集：${liveIdSelect.value} <- ${webRid}`);
  } catch (err) {
    showToast(err.message);
    loadCollectorSnapshot(true);
  }
}

async function stopCollector() {
  try {
    const data = await postJSON("/api/collector/web/stop");
    renderCollectorSnapshot(data.snapshot || {});
    refreshStatic().catch(() => {});
    showToast("网页采集已停止");
  } catch (err) {
    showToast(err.message);
  }
}

function bindCollectorActions() {
  collectorInspectBtn.addEventListener("click", () => {
    inspectCollectorRoom();
  });

  collectorAudienceBtn.addEventListener("click", () => {
    fetchCollectorAudience();
  });

  collectorStartBtn.addEventListener("click", () => {
    startCollector();
  });

  collectorStopBtn.addEventListener("click", () => {
    stopCollector();
  });
}

function ensureCollectorPolling() {
  if (state.collectorPollTimer) return;
  state.collectorPollTimer = window.setInterval(() => {
    loadCollectorSnapshot(true);
  }, 3000);
}

window.addEventListener("resize", () => {
  trendChart.resize();
  heatmapChart.resize();
  funnelChart.resize();
  sentimentChart.resize();
});

function init() {
  bindTopNav();
  bindPageNav();
  bindGlobalSearch();
  bindOperationActions();
  bindSettingActions();
  bindDataActions();
  bindCollectorActions();

  renderOverview();
  renderOperation();
  renderSetting();

  setInterval(renderOverview, 5000);

  setRealtimeStatus("实时未开启", "rt-off");
  collectorPipelineLiveId.textContent = liveIdSelect.value;
  refreshStatic().catch((err) => showToast(err.message));
  loadCollectorSnapshot(true);
  ensureCollectorPolling();

  switchTopPage("data");
  switchPage(state.settings.defaultPage);
}

init();


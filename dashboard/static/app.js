// ============================================================
// Quantum Stone Capital — Dashboard Frontend
// ============================================================

const wsDot = document.getElementById("ws-dot");
const wsLabel = document.getElementById("ws-label");
const clock = document.getElementById("clock");
const priceGrid = document.getElementById("price-grid");
const priceSourcePill = document.getElementById("price-source-pill");
const accountsGrid = document.getElementById("accounts-grid");
const decisionsBody = document.getElementById("decisions-body");
const decisionsCount = document.getElementById("decisions-count");
const footerInfo = document.getElementById("footer-info");

// Metrics
const elEquity = document.getElementById("metric-equity");
const elEquitySub = document.getElementById("metric-equity-sub");
const elDailyPnl = document.getElementById("metric-daily-pnl");
const elDailyPnlSub = document.getElementById("metric-daily-pnl-sub");
const elPositions = document.getElementById("metric-positions");
const elWinRate = document.getElementById("metric-winrate");
const elPf = document.getElementById("metric-pf");

// Chart
let equityChart = null;
const equityHistory = [];

// ---------- formatting ----------

function fmtNum(v, decimals = 2) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return Number(v).toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

function fmtMoney(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "";
    return sign + "$" + Math.abs(v).toLocaleString("en-US", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });
}

function fmtMoneyShort(v) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    const abs = Math.abs(v);
    const sign = v < 0 ? "-" : "";
    if (abs >= 1e6) return sign + "$" + (abs / 1e6).toFixed(2) + "M";
    if (abs >= 1e3) return sign + "$" + (abs / 1e3).toFixed(1) + "K";
    return sign + "$" + abs.toFixed(2);
}

function fmtPrice(sym, price) {
    if (price === null || price === undefined || isNaN(price)) return "—";
    if (sym === "BTCUSD" || sym === "XAUUSD" || sym === "SPY") return price.toFixed(2);
    if (sym === "ETHUSD" || sym === "SOLUSD") return price.toFixed(2);
    if (price < 10) return price.toFixed(5);
    return price.toFixed(4);
}

function fmtPct(v, decimals = 2) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    return (v * 100).toFixed(decimals) + "%";
}

function fmtTime(ts) {
    if (!ts) return "—";
    try { return new Date(ts).toLocaleTimeString(); } catch { return "—"; }
}

function tagClass(v) {
    return "tag " + String(v || "").replace(/[^a-z_]/g, "");
}

// ---------- render: prices ----------

function renderPrices(prices) {
    const syms = Object.keys(prices).sort();
    if (syms.length === 0) {
        priceGrid.innerHTML = '<div class="empty">Waiting for live data…</div>';
        priceSourcePill.textContent = "offline";
        return;
    }
    const sources = new Set(Object.values(prices).map(p => p.source));
    priceSourcePill.textContent = Array.from(sources).join(" · ");

    priceGrid.innerHTML = syms.map(sym => {
        const p = prices[sym];
        const spread = p.ask > 0 && p.bid > 0 ? (p.ask - p.bid) : 0;
        return `
            <div class="price-card">
                <div class="symbol">
                    <span>${sym}</span>
                    <span class="source-tag">${p.source || "?"}</span>
                </div>
                <div class="value">${fmtPrice(sym, p.mid)}</div>
                <div class="spread">bid ${fmtPrice(sym, p.bid)} · ask ${fmtPrice(sym, p.ask)}</div>
            </div>
        `;
    }).join("");
}

// ---------- render: accounts ----------

function renderAccounts(accounts) {
    const names = Object.keys(accounts);
    if (names.length === 0) {
        accountsGrid.innerHTML = '<div class="empty">No accounts configured</div>';
        return;
    }
    accountsGrid.innerHTML = names.map(name => {
        const a = accounts[name];
        const isProp = a.type === "prop_firm";
        const dailyLossPct = (a.daily_loss_pct || 0) * 100;
        const ddPct = (a.drawdown_pct || 0) * 100;
        const dailyMaxPct = (a.max_daily_loss || 0.03) * 100;
        const ddMaxPct = (a.max_drawdown || 0.10) * 100;
        const dailyWidth = Math.min(100, dailyMaxPct > 0 ? (dailyLossPct / dailyMaxPct) * 100 : 0);
        const ddWidth = Math.min(100, ddMaxPct > 0 ? (ddPct / ddMaxPct) * 100 : 0);
        const dailyColor = dailyWidth >= 80 ? "danger" : (dailyWidth >= 50 ? "warn" : "");
        const ddColor = ddWidth >= 80 ? "danger" : (ddWidth >= 50 ? "warn" : "");
        const pnlClass = a.total_pnl > 0 ? "pos" : (a.total_pnl < 0 ? "neg" : "");
        const badgeClass = isProp ? "badge prop" : "badge";
        const cardClass = isProp ? "account-card prop_firm" : "account-card retail";

        return `
            <div class="${cardClass}">
                <div class="account-header">
                    <h3>${a.name}</h3>
                    <span class="${badgeClass}">${a.type.replace("_", " ")}</span>
                </div>
                <div class="stats">
                    <div class="stat">
                        <div class="label">Balance</div>
                        <div class="val">${fmtMoneyShort(a.balance)}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Equity</div>
                        <div class="val">${fmtMoneyShort(a.equity)}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Total P&amp;L</div>
                        <div class="val ${pnlClass}">${fmtMoneyShort(a.total_pnl)}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Free Margin</div>
                        <div class="val">${fmtMoneyShort(a.free_margin)}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Open / Closed</div>
                        <div class="val">${a.open_positions} / ${a.closed_positions}</div>
                    </div>
                    <div class="stat">
                        <div class="label">Risk / Trade</div>
                        <div class="val">${fmtPct(a.max_risk_per_trade, 1)}</div>
                    </div>
                </div>
                <div class="risk-row">
                    <div class="risk-item">
                        <div class="risk-label">
                            <span>Daily Loss</span>
                            <span class="val">${dailyLossPct.toFixed(2)}% / ${dailyMaxPct.toFixed(0)}%</span>
                        </div>
                        <div class="progress">
                            <div class="bar ${dailyColor}" style="width:${dailyWidth}%"></div>
                        </div>
                    </div>
                    <div class="risk-item">
                        <div class="risk-label">
                            <span>Drawdown</span>
                            <span class="val">${ddPct.toFixed(2)}% / ${ddMaxPct.toFixed(0)}%</span>
                        </div>
                        <div class="progress">
                            <div class="bar ${ddColor}" style="width:${ddWidth}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

// ---------- render: decisions ----------

function renderDecisions(decisions) {
    if (!decisions || decisions.length === 0) {
        decisionsBody.innerHTML = '<tr><td colspan="7" class="empty">No decisions yet — waiting for the brain loop…</td></tr>';
        decisionsCount.textContent = "0";
        return;
    }
    decisionsCount.textContent = decisions.length;
    decisionsBody.innerHTML = decisions.slice().reverse().slice(0, 50).map(d => {
        const reasons = (d.reasons || []).join(", ") || "—";
        return `
            <tr>
                <td>${fmtTime(d.timestamp)}</td>
                <td>${d.symbol}</td>
                <td><span class="${tagClass(d.decision)}">${d.decision}</span></td>
                <td><span class="${tagClass(d.direction)}">${d.direction}</span></td>
                <td>${((d.confidence || 0) * 100).toFixed(0)}%</td>
                <td>${d.strategy_name || "—"}</td>
                <td style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${reasons}</td>
            </tr>
        `;
    }).join("");
}

// ---------- render: top metrics ----------

function renderMetrics(accounts, decisions, prices) {
    const names = Object.keys(accounts);
    let totalEquity = 0;
    let totalDaily = 0;
    let totalOpen = 0;
    for (const n of names) {
        const a = accounts[n];
        totalEquity += (a.equity || 0);
        totalDaily += (a.daily_pnl || 0);
        totalOpen += (a.open_positions || 0);
    }

    elEquity.textContent = fmtMoney(totalEquity);
    elEquitySub.textContent = "across " + names.length + " accounts";

    elDailyPnl.textContent = fmtMoney(totalDaily);
    elDailyPnl.className = "metric-value " + (totalDaily > 0 ? "pos" : (totalDaily < 0 ? "neg" : ""));
    elDailyPnlSub.textContent = totalDaily > 0 ? "winning day" : (totalDaily < 0 ? "losing day" : "flat");

    elPositions.textContent = String(totalOpen);

    // Win rate and PF from decisions (no trades yet → placeholders)
    const trades = (decisions || []).filter(d => d.decision === "trade");
    if (trades.length === 0) {
        elWinRate.textContent = "—";
        elPf.textContent = "—";
    } else {
        // Placeholder: real win rate requires closed trades
        elWinRate.textContent = "—";
        elPf.textContent = "—";
    }
}

// ---------- render: equity chart ----------

function renderEquityChart(accounts) {
    const now = Date.now();
    let equity = 0;
    for (const n of Object.keys(accounts)) equity += (accounts[n].equity || 0);
    equityHistory.push({ t: now, y: equity });
    if (equityHistory.length > 200) equityHistory.shift();

    const labels = equityHistory.map(p => new Date(p.t).toLocaleTimeString());
    const data = equityHistory.map(p => p.y);

    if (equityChart) {
        equityChart.data.labels = labels;
        equityChart.data.datasets[0].data = data;
        equityChart.update("none");
        return;
    }

    const ctx = document.getElementById("equity-chart").getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, "rgba(167, 139, 250, 0.4)");
    gradient.addColorStop(1, "rgba(167, 139, 250, 0.0)");

    equityChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Combined Equity",
                data,
                borderColor: "#a78bfa",
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: "#a78bfa",
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#151a2b",
                    borderColor: "#232a44",
                    borderWidth: 1,
                    titleColor: "#ffffff",
                    bodyColor: "#d0d6e6",
                    callbacks: {
                        label: (ctx) => fmtMoney(ctx.parsed.y),
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: "rgba(35, 42, 68, 0.4)" },
                    ticks: { color: "#5a637f", font: { size: 10 }, maxTicksLimit: 6 },
                },
                y: {
                    grid: { color: "rgba(35, 42, 68, 0.4)" },
                    ticks: {
                        color: "#5a637f", font: { size: 10 },
                        callback: (v) => fmtMoneyShort(v),
                    },
                },
            },
        },
    });
}

// ---------- render: calendar heatmap ----------

function renderCalendar(accounts) {
    // Aggregate total P&L per day. Since we don't have trade history yet,
    // show today's total across accounts and mark past days as empty.
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    let totalDaily = 0;
    for (const n of Object.keys(accounts)) totalDaily += (accounts[n].daily_pnl || 0);

    const headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    let html = headers.map(h => `<div class="cal-header">${h}</div>`).join("");

    for (let i = 0; i < firstDay; i++) html += '<div class="cal-cell empty"></div>';

    for (let day = 1; day <= daysInMonth; day++) {
        const isToday = (day === now.getDate());
        let cls = "cal-cell";
        let pnlText = "";

        if (isToday && totalDaily !== 0) {
            cls += totalDaily > 0 ? " win" : " loss";
            pnlText = fmtMoneyShort(totalDaily);
        } else {
            cls += " flat";
        }
        if (isToday) cls += " today";

        html += `
            <div class="${cls}">
                <div class="day">${day}</div>
                ${pnlText ? `<div class="pnl">${pnlText}</div>` : ""}
            </div>
        `;
    }

    document.getElementById("calendar").innerHTML = html;
}


// ---------- render: routing stats ----------

function renderRouting(stats) {
    const el = document.getElementById("routing-stats");
    if (!el) return;
    if (!stats) {
        el.innerHTML = '<div class="empty">No routing data yet</div>';
        return;
    }
    const s = stats;
    el.innerHTML = `
        <div class="routing-stat">
            <div class="label">Total</div>
            <div class="val">${s.total || 0}</div>
        </div>
        <div class="routing-stat">
            <div class="label">Personal</div>
            <div class="val blue">${s.personal || 0}</div>
        </div>
        <div class="routing-stat">
            <div class="label">Prop</div>
            <div class="val amber">${s.prop || 0}</div>
        </div>
        <div class="routing-stat">
            <div class="label">Blocked</div>
            <div class="val red">${s.blocked || 0}</div>
        </div>
        <div class="routing-stat">
            <div class="label">Personal Rule</div>
            <div class="val blue">${(s.by_rule_source && s.by_rule_source.personal) || 0}</div>
        </div>
        <div class="routing-stat">
            <div class="label">Prop Rule</div>
            <div class="val amber">${(s.by_rule_source && s.by_rule_source.prop_firm) || 0}</div>
        </div>
    `;
}

// ---------- WebSocket ----------

let ws = null;
let reconnectTimer = null;

function connect() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = proto + "//" + window.location.host + "/ws";
    ws = new WebSocket(url);

    ws.onopen = () => {
        wsDot.className = "dot live";
        wsLabel.textContent = "live";
    };

    ws.onmessage = (ev) => {
        try {
            const data = JSON.parse(ev.data);
            const prices = data.prices || {};
            const accounts = data.accounts || {};
            const decisions = data.recent_decisions || [];

            renderPrices(prices);
            renderAccounts(accounts);
            renderMetrics(accounts, decisions, prices);
            renderEquityChart(accounts);
            renderCalendar(accounts);
            renderDecisions(decisions);
            renderRouting(data.routing_stats);

            footerInfo.textContent = "Updated " + new Date(data.now).toLocaleTimeString() +
                " · Started " + new Date(data.started_at).toLocaleString();
        } catch (e) {
            console.error("parse error", e);
        }
    };

    ws.onclose = () => {
        wsDot.className = "dot dead";
        wsLabel.textContent = "reconnecting…";
        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

// ---------- Clock ----------

setInterval(() => {
    clock.textContent = new Date().toLocaleTimeString();
}, 1000);

// ---------- Boot ----------

connect();

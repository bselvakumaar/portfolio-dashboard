from app.config import get_settings


def render_dashboard_html() -> str:
    settings = get_settings()
    default_tickers = ",".join(settings.default_tickers)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Steward Quant Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg-1: #08141e;
      --bg-2: #132938;
      --panel: #0f2230;
      --panel-2: #15364a;
      --accent: #23c28f;
      --accent-2: #f9a825;
      --text: #e7f2f8;
      --muted: #9ab2c2;
      --danger: #ff6b6b;
      --ok: #42d594;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: "Segoe UI", Tahoma, sans-serif;
      background:
        radial-gradient(1200px 700px at 92% -10%, #1a435a 0%, transparent 40%),
        radial-gradient(1000px 500px at -20% 130%, #234739 0%, transparent 52%),
        linear-gradient(135deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
    }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 20px; }}
    .title {{ font-size: 30px; font-weight: 700; margin: 6px 0; }}
    .subtitle {{ color: var(--muted); margin-bottom: 14px; }}
    .panel {{
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    .section-title {{ font-weight: 700; margin-bottom: 10px; }}
    .controls {{
      display: grid;
      grid-template-columns: 2.2fr 0.8fr 0.8fr auto auto;
      gap: 10px;
      align-items: end;
    }}
    label {{ display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }}
    input, textarea {{
      width: 100%;
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.13);
      border-radius: 10px;
      color: var(--text);
      padding: 10px;
      font-size: 14px;
    }}
    textarea {{ min-height: 110px; resize: vertical; }}
    button {{
      border: none;
      border-radius: 10px;
      padding: 11px 14px;
      font-weight: 700;
      cursor: pointer;
      background: linear-gradient(120deg, var(--accent), #36a9cd);
      color: #06211e;
    }}
    button.alt {{
      background: linear-gradient(120deg, var(--accent-2), #f6d365);
      color: #2a1b00;
    }}
    .status {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
    .grid6 {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }}
    .metric {{
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      padding: 12px;
    }}
    .metric .k {{ color: var(--muted); font-size: 12px; }}
    .metric .v {{ margin-top: 7px; font-size: 22px; font-weight: 700; }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 8px 6px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .cards {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
    .card {{
      background: var(--panel-2);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      padding: 10px;
    }}
    .card .ticker {{ font-weight: 700; font-size: 16px; }}
    .tag {{
      border-radius: 7px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 700;
      display: inline-block;
    }}
    .strong_buy {{ background: rgba(66,213,148,0.2); color: #66f0af; }}
    .buy {{ background: rgba(35,194,143,0.2); color: #6debc4; }}
    .hold {{ background: rgba(249,168,37,0.2); color: #ffcf70; }}
    .avoid {{ background: rgba(255,107,107,0.2); color: #ffa0a0; }}
    @media (max-width: 1100px) {{
      .controls {{ grid-template-columns: 1fr; }}
      .grid6 {{ grid-template-columns: repeat(3, 1fr); }}
      .grid2, .grid3 {{ grid-template-columns: 1fr; }}
      .cards {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">Steward Quant Intelligence Dashboard</div>
    <div class="subtitle">Portfolio + Market Pulse + Top Picks + Multi-Horizon Projections</div>

    <div class="panel">
      <div class="section-title">Run Dashboard</div>
      <div class="controls">
        <div>
          <label>Tickers</label>
          <input id="tickers" value="{default_tickers}" />
        </div>
        <div>
          <label>Top Picks</label>
          <input id="topN" type="number" min="1" max="20" value="5" />
        </div>
        <div>
          <label>Capital (INR)</label>
          <input id="capital" type="number" min="1" value="1000000" />
        </div>
        <button id="runBtn">Run Dashboard</button>
        <button id="pulseBtn" class="alt">Load Market Pulse</button>
      </div>
      <div class="status" id="status">Ready.</div>
    </div>

    <div class="grid6">
      <div class="metric"><div class="k">Coverage</div><div class="v" id="mCoverage">-</div></div>
      <div class="metric"><div class="k">Valid</div><div class="v" id="mValid">-</div></div>
      <div class="metric"><div class="k">Avg Score</div><div class="v" id="mScore">-</div></div>
      <div class="metric"><div class="k">Avg Pred 21d</div><div class="v" id="mRet">-</div></div>
      <div class="metric"><div class="k">Portfolio PnL 21d</div><div class="v" id="mPnl">-</div></div>
      <div class="metric"><div class="k">Diversification</div><div class="v" id="mDiv">-</div></div>
    </div>

    <div class="panel">
      <div class="section-title">Top Picks Recommendations</div>
      <div id="pickCards" class="cards"></div>
    </div>

    <div class="grid2">
      <div class="panel">
        <div class="section-title">Top Picks Projection Board</div>
        <table id="projectionTable">
          <thead><tr><th>Ticker</th><th>3D%</th><th>5D%</th><th>7D%</th><th>21D%</th><th>Rec</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="panel">
        <div class="section-title">Synthetic Portfolio</div>
        <table id="portfolioTable">
          <thead><tr><th>Ticker</th><th>Weight</th><th>Allocation</th><th>Pred 21D%</th><th>Rec</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div class="grid2">
      <div class="panel">
        <div class="section-title">Top Gainers (10+)</div>
        <table id="gainersTable">
          <thead><tr><th>Ticker</th><th>Sector</th><th>Close</th><th>Day %</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="panel">
        <div class="section-title">Top Losers (10+)</div>
        <table id="losersTable">
          <thead><tr><th>Ticker</th><th>Sector</th><th>Close</th><th>Day %</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div class="panel">
      <div class="section-title">Sector-wise Performance</div>
      <table id="sectorTable">
        <thead><tr><th>Sector</th><th>Scripts</th><th>Avg Day %</th><th>Total Volume</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="panel">
      <div class="section-title">My Portfolio</div>
      <div class="grid2">
        <div>
          <label>Holdings (one per line: TICKER,QUANTITY,AVG_PRICE)</label>
          <textarea id="holdingsInput">RELIANCE.NS,20,2450
TCS.NS,12,3800
HDFCBANK.NS,30,1600
INFY.NS,18,1450
ICICIBANK.NS,25,1050</textarea>
          <button id="analyzePortfolioBtn">Analyze Portfolio</button>
          <div class="status" id="portfolioStatus">Portfolio analyzer ready.</div>
        </div>
        <div class="grid3">
          <div class="metric"><div class="k">Invested</div><div class="v" id="pInvested">-</div></div>
          <div class="metric"><div class="k">Current Value</div><div class="v" id="pCurrent">-</div></div>
          <div class="metric"><div class="k">Unrealized PnL</div><div class="v" id="pPnl">-</div></div>
          <div class="metric"><div class="k">Unrealized %</div><div class="v" id="pPnlPct">-</div></div>
          <div class="metric"><div class="k">Expected PnL 7D</div><div class="v" id="pExp7">-</div></div>
          <div class="metric"><div class="k">Expected PnL 21D</div><div class="v" id="pExp21">-</div></div>
        </div>
      </div>
      <table id="portfolioAnalyzeTable">
        <thead><tr><th>Ticker</th><th>Qty</th><th>Avg</th><th>LTP</th><th>Value</th><th>PnL</th><th>Score</th><th>Rec</th><th>7D%</th><th>21D%</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>

  <script>
    function asMoney(value) {{
      return new Intl.NumberFormat("en-IN", {{ style: "currency", currency: "INR", maximumFractionDigits: 0 }}).format(value || 0);
    }}
    function cls(rec) {{
      const k = (rec || "").toLowerCase();
      return k === "strong_buy" ? "strong_buy" : k;
    }}
    function setRows(tableId, rowsHtml) {{
      document.querySelector(`#${{tableId}} tbody`).innerHTML = rowsHtml.join("");
    }}

    function setMetrics(data) {{
      const ov = data.market_overview || {{}};
      const ps = (data.synthetic_portfolio || {{}}).summary || {{}};
      document.getElementById("mCoverage").textContent = ov.coverage_tickers ?? "-";
      document.getElementById("mValid").textContent = ov.valid_tickers ?? "-";
      document.getElementById("mScore").textContent = ov.average_steward_score ?? "-";
      document.getElementById("mRet").textContent = (ov.average_predicted_return_21d_pct ?? "-") + "%";
      document.getElementById("mPnl").textContent = asMoney(ps.expected_pnl_21d || 0);
      document.getElementById("mDiv").textContent = ps.diversification_index ?? "-";
    }}

    function setTopPickCards(data) {{
      const container = document.getElementById("pickCards");
      const top = data.top_picks || [];
      container.innerHTML = top.map(x => {{
        const p = x.prediction || {{}};
        return `<div class="card">
          <div class="ticker">${{x.ticker}}</div>
          <div>Score: <b>${{x.final_score}}</b></div>
          <div>Pred 21D: <b>${{p.predicted_return_pct}}%</b></div>
          <div>Confidence: <b>${{p.confidence}}</b></div>
          <div><span class="tag ${{cls(p.recommendation)}}">${{p.recommendation}}</span></div>
        </div>`;
      }}).join("");
    }}

    function setProjectionTable(data) {{
      const top = data.top_picks || [];
      const rows = top.map(x => {{
        const proj = ((x.prediction || {{}}).projection) || {{}};
        const rec = (x.prediction || {{}}).recommendation || "HOLD";
        return `<tr>
          <td>${{x.ticker}}</td>
          <td>${{proj.next_3d_return_pct ?? 0}}%</td>
          <td>${{proj.next_5d_return_pct ?? 0}}%</td>
          <td>${{proj.next_7d_return_pct ?? 0}}%</td>
          <td>${{proj.next_21d_return_pct ?? 0}}%</td>
          <td><span class="tag ${{cls(rec)}}">${{rec}}</span></td>
        </tr>`;
      }});
      setRows("projectionTable", rows);
    }}

    function setSyntheticPortfolio(data) {{
      const pos = ((data.synthetic_portfolio || {{}}).positions) || [];
      const rows = pos.map(x => `<tr>
        <td>${{x.ticker}}</td>
        <td>${{(x.weight * 100).toFixed(2)}}%</td>
        <td>${{asMoney(x.allocation)}}</td>
        <td>${{x.predicted_return_21d_pct}}%</td>
        <td><span class="tag ${{cls(x.recommendation)}}">${{x.recommendation}}</span></td>
      </tr>`);
      setRows("portfolioTable", rows);
    }}

    async function runDashboard() {{
      const tickers = document.getElementById("tickers").value.split(",").map(x => x.trim()).filter(Boolean);
      const top_n = parseInt(document.getElementById("topN").value || "5", 10);
      const capital = parseFloat(document.getElementById("capital").value || "1000000");
      const status = document.getElementById("status");
      status.textContent = "Running dashboard...";
      try {{
        const res = await fetch("/dashboard", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ tickers, top_n, capital, push_to_sheets: false }})
        }});
        if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
        const data = await res.json();
        setMetrics(data);
        setTopPickCards(data);
        setProjectionTable(data);
        setSyntheticPortfolio(data);
        status.textContent = "Dashboard updated " + new Date().toLocaleTimeString();
      }} catch (e) {{
        status.textContent = "Dashboard failed: " + e.message;
      }}
    }}

    async function loadMarketPulse() {{
      const status = document.getElementById("status");
      status.textContent = "Loading market pulse...";
      try {{
        const res = await fetch("/market/snapshot?top_n=10");
        if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
        const data = await res.json();
        setRows("gainersTable", (data.top_gainers || []).map(x => `<tr><td>${{x.ticker}}</td><td>${{x.sector}}</td><td>${{x.close}}</td><td>${{x.day_return_pct}}%</td></tr>`));
        setRows("losersTable", (data.top_losers || []).map(x => `<tr><td>${{x.ticker}}</td><td>${{x.sector}}</td><td>${{x.close}}</td><td>${{x.day_return_pct}}%</td></tr>`));
        setRows("sectorTable", (data.sector_summary || []).map(x => `<tr><td>${{x.sector}}</td><td>${{x.scripts}}</td><td>${{x.avg_day_return_pct}}%</td><td>${{x.total_volume}}</td></tr>`));
        status.textContent = "Market pulse updated " + new Date().toLocaleTimeString();
      }} catch (e) {{
        status.textContent = "Market pulse failed: " + e.message;
      }}
    }}

    function parseHoldings(text) {{
      return text.split("\\n")
        .map(line => line.trim())
        .filter(Boolean)
        .map(line => {{
          const parts = line.split(",").map(x => x.trim());
          return {{
            ticker: (parts[0] || "").toUpperCase(),
            quantity: Number(parts[1] || "0"),
            avg_price: Number(parts[2] || "0")
          }};
        }})
        .filter(x => x.ticker && x.quantity > 0);
    }}

    async function analyzePortfolio() {{
      const status = document.getElementById("portfolioStatus");
      const holdings = parseHoldings(document.getElementById("holdingsInput").value);
      if (!holdings.length) {{
        status.textContent = "No valid holdings provided.";
        return;
      }}
      status.textContent = "Analyzing portfolio...";
      try {{
        const res = await fetch("/portfolio/analyze", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ holdings }})
        }});
        if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
        const data = await res.json();
        const p = data.portfolio || {{}};
        const s = p.summary || {{}};
        document.getElementById("pInvested").textContent = asMoney(s.total_invested || 0);
        document.getElementById("pCurrent").textContent = asMoney(s.total_current_value || 0);
        document.getElementById("pPnl").textContent = asMoney(s.total_unrealized_pnl || 0);
        document.getElementById("pPnlPct").textContent = (s.total_unrealized_pnl_pct ?? 0) + "%";
        document.getElementById("pExp7").textContent = asMoney(s.expected_pnl_next_7d || 0);
        document.getElementById("pExp21").textContent = asMoney(s.expected_pnl_next_21d || 0);

        setRows("portfolioAnalyzeTable", (p.positions || []).map(x => `<tr>
          <td>${{x.ticker}}</td>
          <td>${{x.quantity}}</td>
          <td>${{x.avg_price}}</td>
          <td>${{x.current_price}}</td>
          <td>${{asMoney(x.current_value)}}</td>
          <td>${{asMoney(x.unrealized_pnl)}}</td>
          <td>${{x.final_score}}</td>
          <td><span class="tag ${{cls(x.recommendation)}}">${{x.recommendation}}</span></td>
          <td>${{x.projection.next_7d_return_pct}}%</td>
          <td>${{x.projection.next_21d_return_pct}}%</td>
        </tr>`));
        status.textContent = "Portfolio analysis updated " + new Date().toLocaleTimeString();
      }} catch (e) {{
        status.textContent = "Portfolio analysis failed: " + e.message;
      }}
    }}

    document.getElementById("runBtn").addEventListener("click", runDashboard);
    document.getElementById("pulseBtn").addEventListener("click", loadMarketPulse);
    document.getElementById("analyzePortfolioBtn").addEventListener("click", analyzePortfolio);
    runDashboard();
    loadMarketPulse();
  </script>
</body>
</html>"""

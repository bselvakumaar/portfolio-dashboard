import json

from app.config import get_settings


def render_dashboard_html() -> str:
    settings = get_settings()
    default_tickers_json = json.dumps(settings.default_tickers)
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Steward Quant React Dashboard</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    :root { --bg:#091722; --panel:#10263a; --line:#23516d; --txt:#e7f2f8; --muted:#9ab2c2; --accent:#23c28f; --warn:#f9a825; }
    * { box-sizing: border-box; } body { margin:0; color:var(--txt); font-family:Segoe UI,Tahoma,sans-serif; background:linear-gradient(135deg,#08141e,#122636); }
    .wrap { max-width:1180px; margin:0 auto; padding:20px; } .title { font-size:30px; font-weight:700; margin:0 0 8px; } .sub { color:var(--muted); margin-bottom:14px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px; margin-bottom:12px; }
    .controls { display:grid; grid-template-columns:2fr .8fr .8fr auto auto; gap:10px; align-items:end; } .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    .grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; } .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
    label { display:block; color:var(--muted); font-size:12px; margin-bottom:6px; } input, textarea { width:100%; background:var(--bg); color:var(--txt); border:1px solid var(--line); border-radius:8px; padding:10px; }
    textarea { min-height:110px; resize:vertical; } button { border:none; border-radius:8px; padding:11px 14px; font-weight:700; cursor:pointer; background:linear-gradient(120deg,var(--accent),#36a9cd); color:#05231f; }
    button.alt { background:linear-gradient(120deg,var(--warn),#f6d365); color:#281900; } .status { margin-top:8px; color:var(--muted); font-size:13px; }
    .metric { background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:10px; } .metric .k { color:var(--muted); font-size:12px; } .metric .v { margin-top:5px; font-size:20px; font-weight:700; }
    table { width:100%; border-collapse:collapse; } th,td { text-align:left; border-bottom:1px solid var(--line); padding:7px 6px; font-size:13px; } th { color:var(--muted); }
    .card { background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:10px; } .ticker { font-size:16px; font-weight:700; } .badge { border-radius:6px; padding:2px 8px; font-size:11px; font-weight:700; background:rgba(35,194,143,.2); color:#75edca; text-transform:uppercase; }
    .portfolio-help { border:1px solid rgba(249,168,37,.5); background:rgba(249,168,37,.15); color:#ffd37d; border-radius:8px; padding:10px; margin-bottom:10px; font-size:13px; }
    @media (max-width: 1100px) { .controls,.grid2,.grid4,.cards { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <div id="root"></div>
  <script>window.STEWARD_DEFAULT_TICKERS = __DEFAULT_TICKERS__;</script>
  <script type="text/babel">
    const { useEffect, useMemo, useState } = React;
    const money = (v) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v || 0);
    const parseHoldings = (text) => text.split("\\n").map((x) => x.trim()).filter(Boolean).map((line) => {
      const p = line.split(",").map((x) => x.trim());
      return { ticker: (p[0] || "").toUpperCase(), quantity: Number(p[1] || 0), avg_price: Number(p[2] || 0) };
    }).filter((x) => x.ticker && x.quantity > 0);

    function App() {
      const [tickers, setTickers] = useState((window.STEWARD_DEFAULT_TICKERS || []).join(","));
      const [topN, setTopN] = useState(5);
      const [capital, setCapital] = useState(1000000);
      const [status, setStatus] = useState("Ready.");
      const [portfolioStatus, setPortfolioStatus] = useState("Please create your portfolio and click Analyze Portfolio.");
      const [dashboard, setDashboard] = useState(null);
      const [pulse, setPulse] = useState(null);
      const [holdingsText, setHoldingsText] = useState("");
      const [portfolio, setPortfolio] = useState(null);
      const holdings = useMemo(() => parseHoldings(holdingsText), [holdingsText]);

      const runDashboard = async () => {
        setStatus("Running dashboard...");
        try {
          const res = await fetch("/dashboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tickers: tickers.split(",").map((x) => x.trim()).filter(Boolean),
              top_n: Math.max(1, Math.min(20, Number(topN) || 5)),
              capital: Math.max(1, Number(capital) || 1000000),
              push_to_sheets: false
            })
          });
          if (!res.ok) throw new Error("HTTP " + res.status);
          setDashboard(await res.json());
          setStatus("Dashboard updated " + new Date().toLocaleTimeString());
        } catch (e) { setStatus("Dashboard failed: " + e.message); }
      };

      const loadPulse = async () => {
        try {
          const res = await fetch("/market/snapshot?top_n=10");
          if (!res.ok) throw new Error("HTTP " + res.status);
          setPulse(await res.json());
        } catch (e) { setStatus("Market pulse failed: " + e.message); }
      };

      const analyzePortfolio = async () => {
        if (!holdings.length) {
          setPortfolioStatus("Please create your portfolio first. Add holdings and run analysis.");
          return;
        }
        setPortfolioStatus("Analyzing portfolio...");
        try {
          const res = await fetch("/portfolio/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ holdings })
          });
          if (!res.ok) throw new Error("HTTP " + res.status);
          const data = await res.json();
          setPortfolio(data.portfolio || null);
          setPortfolioStatus("Portfolio analysis updated " + new Date().toLocaleTimeString());
        } catch (e) { setPortfolioStatus("Portfolio analysis failed: " + e.message); }
      };

      useEffect(() => { runDashboard(); loadPulse(); }, []);

      const overview = dashboard?.market_overview || {};
      const picks = dashboard?.top_picks || [];
      const synth = dashboard?.synthetic_portfolio?.summary || {};
      const synthPos = dashboard?.synthetic_portfolio?.positions || [];
      const pSummary = portfolio?.summary || {};
      const pPos = portfolio?.positions || [];

      return (
        <div className="wrap">
          <div className="title">Steward Quant React Dashboard</div>
          <div className="sub">Better dashboard management with live API integration.</div>

          <div className="panel">
            <div className="controls">
              <div><label>Tickers</label><input value={tickers} onChange={(e) => setTickers(e.target.value)} /></div>
              <div><label>Top Picks</label><input type="number" min="1" max="20" value={topN} onChange={(e) => setTopN(e.target.value)} /></div>
              <div><label>Capital</label><input type="number" min="1" value={capital} onChange={(e) => setCapital(e.target.value)} /></div>
              <button onClick={runDashboard}>Run Dashboard</button>
              <button className="alt" onClick={loadPulse}>Load Market Pulse</button>
            </div>
            <div className="status">{status}</div>
          </div>

          <div className="grid4">
            <div className="metric"><div className="k">Coverage</div><div className="v">{overview.coverage_tickers ?? "-"}</div></div>
            <div className="metric"><div className="k">Avg Score</div><div className="v">{overview.average_steward_score ?? "-"}</div></div>
            <div className="metric"><div className="k">Avg Pred 21d</div><div className="v">{overview.average_predicted_return_21d_pct ?? "-"}%</div></div>
            <div className="metric"><div className="k">Expected PnL 21d</div><div className="v">{money(synth.expected_pnl_21d || 0)}</div></div>
          </div>

          <div className="panel">
            <div className="cards">
              {picks.map((x) => <div className="card" key={x.ticker}><div className="ticker">{x.ticker}</div><div>Score: <b>{x.final_score}</b></div><div>21D: <b>{x.prediction?.predicted_return_pct ?? 0}%</b></div><span className="badge">{x.prediction?.recommendation || "hold"}</span></div>)}
            </div>
          </div>

          <div className="grid2">
            <div className="panel">
              <div className="ticker" style={{marginBottom: "8px"}}>Synthetic Portfolio</div>
              <table><thead><tr><th>Ticker</th><th>Weight</th><th>Allocation</th><th>Pred 21D%</th></tr></thead><tbody>
                {synthPos.map((x) => <tr key={x.ticker}><td>{x.ticker}</td><td>{((x.weight || 0) * 100).toFixed(2)}%</td><td>{money(x.allocation)}</td><td>{x.predicted_return_21d_pct ?? 0}%</td></tr>)}
              </tbody></table>
            </div>
            <div className="panel">
              <div className="ticker" style={{marginBottom: "8px"}}>Top Gainers</div>
              <table><thead><tr><th>Ticker</th><th>Sector</th><th>Day %</th></tr></thead><tbody>
                {(pulse?.top_gainers || []).map((x) => <tr key={x.ticker}><td>{x.ticker}</td><td>{x.sector}</td><td>{x.day_return_pct}%</td></tr>)}
              </tbody></table>
            </div>
          </div>

          <div className="panel">
            <div className="ticker" style={{marginBottom: "8px"}}>My Portfolio</div>
            {!holdings.length && <div className="portfolio-help">Please create your portfolio: use one holding per line as TICKER,QUANTITY,AVG_PRICE and click Analyze Portfolio.</div>}
            <div className="grid2">
              <div>
                <label>Holdings</label>
                <textarea value={holdingsText} onChange={(e) => setHoldingsText(e.target.value)} placeholder={"RELIANCE.NS,20,2450\\nTCS.NS,12,3800"} />
                <button onClick={analyzePortfolio}>Analyze Portfolio</button>
                <div className="status">{portfolioStatus}</div>
              </div>
              <div className="grid4">
                <div className="metric"><div className="k">Invested</div><div className="v">{money(pSummary.total_invested || 0)}</div></div>
                <div className="metric"><div className="k">Current</div><div className="v">{money(pSummary.total_current_value || 0)}</div></div>
                <div className="metric"><div className="k">PnL</div><div className="v">{money(pSummary.total_unrealized_pnl || 0)}</div></div>
                <div className="metric"><div className="k">Exp 21D</div><div className="v">{money(pSummary.expected_pnl_next_21d || 0)}</div></div>
              </div>
            </div>
            <table><thead><tr><th>Ticker</th><th>Qty</th><th>Current</th><th>Value</th><th>PnL</th><th>Rec</th></tr></thead><tbody>
              {pPos.map((x) => <tr key={x.ticker}><td>{x.ticker}</td><td>{x.quantity}</td><td>{x.current_price}</td><td>{money(x.current_value)}</td><td>{money(x.unrealized_pnl)}</td><td>{x.recommendation || "HOLD"}</td></tr>)}
            </tbody></table>
          </div>
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>
"""
    return html.replace("__DEFAULT_TICKERS__", default_tickers_json)

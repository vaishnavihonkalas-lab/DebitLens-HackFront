import React, { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  ScanLine,
  LayoutDashboard,
  Upload,
  Repeat2,
  ShieldCheck,
  Network,
  Settings,
  ArrowUpRight,
  ArrowRight,
  Check,
  Search,
  Download,
  AlertTriangle,
  ChevronRight,
  FileText,
  RefreshCw,
} from "lucide-react";
import "./style.css";

type Tx = {
  id: string;
  date: string;
  description: string;
  amount: number;
  direction: string;
};
type Evidence = { id: string; kind: string; note: string };
type Change = {
  old: number;
  new: number;
  difference: number;
  percent: number;
  date: string;
  label: string;
  notice: string;
};
type Finding = {
  id: string;
  service: string;
  account: string;
  category: string;
  channel: string;
  label: string;
  cycle: string | null;
  monthly_paise: number;
  next_date: string | null;
  reasons: string[];
  missing: string[];
  transactions: Tx[];
  evidence: Evidence[];
  changes: Change[];
};
type Case = {
  service_status: string;
  mandate_status: string;
  request_date: string | null;
  effective_date: string | null;
  note: string;
};
type Alert = {
  finding_id: string;
  service: string;
  transaction: Tx;
  message: string;
};
type Data = {
  findings: Finding[];
  alerts: Alert[];
  monthly_paise: number;
  coverage: {
    count: number;
    accounts: string[];
    start: string | null;
    end: string | null;
  };
  cases: Record<string, Case>;
  history: { at: string; kind: string; finding_id: string }[];
};
type Guide = {
  channel: string;
  title: string;
  url: string | null;
  checked: string | null;
  steps: string[];
  note: string;
};
type Graph = {
  mode: string;
  nodes: {
    id: string;
    type: string;
    label: string;
    properties: Record<string, unknown>;
  }[];
  edges: { source: string; target: string; label: string }[];
  message?: string;
};
const money = (p: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(p / 100);
const blank: Case = {
  service_status: "Unknown",
  mandate_status: "Unknown",
  request_date: null,
  effective_date: null,
  note: "",
};
const fields = [
  "transaction_id",
  "date",
  "description",
  "amount",
  "direction",
  "account_label",
  "currency",
  "payment_rail",
  "mandate_reference",
  "billing_channel",
  "subscription_reference",
];
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = "Request failed";
    try {
      const j = await r.json();
      detail =
        typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      detail = await r.text().catch(() => detail);
    }
    throw Error(detail);
  }
  return r.json();
}

function graphLayout(graph: Graph) {
  const groups = [
    ["Account"],
    ["Transaction"],
    ["MerchantDescriptor"],
    ["Service"],
    ["BillingChannel", "Mandate", "Evidence", "CancellationCase"],
  ];
  const positions: Record<string, { x: number; y: number }> = {};
  let count = 1;
  groups.forEach((types, col) => {
    const nodes = graph.nodes.filter((n) => types.includes(n.type));
    count = Math.max(count, nodes.length);
    nodes.forEach((n, i) => {
      positions[n.id] = { x: 24 + col * 176, y: 42 + i * 70 };
    });
  });
  return { positions, height: Math.max(380, count * 70 + 50) };
}
function graphNodeLabel(n: Graph["nodes"][number]) {
  if (n.type === "Transaction")
    return String(n.properties.date) + " " + money(Number(n.properties.amount));
  if (n.type === "CancellationCase") return String(n.properties.service_status);
  return n.label.length > 23 ? n.label.slice(0, 21) + "…" : n.label;
}

function App() {
  const [tab, setTab] = useState("Overview"),
    [data, setData] = useState<Data | null>(null),
    [health, setHealth] = useState<{
      storage: string;
      neo4j_connected: boolean;
    } | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState(""),
    [query, setQuery] = useState("");
  const [csv, setCsv] = useState(""),
    [mapping, setMapping] = useState<Record<string, string>>({}),
    [headers, setHeaders] = useState<string[]>([]),
    [preview, setPreview] = useState<{
      rows: Tx[];
      valid_count: number;
      errors: { row: number; message: string }[];
      duplicates: number;
    } | null>(null);
  const [msg, setMsg] = useState(""),
    [parsed, setParsed] = useState<Record<string, string> | null>(null),
    [guides, setGuides] = useState<Guide[]>([]),
    [caseForm, setCaseForm] = useState<Case>(blank),
    [graph, setGraph] = useState<Graph | null>(null),
    [node, setNode] = useState("");
  const finding = data?.findings.find((f) => f.id === selected);
  async function refresh() {
    const [d, h, g] = await Promise.all([
      api<Data>("/dashboard"),
      api<{ storage: string; neo4j_connected: boolean }>("/health"),
      api<Guide[]>("/guides"),
    ]);
    setData(d);
    setHealth(h);
    setGuides(g);
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void action(refresh);
  }, []);
  useEffect(() => {
    setCaseForm(data?.cases[selected] || { ...blank });
  }, [selected, data]);
  useEffect(() => {
    setGraph(null);
    if (tab === "Evidence Graph" && !selected && data?.findings.length) {
      setSelected(
        (
          data.findings.find((f) => f.category === "subscription") ||
          data.findings[0]
        ).id,
      );
      return;
    }
    if (tab === "Evidence Graph")
      void action(async () =>
        setGraph(
          await api<Graph>(
            "/graph" + (selected ? "?finding_id=" + selected : ""),
          ),
        ),
      );
  }, [tab, selected]);
  const nav = [
    ["Overview", LayoutDashboard],
    ["Imports", Upload],
    ["Recurring Payments", Repeat2],
    ["Cancellation Centre", ShieldCheck],
    ["Evidence Graph", Network],
    ["Settings & Data", Settings],
  ] as const;
  function open(f: Finding, destination = "Recurring Payments") {
    setSelected(f.id);
    setTab(destination);
  }
  async function sample(name: string) {
    return fetch("/api/samples/" + name).then((r) => r.text());
  }
  function guideFor(f: Finding) {
    return (
      guides.find((g) => g.channel === f.channel) ||
      guides.find((g) => g.channel === "UNKNOWN")
    );
  }
  async function download(path: string, name: string) {
    const r = await fetch("/api" + path);
    if (!r.ok) throw Error("Export failed");
    const blob = await r.blob(),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function groupSelect() {
    return (
      <label className="selectlabel">
        Selected commitment
        <select
          aria-label="Selected commitment"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Choose a finding</option>
          {data?.findings.map((f) => (
            <option key={f.id} value={f.id}>
              {f.service} · {f.account}
            </option>
          ))}
        </select>
      </label>
    );
  }
  function findingsList() {
    const fs =
      data?.findings.filter((f) =>
        (f.service + " " + f.label + " " + f.account)
          .toLowerCase()
          .includes(query.toLowerCase()),
      ) || [];
    return (
      <>
        <div className="sectionhead">
          <div>
            <h2>Your payment patterns</h2>
            <p>Open a finding to see the evidence behind it.</p>
          </div>
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Search findings"
              placeholder="Search services"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Service / descriptor</th>
                <th>Evidence assessment</th>
                <th>Cycle</th>
                <th>Monthly equivalent</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {fs.map((f) => (
                <tr key={f.id}>
                  <td>
                    <b>{f.service}</b>
                    <small>
                      {f.account} · {f.channel}
                    </small>
                  </td>
                  <td>
                    <span
                      className={
                        "tag " + (f.label.includes("Likely") ? "green" : "")
                      }
                    >
                      {f.label}
                    </span>
                  </td>
                  <td>{f.cycle || "Unknown"}</td>
                  <td>
                    {f.monthly_paise ? money(f.monthly_paise) : "Not projected"}
                  </td>
                  <td>
                    <button
                      className="iconbutton"
                      aria-label={"Inspect " + f.service}
                      onClick={() => open(f)}
                    >
                      <ArrowUpRight size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!fs.length && (
            <p className="empty">
              No findings yet. Import records or load the fictional demo.
            </p>
          )}
        </div>
      </>
    );
  }
  function detail() {
    if (!finding)
      return (
        <div className="empty">
          Select a payment finding to inspect its supporting records.
        </div>
      );
    return (
      <section className="paper detail">
        <div className="sectionhead">
          <div>
            <span className="eyebrow">EVIDENCE, NOT GUESSWORK</span>
            <h2>{finding.service}</h2>
            <p>{finding.label}</p>
          </div>
          <button onClick={() => open(finding, "Cancellation Centre")}>
            Manage cancellation <ArrowRight size={15} />
          </button>
        </div>
        <div className="reasonlist">
          {finding.reasons.map((x) => (
            <p key={x}>
              <Check size={15} />
              {x}
            </p>
          ))}
        </div>
        <div className="toolbar">
          <button
            onClick={() =>
              action(async () => {
                await api("/findings/" + selected + "/decision", "PUT", {
                  decision: "confirmed",
                });
                await refresh();
              })
            }
          >
            Confirm recurring pattern
          </button>
          <button
            onClick={() =>
              action(async () => {
                await api("/findings/" + selected + "/decision", "PUT", {
                  decision: "rejected",
                });
                await refresh();
              })
            }
          >
            Reject suggestion
          </button>
          <button
            onClick={() =>
              action(async () => {
                await api("/findings/" + selected + "/decision", "PUT", {
                  decision: "reset",
                });
                await refresh();
              })
            }
          >
            Reset assessment
          </button>
          <button onClick={() => open(finding, "Evidence Graph")}>
            Trace graph <Network size={15} />
          </button>
        </div>
        <h3>Source transactions</h3>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Debit</th>
                <th>Correction</th>
              </tr>
            </thead>
            <tbody>
              {finding.transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description}</td>
                  <td>{money(t.amount)}</td>
                  <td>
                    <button
                      onClick={() => {
                        const service = prompt(
                          "Correct service name",
                          finding.service,
                        );
                        if (!service) return;
                        const channel = prompt(
                          "Billing channel: UPI, CARD, GOOGLE_PLAY, APPLE, DIRECT, UNKNOWN",
                          finding.channel,
                        );
                        if (channel === null) return;
                        const reference = prompt(
                          "Subscription reference (use a unique value to split this transaction into another subscription)",
                          "",
                        );
                        if (reference === null) return;
                        void action(async () => {
                          await api("/transactions/" + t.id, "PUT", {
                            service,
                            billing_channel: channel,
                            subscription_reference: reference,
                          });
                          setSelected("");
                          await refresh();
                          setNotice(
                            "Correction saved. Reopen the regrouped finding; previous case/evidence stays attached to its original group.",
                          );
                        });
                      }}
                    >
                      Correct / split
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {finding.changes.map((c, i) => (
          <div className="alert" key={i}>
            <b>
              {c.label}: {money(c.old)} to {money(c.new)}
            </b>
            <p>
              +{money(c.difference)} (+{c.percent}%) on {c.date}. Check plan,
              tax and billing-period comparability.
            </p>
            <small>{c.notice}</small>
          </div>
        ))}
        <h3>Supplied evidence</h3>
        {finding.evidence.length ? (
          finding.evidence.map((e) => (
            <div className="evidence" key={e.id}>
              <b>{e.kind}</b>
              <p>{e.note}</p>
              <small>User-provided; issuer authenticity unverified.</small>
            </div>
          ))
        ) : (
          <p>No supporting messages supplied.</p>
        )}
        <div className="note">
          {finding.missing.join(". ")}. A repeated purchase is not proof of an
          active mandate.
        </div>
      </section>
    );
  }
  return (
    <div className="layout">
      <aside>
        <div className="brand">
          <ScanLine size={29} />
          <span>
            DebitLens<small>MAKE EVERY DEBIT VISIBLE</small>
          </span>
        </div>
        <div className="workspace">
          <span className="avatar">DL</span>
          <div>
            Personal workspace<small>Local, single-user prototype</small>
          </div>
        </div>
        <nav>
          {nav.map(([name, Icon]) => (
            <button
              key={name}
              className={tab === name ? "active" : ""}
              onClick={() => setTab(name)}
            >
              <Icon size={18} />
              {name}
              {name === "Cancellation Centre" && !!data?.alerts.length && (
                <em>{data.alerts.length}</em>
              )}
            </button>
          ))}
        </nav>
        <div className="asidefoot">
          <ShieldCheck size={21} />
          <b>Your records, your decisions.</b>
          <p>No bank login. No automatic cancellations. No money moved.</p>
          <span>hackFront India · Fintech</span>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Personal workspace <ChevronRight size={14} /> {tab}
          </div>
          <span className={"status " + (health?.neo4j_connected ? "good" : "")}>
            {health
              ? health.neo4j_connected
                ? "Neo4j connected"
                : "SQLite preview · no Neo4j"
              : "Checking backend"}
          </span>
        </header>
        <div className="content">
          <div className="pagehead">
            <div>
              <div className="eyebrow">YOUR RECURRING PAYMENT WORKSPACE</div>
              <h1>
                {tab === "Overview" ? "Know where your money goes." : tab}
              </h1>
              <p>
                {tab === "Overview"
                  ? "Find recurring charges. Understand changes. Take the right next step."
                  : "Clear records and practical actions, with evidence at every step."}
              </p>
            </div>
            <button
              className="primary"
              disabled={busy}
              onClick={() => setTab("Imports")}
            >
              <Upload size={16} /> Import records
            </button>
          </div>
          <p className="disclaimer">
            Findings depend on the records you provide. Bank and
            payment-provider connections are not active in this prototype.
          </p>
          {busy && (
            <p role="status" className="note">
              Working…
            </p>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => action(refresh)}>Retry connection</button>
            </div>
          )}
          {notice && (
            <div className="success" role="status">
              {notice}
            </div>
          )}
          {tab === "Overview" && (
            <>
              <div className="metrics">
                <div className="metric teal">
                  <span>Projected monthly equivalent</span>
                  <strong>{money(data?.monthly_paise || 0)}</strong>
                  <small>
                    Based on supported patterns; not realised savings
                  </small>
                </div>
                <div className="metric">
                  <span>Payment patterns found</span>
                  <strong>
                    {data?.findings.filter((f) => f.cycle).length || 0}
                  </strong>
                  <small>Includes patterns needing review</small>
                </div>
                <div className="metric">
                  <span>Possible price increases</span>
                  <strong>
                    {data?.findings
                      .filter((f) => f.category !== "utility")
                      .reduce((a, f) => a + f.changes.length, 0) || 0}
                  </strong>
                  <small>Check that plans and periods are comparable</small>
                </div>
                <div className="metric">
                  <span>After-cancellation alerts</span>
                  <strong>{data?.alerts.length || 0}</strong>
                  <small>Review evidence before taking action</small>
                </div>
              </div>
              <section className="intro">
                <div>
                  <span className="eyebrow">START WITH THE RECORDS</span>
                  <h2>A confusing charge deserves a clear explanation.</h2>
                  <p>
                    Trace a debit back to its service, billing channel and
                    cancellation evidence. Keep uncertain matches open for
                    review.
                  </p>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() =>
                      action(async () => {
                        await api("/demo", "POST");
                        await refresh();
                        setNotice(
                          "Fictional sample records loaded. No real account connected.",
                        );
                      })
                    }
                  >
                    Load fictional demo <ArrowRight size={16} />
                  </button>
                </div>
                <div className="sampleproof">
                  <span className="tag green">ILLUSTRATIVE DEMO FINDING</span>
                  <h3>StreamBee</h3>
                  <p>STREAMBEE / SBEE MEDIA</p>
                  <div className="sampleamount">
                    ₹299 <ArrowRight size={19} /> ₹399
                  </div>
                  <small>Possible price increase · +33.4%</small>
                  <hr />
                  <p>
                    <FileText size={15} /> Traceable source records
                  </p>
                  <p>
                    <ShieldCheck size={15} /> Separate cancellation and mandate
                    status
                  </p>
                </div>
              </section>
              <section className="paper">{findingsList()}</section>
              <div className="coverage">
                <b>Data coverage</b>
                <span>{data?.coverage.count || 0} transactions</span>
                <span>
                  {data?.coverage.start || "No start date"} to{" "}
                  {data?.coverage.end || "no end date"}
                </span>
                <span>{data?.coverage.accounts.length || 0} accounts</span>
                <small>
                  Missing accounts and unobserved annual renewals remain
                  invisible. Date span does not guarantee continuous coverage.
                </small>
              </div>
            </>
          )}
          {tab === "Imports" && (
            <>
              <section className="paper">
                <div className="sectionhead">
                  <div>
                    <h2>Import transaction records</h2>
                    <p>
                      CSV only · INR · YYYY-MM-DD or DD/MM/YYYY · maximum 2 MB /
                      10,000 rows.
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      action(async () => {
                        setCsv(await sample("initial.csv"));
                        setHeaders([]);
                        setMapping({});
                        setPreview(null);
                      })
                    }
                  >
                    Use sample CSV
                  </button>
                </div>
                <p>
                  Required columns: date, description, amount, direction,
                  account_label, currency. Positive amount; debit or credit
                  direction. Optional transaction_id, payment_rail,
                  mandate_reference, billing_channel, subscription_reference.
                </p>
                <input
                  aria-label="CSV file"
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      if (file.size > 2000000) {
                        setError("Maximum CSV size is 2 MB");
                        return;
                      }
                      void file.text().then((t) => {
                        setCsv(t);
                        setPreview(null);
                        setHeaders([]);
                        setMapping({});
                      });
                    }
                  }}
                />
                <textarea
                  aria-label="CSV content"
                  rows={7}
                  value={csv}
                  onChange={(e) => {
                    setCsv(e.target.value);
                    setPreview(null);
                  }}
                  placeholder="Paste CSV, choose a file, or use sample CSV"
                />
                <div className="toolbar">
                  <button
                    onClick={() =>
                      action(async () => {
                        const r = await api<{ headers: string[] }>(
                          "/import/headers",
                          "POST",
                          { text: csv },
                        );
                        setHeaders(r.headers);
                      })
                    }
                  >
                    Map columns
                  </button>
                  <button
                    disabled={busy || !csv}
                    onClick={() =>
                      action(async () =>
                        setPreview(
                          await api("/import/preview", "POST", {
                            text: csv,
                            mapping: Object.keys(mapping).length
                              ? mapping
                              : undefined,
                          }),
                        ),
                      )
                    }
                  >
                    Preview import
                  </button>
                  <button
                    className="primary"
                    disabled={busy || !preview}
                    onClick={() =>
                      action(async () => {
                        const r = await api<{
                          imported: number;
                          duplicates: number;
                          errors: unknown[];
                        }>("/import", "POST", {
                          text: csv,
                          mapping: Object.keys(mapping).length
                            ? mapping
                            : undefined,
                        });
                        await refresh();
                        setNotice(
                          `Imported ${r.imported} rows. Skipped ${r.duplicates} duplicates; ${r.errors.length} invalid rows. Only valid rows were saved.`,
                        );
                        setPreview(null);
                      })
                    }
                  >
                    Import valid rows
                  </button>
                  <button
                    onClick={() =>
                      action(async () => {
                        setCsv(await sample("later.csv"));
                        setPreview(null);
                        setMapping({});
                        setHeaders([]);
                      })
                    }
                  >
                    Use later statement
                  </button>
                </div>
                {headers.length > 0 && (
                  <div className="mapping">
                    {fields.map((f) => (
                      <label key={f}>
                        {f}
                        <select
                          value={mapping[f] || f}
                          onChange={(e) => {
                            setMapping({ ...mapping, [f]: e.target.value });
                            setPreview(null);
                          }}
                        >
                          <option value={f}>Default: {f}</option>
                          {headers
                            .filter((h) => h !== f)
                            .map((h) => (
                              <option key={h}>{h}</option>
                            ))}
                        </select>
                      </label>
                    ))}
                  </div>
                )}
                {preview && (
                  <div className="note">
                    <b>
                      {preview.valid_count} valid rows; {preview.errors.length}{" "}
                      errors.
                    </b>
                    <pre>
                      {JSON.stringify(preview.rows.slice(0, 3), null, 2)}
                    </pre>
                    {preview.errors.map((e, i) => (
                      <p key={i}>
                        Row {e.row}: {e.message}
                      </p>
                    ))}
                  </div>
                )}
                <p className="muted">
                  Without stable transaction IDs, duplicate matching uses a
                  fingerprint plus occurrence count. Identical purchases remain
                  separate within a file; cross-file matching can be uncertain.
                </p>
              </section>
              <section className="paper">
                <h2>Add selected message evidence</h2>
                <p>
                  Supported format: one labelled field per line, e.g. Kind:
                  cancellation, Service: StreamBee, Effective date: 2026-09-30.
                  This parser does not understand arbitrary bank messages.
                </p>
                {groupSelect()}
                <button
                  onClick={() =>
                    action(async () => {
                      setMsg(await sample("message.txt"));
                      setParsed(null);
                    })
                  }
                >
                  Load fictional message
                </button>
                <textarea
                  aria-label="Message text"
                  value={msg}
                  rows={5}
                  onChange={(e) => {
                    setMsg(e.target.value);
                    setParsed(null);
                  }}
                />
                <button
                  disabled={!msg || busy}
                  onClick={() =>
                    action(async () =>
                      setParsed(
                        await api("/messages/preview", "POST", { text: msg }),
                      ),
                    )
                  }
                >
                  Parse message
                </button>
                {parsed && (
                  <div className="mapping">
                    {[
                      "kind",
                      "service",
                      "amount",
                      "effective_date",
                      "mandate_reference",
                      "billing_channel",
                    ].map((k) => (
                      <label key={k}>
                        {k}
                        <input
                          value={parsed[k] || ""}
                          onChange={(e) =>
                            setParsed({ ...parsed, [k]: e.target.value })
                          }
                        />
                      </label>
                    ))}
                    <button
                      className="primary"
                      disabled={!selected || busy}
                      onClick={() =>
                        action(async () => {
                          await api("/evidence", "POST", {
                            finding_id: selected,
                            kind: parsed.kind,
                            note: parsed.raw,
                            service: parsed.service,
                            amount: parsed.amount,
                            effective_date: parsed.effective_date || null,
                            mandate_reference: parsed.mandate_reference,
                            billing_channel: parsed.billing_channel,
                          });
                          await refresh();
                          setNotice(
                            "Evidence saved as user-supplied and unverified. Cancellation statuses have not changed automatically.",
                          );
                          setParsed(null);
                        })
                      }
                    >
                      Confirm and save evidence
                    </button>
                  </div>
                )}
              </section>
            </>
          )}
          {tab === "Recurring Payments" && (
            <>
              <section className="paper">{findingsList()}</section>
              {groupSelect()}
              {detail()}
            </>
          )}
          {tab === "Cancellation Centre" && (
            <>
              {data?.alerts.map((a, i) => (
                <div className="alert" key={i}>
                  <b>
                    <AlertTriangle size={16} /> {a.service}:{" "}
                    {money(a.transaction.amount)} on {a.transaction.date}
                  </b>
                  <p>{a.message}</p>
                  <small>
                    A pending or final charge, refund timing or incorrect match
                    may explain it. No fraud or refund decision is made.
                  </small>
                </div>
              ))}
              {groupSelect()}
              {finding ? (
                <>
                  <section className="paper">
                    <h2>{finding.service}: cancellation record</h2>
                    <p>
                      Two separate actions. Stopping a payment mandate does not
                      necessarily end the contract or refund a past charge.
                    </p>
                    {["loan", "insurance", "utility"].includes(
                      finding.category,
                    ) && (
                      <div className="alert">
                        Important obligation: confirm the consequences before
                        stopping payment.
                      </div>
                    )}
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void action(async () => {
                          await api("/cases/" + selected, "PUT", caseForm);
                          await refresh();
                          setNotice(
                            "Cancellation record saved. No external cancellation was performed.",
                          );
                        });
                      }}
                    >
                      <div className="mapping">
                        <label>
                          Service status
                          <select
                            aria-label="Service status"
                            value={caseForm.service_status}
                            onChange={(e) =>
                              setCaseForm({
                                ...caseForm,
                                service_status: e.target.value,
                              })
                            }
                          >
                            {[
                              "Unknown",
                              "Active",
                              "Cancellation requested",
                              "Cancellation reported by user",
                              "Supported by supplied confirmation",
                            ].map((v) => (
                              <option key={v}>{v}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Mandate status
                          <select
                            aria-label="Mandate status"
                            value={caseForm.mandate_status}
                            onChange={(e) =>
                              setCaseForm({
                                ...caseForm,
                                mandate_status: e.target.value,
                              })
                            }
                          >
                            {[
                              "Unknown",
                              "Active according to supplied information",
                              "Revocation requested",
                              "Revocation reported by user",
                              "Supported by supplied confirmation",
                            ].map((v) => (
                              <option key={v}>{v}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Request date
                          <input
                            aria-label="Request date"
                            type="date"
                            value={caseForm.request_date || ""}
                            onChange={(e) =>
                              setCaseForm({
                                ...caseForm,
                                request_date: e.target.value || null,
                              })
                            }
                          />
                        </label>
                        <label>
                          Effective cancellation date
                          <input
                            aria-label="Effective cancellation date"
                            type="date"
                            value={caseForm.effective_date || ""}
                            onChange={(e) =>
                              setCaseForm({
                                ...caseForm,
                                effective_date: e.target.value || null,
                              })
                            }
                          />
                        </label>
                      </div>
                      <label>
                        Confirmation reference / notes
                        <textarea
                          aria-label="Cancellation notes"
                          value={caseForm.note}
                          onChange={(e) =>
                            setCaseForm({ ...caseForm, note: e.target.value })
                          }
                        />
                      </label>
                      <div className="toolbar">
                        <button className="primary" disabled={busy}>
                          Save cancellation record
                        </button>
                        <button type="button" onClick={() => setTab("Imports")}>
                          Add confirmation evidence
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            action(() =>
                              download("/export", "DebitLens_evidence.json"),
                            )
                          }
                        >
                          <Download size={15} /> Export evidence
                        </button>
                      </div>
                    </form>
                  </section>
                  <section className="paper">
                    <h2>Cancellation route: {guideFor(finding)?.title}</h2>
                    <p>
                      Billing channel: <b>{finding.channel}</b>. If this is
                      wrong, correct it in the finding before using these steps.
                    </p>
                    <ol>
                      {guideFor(finding)?.steps.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ol>
                    <div className="note">{guideFor(finding)?.note}</div>
                    {guideFor(finding)?.url ? (
                      <a
                        href={guideFor(finding)?.url || ""}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open official instructions <ArrowUpRight size={14} />
                      </a>
                    ) : (
                      <p>
                        Generic guidance; provider-specific steps unverified.
                      </p>
                    )}
                    <small>
                      Source checked:{" "}
                      {guideFor(finding)?.checked || "Not provider-verified"}.
                      Never enter PINs, OTPs or bank passwords here.
                    </small>
                  </section>
                </>
              ) : (
                <div className="paper empty">
                  Choose a finding to view its cancellation route.
                </div>
              )}
            </>
          )}
          {tab === "Evidence Graph" && (
            <>
              {groupSelect()}
              <section className="paper">
                <div className="sectionhead">
                  <div>
                    <h2>Follow the evidence</h2>
                    <p>
                      Connections come from actual Neo4j query results. Up to
                      500 relationships.
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      action(async () =>
                        setGraph(
                          await api(
                            "/graph" +
                              (selected ? "?finding_id=" + selected : ""),
                          ),
                        ),
                      )
                    }
                  >
                    <RefreshCw size={15} /> Refresh graph
                  </button>
                </div>
                {graph?.mode !== "neo4j" ? (
                  <div className="note">{graph?.message || "Connecting…"}</div>
                ) : (
                  <>
                    <div className="graphcanvas">
                      <svg
                        viewBox={`0 0 900 ${graphLayout(graph).height}`}
                        role="img"
                        aria-label="Neo4j evidence relationships"
                      >
                        {graph.edges.map((e, i) => {
                          const a = graphLayout(graph).positions[e.source],
                            b = graphLayout(graph).positions[e.target];
                          return (
                            <line
                              key={i}
                              x1={a.x}
                              y1={a.y}
                              x2={b.x}
                              y2={b.y}
                              stroke="#b0ccc5"
                              strokeWidth="1.5"
                            />
                          );
                        })}
                        {graph.nodes.map((n, i) => (
                          <g
                            key={n.id}
                            role="button"
                            tabIndex={0}
                            aria-label={n.type + " " + n.label}
                            onClick={() => setNode(n.id)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") setNode(n.id);
                            }}
                            transform={`translate(${graphLayout(graph).positions[n.id].x},${graphLayout(graph).positions[n.id].y})`}
                          >
                            <circle
                              r="12"
                              fill={
                                n.type === "Service" ? "#08776b" : "#d1eae3"
                              }
                              stroke="#08776b"
                            />
                            <text x="20" y="0" fontSize="11" fill="#536966">
                              {n.type}
                            </text>
                            <text x="20" y="17" fontSize="10" fill="#172f36">
                              {graphNodeLabel(n)}
                            </text>
                          </g>
                        ))}
                      </svg>
                    </div>
                    {node && (
                      <pre>
                        {JSON.stringify(
                          graph.nodes.find((n) => n.id === node),
                          null,
                          2,
                        )}
                      </pre>
                    )}
                    <details>
                      <summary>Inspect relationship data</summary>
                      <pre>{JSON.stringify(graph.edges, null, 2)}</pre>
                    </details>
                    {!graph.nodes.length && (
                      <p>No graph records yet. Import sample records first.</p>
                    )}
                  </>
                )}
              </section>
            </>
          )}
          {tab === "Settings & Data" && (
            <>
              <section className="paper">
                <h2>Storage and privacy</h2>
                <p>
                  Storage mode: <b>{health?.storage || "Unavailable"}</b>. This
                  is a local single-user prototype. Anyone with access to this
                  local app can access this workspace.
                </p>
                <p>
                  No bank connection, external analytics or external AI
                  requests. Records go to the locally running backend and its
                  database. Do not expose this app publicly with real financial
                  records.
                </p>
                <div className="toolbar">
                  <button
                    onClick={() =>
                      action(() =>
                        download("/export", "DebitLens_evidence.json"),
                      )
                    }
                  >
                    Download evidence JSON
                  </button>
                  <button
                    onClick={() =>
                      action(() =>
                        download("/export.csv", "DebitLens_findings.csv"),
                      )
                    }
                  >
                    Download findings CSV
                  </button>
                  <button
                    className="danger"
                    onClick={() => {
                      if (
                        confirm(
                          "Delete all transactions, evidence, cases and history? This cannot be undone.",
                        )
                      )
                        void action(async () => {
                          await api("/workspace", "DELETE");
                          setSelected("");
                          await refresh();
                          setNotice(
                            "Workspace records deleted. Backups or downloaded exports are not removed.",
                          );
                        });
                    }}
                  >
                    Delete workspace
                  </button>
                </div>
              </section>
              <section className="paper">
                <h2>Activity history</h2>
                <p>
                  Local application history is editable by someone with database
                  access. It is not an immutable audit record.
                </p>
                {data?.history
                  .slice()
                  .reverse()
                  .slice(0, 50)
                  .map((h, i) => (
                    <div className="history" key={i}>
                      <span>{h.kind}</span>
                      <small>{h.at}</small>
                    </div>
                  ))}
              </section>
            </>
          )}
          <footer>
            DebitLens · Built for informed decisions{" "}
            <span>
              Fictional demo services. Supplied evidence is not issuer-verified.
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

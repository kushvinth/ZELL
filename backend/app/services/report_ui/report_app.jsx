function EventTimelineBars({ rows }) {
  const data = safeArray(rows).slice(0, 10);

  if (!data.length) {
    return <p className="muted-empty">No major event timeline.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        margin={{ top: 10, right: 8, left: -18, bottom: 0 }}
      >
        <CartesianGrid stroke={TOKENS.borderSoft} vertical={false} />
        <XAxis
          dataKey="cycle"
          tick={{ fill: TOKENS.subtle, fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: TOKENS.subtle, fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value, _name, ctx) => [
            value,
            truncate(ctx?.payload?.event_label || "event", 48),
          ]}
          contentStyle={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            color: "#111827",
            borderRadius: 8,
          }}
        />
        <Bar dataKey="event_frequency" fill="#f59e0b" radius={[5, 5, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function KeyMetricGrid({ metrics }) {
  return (
    <div className="metric-grid">
      <MetricTile
        label="Total responses"
        value={safeNumber(metrics.total_responses)}
        hint="persisted response rows"
        accent="#2563eb"
      />
      <MetricTile
        label="Migration events"
        value={safeNumber(metrics.migration_events)}
        hint="is_migrating count"
        accent="#f59e0b"
        delay={90}
      />
      <MetricTile
        label="Trust drop events"
        value={safeNumber(metrics.trust_drop_events)}
        hint="is_less_trusting count"
        accent="#ef4444"
        delay={170}
      />
      <MetricTile
        label="Relationship edges"
        value={safeNumber(metrics.relationship_edges)}
        hint="graph edge count"
        accent="#7c3aed"
        delay={250}
      />
      <MetricTile
        label="Dominant decision"
        value={metrics.dominant_decision || "none"}
        hint="highest frequency"
        accent="#059669"
        delay={320}
      />
      <MetricTile
        label="Dominant emotion"
        value={metrics.dominant_emotion || "none"}
        hint="lexical proxy"
        accent="#dc2626"
        delay={390}
      />
    </div>
  );
}

function NarrativeSection({
  report,
  metadata,
  metrics,
  charts,
  insights,
  rawTables,
}) {
  const topActions = safeArray(rawTables.responses).slice(0, 6);
  const trend = safeArray(charts.agent_behavior_over_time);
  const peakMigration = trend.reduce(
    (acc, row) =>
      safeNumber(row.migrating_rate, 0) > safeNumber(acc.migrating_rate, 0)
        ? row
        : acc,
    trend[0] || { cycle: 0, migrating_rate: 0 },
  );

  return (
    <section className="report-reading-panel">
      <div className="report-content-wrapper">
        <HeroHeader
          metadata={metadata}
          reproducibility={report.reproducibility || {}}
        />

        <article className="narrative-section">
          <div className="section-title-row">
            <span className="section-index">01</span>
            <h3>Executive summary</h3>
          </div>
          <p>
            This run captured {formatInt(metrics.total_responses)} agent
            responses over {formatInt(metadata.cycles)}
            cycles. The dominant decision pattern is{" "}
            <strong>{metrics.dominant_decision || "unknown"}</strong>, while
            collective emotion trends toward{" "}
            <strong>{metrics.dominant_emotion || "unknown"}</strong>.
          </p>
          <blockquote>
            Highest migration pressure appeared in{" "}
            {cycleLabel(peakMigration.cycle)}, peaking at
            {` ${(safeNumber(peakMigration.migrating_rate) * 100).toFixed(1)}%`}
            .
          </blockquote>
        </article>

        <article className="narrative-section">
          <div className="section-title-row">
            <span className="section-index">02</span>
            <h3>Behavioral highlights</h3>
          </div>
          <p>
            Migration events reached {formatInt(metrics.migration_events)}, with
            trust drop events at
            {` ${formatInt(metrics.trust_drop_events)}.`} The relationship graph
            built
            {` ${formatInt(metrics.relationship_edges)} edges,`} exposing
            central entities that shaped diffusion and alignment behavior.
          </p>
          {safeArray(insights.anomalies)
            .slice(0, 3)
            .map((item, idx) => (
              <p key={`anomaly-${idx}`} className="inline-note">
                {item}
              </p>
            ))}
        </article>

        <article className="narrative-section">
          <div className="section-title-row">
            <span className="section-index">03</span>
            <h3>Notable actions</h3>
          </div>
          <div className="action-list">
            {topActions.map((row, idx) => (
              <div key={`action-${idx}`} className="action-item">
                <p className="action-head">
                  {row.agent_name || row.agent_id || "Unknown"} ·{" "}
                  {row.agent_region || "Unknown"} ·{` ${cycleLabel(row.cycle)}`}
                </p>
                <p>{row.action || "No explicit action recorded."}</p>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}

function WorkbenchSection({
  metadata,
  charts,
  insights,
  rawTables,
  workflowSteps,
  activeStep,
  metrics,
}) {
  return (
    <aside className="report-workbench-panel">
      <WorkflowRail
        steps={workflowSteps}
        activeStep={activeStep}
        responseCount={metadata.response_count}
      />

      <GlassPanel
        title="Key metrics"
        subtitle="Deterministic counters"
        accent="#2563eb"
      >
        <KeyMetricGrid metrics={metrics} />
      </GlassPanel>

      <GlassPanel
        title="Behavior telemetry"
        subtitle="Migration, trust and sentiment"
        accent="#0ea5e9"
        delay={120}
      >
        <BehaviorTrend rows={charts.agent_behavior_over_time} />
      </GlassPanel>

      <div className="workbench-grid">
        <GlassPanel
          title="Decision blend"
          subtitle="Top decision categories"
          accent="#16a34a"
          delay={170}
        >
          <DecisionDonut rows={charts.distribution_decisions} />
        </GlassPanel>

        <GlassPanel
          title="Emotion landscape"
          subtitle="Top emotional vectors"
          accent="#9333ea"
          delay={200}
        >
          <EmotionRadar rows={charts.distribution_emotions} />
        </GlassPanel>
      </div>

      <div className="workbench-grid">
        <GlassPanel
          title="Event timeline"
          subtitle="Most frequent event per cycle"
          accent="#f59e0b"
          delay={230}
        >
          <EventTimelineBars rows={charts.timeline_major_events} />
        </GlassPanel>

        <GlassPanel
          title="Anomaly feed"
          subtitle="Auto-detected outliers"
          accent="#ef4444"
          delay={260}
        >
          <AnomalyFeed
            anomalies={insights.anomalies}
            notes={insights.final_notes}
          />
        </GlassPanel>
      </div>

      <GlassPanel
        title="Raw evidence"
        subtitle="Sampled response rows"
        accent="#1d4ed8"
        delay={290}
      >
        <RawEvidenceTable rows={rawTables.responses} />
      </GlassPanel>
    </aside>
  );
}

function ZellReportApp() {
  const report = window.__REPORT__ || {};
  const metadata = report.metadata || {};
  const metrics = (report.executive_summary || {}).key_metrics || {};
  const charts = report.charts || {};
  const insights = report.insights || {};
  const rawTables = report.raw_tables || {};

  const workflowSteps = useMemo(
    () => [
      {
        id: "ingest",
        index: "01",
        title: "Seed ingestion",
        meta: `${formatInt(metadata.response_count)} rows parsed`,
      },
      {
        id: "aggregate",
        index: "02",
        title: "Behavior aggregation",
        meta: `${formatInt(metadata.cycles)} cycles normalized`,
      },
      {
        id: "network",
        index: "03",
        title: "Graph synthesis",
        meta: `${formatInt(metadata.relationship_count)} edges mapped`,
      },
      {
        id: "anomaly",
        index: "04",
        title: "Anomaly detection",
        meta: `${safeArray(insights.anomalies).length} insights`,
      },
      {
        id: "compile",
        index: "05",
        title: "Report compose",
        meta: `v${report.report_version || "2.0"}`,
      },
    ],
    [metadata, insights, report],
  );

  const activeStep = useStepper(workflowSteps.length, 1250);

  return (
    <div className="miro-report-shell">
      <header className="top-bar">
        <div className="brand">MIROFISH</div>
        <div className="top-bar-right">
          <span>Prediction Report</span>
          <span className="dot" />
          <span>Ready</span>
        </div>
      </header>

      <main className="main-split-layout">
        <NarrativeSection
          report={report}
          metadata={metadata}
          metrics={metrics}
          charts={charts}
          insights={insights}
          rawTables={rawTables}
        />

        <WorkbenchSection
          metadata={metadata}
          charts={charts}
          insights={insights}
          rawTables={rawTables}
          workflowSteps={workflowSteps}
          activeStep={activeStep}
          metrics={metrics}
        />
      </main>

      <footer className="report-footer">
        <p>
          ZELL deterministic report export | version{" "}
          {report.report_version || "2.0"}
        </p>
        <p>{report.reproducibility?.signature || "signature unavailable"}</p>
      </footer>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<ZellReportApp />);

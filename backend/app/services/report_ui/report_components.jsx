function GlassPanel({
  title,
  subtitle,
  accent = TOKENS.primary,
  children,
  delay = 0,
  style = {},
}) {
  const visible = useVisible(delay);

  return (
    <section
      className="glass-panel"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(14px)",
        transition:
          "opacity .48s ease, transform .48s cubic-bezier(.2, .8, .2, 1)",
        borderColor: `${accent}55`,
        ...style,
      }}
    >
      <div className="glass-panel__header">
        <div className="glass-panel__accent" style={{ background: accent }} />
        <div>
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      <div className="glass-panel__content">{children}</div>
    </section>
  );
}

function MetricTile({
  label,
  value,
  hint,
  accent = TOKENS.primary,
  delay = 0,
}) {
  const visible = useVisible(delay);
  const isNumber = typeof value === "number";
  const animatedValue = useCountUp(isNumber ? value : 0, 1200);

  return (
    <article
      className="metric-tile"
      style={{
        borderColor: `${accent}50`,
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(10px)",
        transition: "opacity .42s ease, transform .42s ease",
      }}
    >
      <div
        className="metric-tile__glow"
        style={{ background: `${accent}24` }}
      />
      <p className="metric-tile__label">{label}</p>
      <p className="metric-tile__value" style={{ color: accent }}>
        {isNumber ? formatInt(animatedValue) : String(value || "-")}
      </p>
      {hint ? <p className="metric-tile__hint">{hint}</p> : null}
    </article>
  );
}

function HeroHeader({ metadata, reproducibility }) {
  const status = String(metadata?.status || "unknown").toLowerCase();
  const runId = String(metadata?.run_id || "unknown");
  const compactRunId = compactId(runId, 8, 4);
  const statusText = status.charAt(0).toUpperCase() + status.slice(1);
  const sig = String(reproducibility?.signature || "").slice(0, 14);

  const subtitle = [
    `${formatInt(metadata?.cycles)} cycles`,
    `${formatInt(metadata?.agent_count)} agents`,
    `${formatInt(metadata?.response_count)} responses`,
    `Status ${statusText}`,
  ].join(" · ");

  return (
    <header className="report-header-block">
      <div className="report-meta">
        <span className="report-tag">Prediction Report</span>
        <span className="report-id" title={`ID: ${runId}`}>
          ID: {compactRunId}
        </span>
        <span className="report-status">{statusText}</span>
      </div>
      <h1 className="main-title">
        {metadata?.event_name || "Simulation Intelligence Report"}
      </h1>
      <p className="sub-title">{subtitle}</p>
      <div className="report-footnote">Deterministic signature {sig}...</div>
      <div className="header-divider" />
    </header>
  );
}

function TabStrip({ tabs, active, onChange }) {
  return (
    <nav className="tab-strip">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`tab-strip__btn ${active === tab.id ? "is-active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          <span className="tab-strip__idx">{tab.index}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}

function WorkflowRail({ steps, activeStep, responseCount }) {
  const progress = steps.length ? ((activeStep + 1) / steps.length) * 100 : 0;

  return (
    <aside className="workflow-rail">
      <div className="workflow-rail__header">
        <p className="workflow-rail__kicker">Execution Flow</p>
        <h3>Report pipeline</h3>
        <p>{formatInt(responseCount)} response rows processed</p>
      </div>

      <div className="workflow-progress">
        <div className="workflow-progress__track">
          <div
            className="workflow-progress__fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p>{Math.round(progress)}% complete</p>
      </div>

      <div className="workflow-list">
        {steps.map((step, idx) => {
          const done = idx < activeStep;
          const current = idx === activeStep;
          return (
            <article
              key={step.id}
              className={`workflow-item ${done ? "is-done" : ""} ${current ? "is-current" : ""}`}
            >
              <div className="workflow-item__line" />
              <div className="workflow-item__dot" />
              <div className="workflow-item__body">
                <p className="workflow-item__title">
                  <span>{step.index}</span>
                  {step.title}
                </p>
                <p className="workflow-item__meta">{step.meta}</p>
              </div>
            </article>
          );
        })}
      </div>

      <div className="workflow-rail__foot">
        <p>Deterministic export signature locked.</p>
      </div>
    </aside>
  );
}

function DarkTip({ active, payload, label }) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  return (
    <div className="chart-tip">
      <p className="chart-tip__title">Cycle {label}</p>
      {payload.map((entry, idx) => (
        <p key={idx} style={{ color: entry.color || TOKENS.text }}>
          {entry.name}:{" "}
          {typeof entry.value === "number"
            ? entry.value.toFixed(3)
            : entry.value}
        </p>
      ))}
    </div>
  );
}

function BehaviorTrend({ rows }) {
  const data = safeArray(rows);

  if (!data.length) {
    return <p className="muted-empty">No behavior trend data.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart
        data={data}
        margin={{ top: 10, right: 14, left: -14, bottom: 0 }}
      >
        <defs>
          <linearGradient id="migFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={TOKENS.primary} stopOpacity={0.45} />
            <stop offset="95%" stopColor={TOKENS.primary} stopOpacity={0.03} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={TOKENS.borderSoft} vertical={false} />
        <XAxis
          dataKey="cycle"
          tick={{ fill: TOKENS.subtle, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: TOKENS.subtle, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<DarkTip />} />
        <Area
          type="monotone"
          dataKey="migrating_rate"
          name="Migration rate"
          stroke={TOKENS.primary}
          fill="url(#migFill)"
          strokeWidth={2.2}
        />
        <Line
          type="monotone"
          dataKey="trust_drop_rate"
          name="Trust drop"
          stroke={TOKENS.danger}
          strokeWidth={2.3}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="avg_sentiment"
          name="Sentiment"
          stroke={TOKENS.green}
          strokeWidth={2.1}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function DecisionDonut({ rows }) {
  const data = safeArray(rows).slice(0, 8);

  if (!data.length) {
    return <p className="muted-empty">No decision distribution.</p>;
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            innerRadius={54}
            outerRadius={84}
            paddingAngle={2.5}
          >
            {data.map((_, idx) => (
              <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: TOKENS.bgElevated,
              border: `1px solid ${TOKENS.border}`,
              color: TOKENS.text,
              borderRadius: 8,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="legend-grid">
        {data.map((row, idx) => (
          <p key={row.label}>
            <span
              style={{ background: CHART_COLORS[idx % CHART_COLORS.length] }}
            />
            {row.label} ({formatInt(row.value)})
          </p>
        ))}
      </div>
    </div>
  );
}

function RoleBars({ rows, color = TOKENS.violet }) {
  const data = safeArray(rows).slice(0, 10);

  if (!data.length) {
    return <p className="muted-empty">No role distribution.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 8, right: 4, left: -22, bottom: 0 }}>
        <CartesianGrid stroke={TOKENS.borderSoft} vertical={false} />
        <XAxis
          dataKey="label"
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
          contentStyle={{
            background: TOKENS.bgElevated,
            border: `1px solid ${TOKENS.border}`,
            color: TOKENS.text,
            borderRadius: 8,
          }}
        />
        <Bar dataKey="value" radius={[5, 5, 0, 0]} fill={color} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function EmotionRadar({ rows }) {
  const data = safeArray(rows).slice(0, 6);

  if (!data.length) {
    return <p className="muted-empty">No emotion landscape.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <RadarChart data={data}>
        <PolarGrid stroke={TOKENS.borderSoft} />
        <PolarAngleAxis
          dataKey="label"
          tick={{ fill: TOKENS.subtle, fontSize: 10 }}
        />
        <Radar
          dataKey="value"
          stroke={TOKENS.violet}
          fill={TOKENS.violet}
          fillOpacity={0.26}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function HeatmapGrid({ rows, regions }) {
  const data = safeArray(rows);
  const headers = safeArray(regions);

  if (!data.length || !headers.length) {
    return <p className="muted-empty">No heatmap data.</p>;
  }

  const maxValue = Math.max(
    1,
    ...data.flatMap((row) =>
      headers.map((region) => safeNumber(row[region], 0)),
    ),
  );

  return (
    <div className="heatmap-grid-wrapper">
      <div
        className="heatmap-grid"
        style={{
          gridTemplateColumns: `48px repeat(${headers.length}, minmax(80px, 1fr))`,
        }}
      >
        <div className="heatmap-head heatmap-head--blank" />
        {headers.map((region) => (
          <div key={region} className="heatmap-head" title={region}>
            {truncate(region, 14)}
          </div>
        ))}
        {data.map((row) => (
          <React.Fragment key={`row-${row.cycle}`}>
            <div className="heatmap-cycle">{cycleLabel(row.cycle)}</div>
            {headers.map((region) => {
              const value = safeNumber(row[region], 0);
              const intensity = value / maxValue;
              return (
                <div
                  key={`${row.cycle}-${region}`}
                  className="heatmap-cell"
                  title={`${region}: ${value}`}
                  style={{
                    background: `rgba(84, 182, 255, ${0.06 + intensity * 0.82})`,
                    borderColor: `rgba(84, 182, 255, ${0.1 + intensity * 0.35})`,
                  }}
                >
                  {value}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function NetworkOrbit({ nodes, edges }) {
  const canvasRef = useRef(null);
  const nodeList = safeArray(nodes).slice(0, 16);
  const edgeList = safeArray(edges);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !nodeList.length) {
      return undefined;
    }

    const context = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    const cx = width / 2;
    const cy = height / 2;

    const points = nodeList.map((node, idx) => {
      const angle = (Math.PI * 2 * idx) / nodeList.length - Math.PI / 2;
      const radius = Math.min(width, height) * 0.33;
      return {
        id: node.agent_id,
        degree: safeNumber(node.degree, 1),
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      };
    });

    const pointMap = Object.fromEntries(
      points.map((point) => [point.id, point]),
    );
    const allowed = new Set(points.map((point) => point.id));
    let frame = 0;
    let raf = 0;

    const draw = () => {
      frame += 1;
      context.clearRect(0, 0, width, height);

      edgeList.slice(0, 220).forEach((edge, idx) => {
        if (!allowed.has(edge.source) || !allowed.has(edge.target)) {
          return;
        }
        const source = pointMap[edge.source];
        const target = pointMap[edge.target];
        if (!source || !target) {
          return;
        }

        const alpha =
          0.08 + ((Math.sin(frame * 0.03 + idx * 0.6) + 1) / 2) * 0.18;
        context.beginPath();
        context.strokeStyle = `rgba(84, 182, 255, ${alpha.toFixed(3)})`;
        context.lineWidth = 1;
        context.moveTo(source.x, source.y);
        context.lineTo(target.x, target.y);
        context.stroke();
      });

      points.forEach((point, idx) => {
        const pulse = (Math.sin(frame * 0.06 + idx) + 1) / 2;
        const radius = 4 + point.degree / 9;
        const core = idx === 0 ? TOKENS.amber : TOKENS.primary;

        const gradient = context.createRadialGradient(
          point.x,
          point.y,
          0,
          point.x,
          point.y,
          radius * 4,
        );
        gradient.addColorStop(0, `${core}99`);
        gradient.addColorStop(1, "rgba(84, 182, 255, 0)");

        context.beginPath();
        context.fillStyle = gradient;
        context.arc(
          point.x,
          point.y,
          radius * (2.4 + pulse * 0.5),
          0,
          Math.PI * 2,
        );
        context.fill();

        context.beginPath();
        context.fillStyle = core;
        context.arc(point.x, point.y, radius, 0, Math.PI * 2);
        context.fill();
      });

      raf = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(raf);
  }, [nodes, edges]);

  if (!nodeList.length) {
    return <p className="muted-empty">No network graph data.</p>;
  }

  return (
    <canvas
      ref={canvasRef}
      width={430}
      height={300}
      className="network-canvas"
    />
  );
}

function AnomalyFeed({ anomalies, notes }) {
  const anomalyList = safeArray(anomalies);
  const notesList = safeArray(notes);

  return (
    <div>
      {anomalyList.length ? (
        <div className="anomaly-list">
          {anomalyList.map((item, idx) => (
            <article
              key={`${item}-${idx}`}
              className="anomaly-item"
              style={{ borderColor: `${TOKENS.danger}48` }}
            >
              <span
                className="anomaly-item__dot"
                style={{ background: TOKENS.danger }}
              />
              <p>{item}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted-empty">No anomaly spikes detected for this run.</p>
      )}

      <div className="notes-box">
        <p>Final notes</p>
        {notesList.map((note, idx) => (
          <span key={`${note}-${idx}`}>{note}</span>
        ))}
      </div>
    </div>
  );
}

function RawEvidenceTable({ rows }) {
  const data = safeArray(rows).slice(0, 40);

  if (!data.length) {
    return <p className="muted-empty">No raw response rows.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Cycle</th>
            <th>Agent</th>
            <th>Region</th>
            <th>Migrating</th>
            <th>Trust drop</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={`${row.id || row.agent_id || row.agent_name}-${idx}`}>
              <td>{row.cycle ?? "-"}</td>
              <td>
                {truncate(row.agent_name || row.agent_id || "unknown", 18)}
              </td>
              <td>{truncate(row.agent_region || "unknown", 18)}</td>
              <td>{row.is_migrating ? "yes" : "no"}</td>
              <td>{row.is_less_trusting ? "yes" : "no"}</td>
              <td title={String(row.action || "")}>
                {truncate(row.action || "", 90)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

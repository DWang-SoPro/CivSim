"use client";

type Achievement = {
  turn?: number;
  year?: number;
  title: string;
  summary?: string;
};

export type GameOverReport = {
  reason: string;
  reason_label?: string;
  civ_name: string;
  total_turns: number;
  year_start: number;
  year_end: number;
  peak_population: number;
  peak_territory: number;
  achievements: Achievement[];
  historical_lesson: string;
};

type GameOverOverlayProps = {
  report: GameOverReport;
  onLoadLatest: () => void;
  onNewGame: () => void;
};

function formatYear(year: number): string {
  if (year < 0) {
    return `公元前${Math.abs(Math.round(year))}年`;
  }
  if (year === 0) {
    return "公元元年";
  }
  return `公元${Math.round(year)}年`;
}

export function GameOverOverlay({
  report,
  onLoadLatest,
  onNewGame,
}: GameOverOverlayProps) {
  const reasonText = report.reason_label || report.reason;

  return (
    <div className="gameover-overlay" role="dialog" aria-modal="true" aria-labelledby="gameover-title">
      <div className="gameover-panel parchment">
        <div className="gameover-seal" aria-hidden="true">
          终
        </div>
        <h2 id="gameover-title" className="gameover-title">
          文明终结报告
        </h2>
        <p className="gameover-civ">
          {report.civ_name}
          <span className="gameover-span">
            {formatYear(report.year_start)} — {formatYear(report.year_end)}
          </span>
        </p>
        <p className="gameover-meta">历 {report.total_turns} 回合</p>

        <div className="gold-divider gameover-divider" aria-hidden="true">
          <span className="gold-divider-mark" />
          <span className="gold-divider-mark" />
        </div>

        <section className="gameover-section">
          <h3>终结原因</h3>
          <p className="gameover-reason">{reasonText}</p>
        </section>

        <section className="gameover-section">
          <h3>巅峰数据</h3>
          <ul className="gameover-peaks">
            <li>
              <span>人口峰值</span>
              <strong>{report.peak_population.toLocaleString("zh-CN")}</strong>
            </li>
            <li>
              <span>领土峰值</span>
              <strong>{report.peak_territory.toLocaleString("zh-CN")} km²</strong>
            </li>
          </ul>
        </section>

        <section className="gameover-section">
          <h3>重大成就</h3>
          {report.achievements.length === 0 ? (
            <p className="gameover-empty">史册未载大事。</p>
          ) : (
            <ul className="gameover-achievements">
              {report.achievements.map((item, index) => (
                <li key={`${item.title}-${index}`}>
                  <strong>{item.title}</strong>
                  {item.summary ? <span>{item.summary}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="gameover-section">
          <h3>历史教训</h3>
          <blockquote className="gameover-lesson">
            {report.historical_lesson}
          </blockquote>
        </section>

        <div className="gameover-actions">
          <button type="button" className="btn-ghost" onClick={onLoadLatest}>
            读档
          </button>
          <button type="button" className="btn-primary" onClick={onNewGame}>
            新局
          </button>
        </div>
      </div>
    </div>
  );
}

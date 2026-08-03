"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

type CivState = {
  civ_name: string;
  template_id: string;
  turn: number;
  year: number;
  population: number;
  tech_agriculture: number;
  tech_engineering: number;
  tech_knowledge: number;
  bureaucratization: number;
  stability: number;
  authority: number;
  class_tension: number | null;
  elite_cohesion: number | null;
  [key: string]: unknown;
};

type DimensionChanges = Record<string, string>;

type ChangeableStateKey =
  | "population"
  | "stability"
  | "authority"
  | "class_tension"
  | "elite_cohesion"
  | "bureaucratization"
  | "tech_agriculture"
  | "tech_engineering"
  | "tech_knowledge";

type NewGameResponse = {
  game_id: string;
  state: CivState;
  seed: number;
  opening_narrative: string;
};

type SubmitActionResponse = {
  turn: number;
  settlement_skipped: boolean;
  vague_prompts: string[];
  dimension_changes: DimensionChanges;
  state: CivState;
  ws_stream_id: string | null;
};

type NarrativePayload = {
  text?: string;
  full_text?: string;
  message?: string;
  state?: CivState;
  dimension_changes?: DimensionChanges;
  reason?: string | null;
  game_over_reason?: string | null;
};

type NarrativeFrame =
  | {
      type: "ping";
      turn?: number;
      stream_id?: null;
      payload?: NarrativePayload;
    }
  | {
      type:
        | "narrative_start"
        | "narrative_delta"
        | "narrative_end"
        | "narrative_error"
        | "state_update"
        | "game_over";
      turn: number;
      stream_id: string;
      payload?: NarrativePayload;
    };

type PendingAction = {
  token: number;
  turn: number;
  streamId: string;
};

type CompletedStream = {
  turn: number;
  streamId: string;
};

type WebSocketStatus = "idle" | "connecting" | "open" | "error";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const WS_BASE_URL = API_BASE_URL.replace(/^http:/, "ws:").replace(
  /^https:/,
  "wss:",
);

const websocketStatusLabel: Record<WebSocketStatus, string> = {
  idle: "未连接",
  connecting: "连接中",
  open: "已连接",
  error: "连接失败，正在重试",
};

const dimensionChangeKeys: Record<ChangeableStateKey, readonly string[]> = {
  // food 是引擎基于人口增长率生成的趋势提示，CivState 无独立 food 字段。
  population: ["population", "food"],
  stability: ["stability"],
  authority: ["authority"],
  class_tension: ["class_tension"],
  elite_cohesion: ["elite_cohesion"],
  bureaucratization: ["bureaucratization"],
  tech_agriculture: ["tech_agriculture"],
  tech_engineering: ["tech_engineering"],
  tech_knowledge: ["tech_knowledge"],
};

function formatErrorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  }

  return fallback;
}

async function readResponse<T>(response: Response): Promise<T> {
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(formatErrorDetail(body, `请求失败（${response.status}）`));
  }

  return body as T;
}

function formatYear(year: number): string {
  return year < 0 ? `公元前 ${Math.abs(year)} 年` : `公元 ${year} 年`;
}

function formatMetric(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return String(Math.round(value * 100) / 100);
}

function getDimensionChange(
  changes: DimensionChanges,
  stateKey: ChangeableStateKey,
): string | undefined {
  for (const changeKey of dimensionChangeKeys[stateKey]) {
    const change = changes[changeKey];
    if (typeof change === "string" && change.trim()) {
      return change.trim();
    }
  }

  return undefined;
}

type ChangeDirection = "up" | "down" | "zero";

function getChangeDirection(change: string): ChangeDirection {
  const normalized = change.trim();
  if (/^[+＋\-−－]?0(?:\.0+)?%?$/.test(normalized)) {
    return "zero";
  }
  if (/^[+＋↑]/.test(normalized)) {
    return "up";
  }
  if (/^[\-−－↓]/.test(normalized)) {
    return "down";
  }
  return "zero";
}

function formatChangeAmount(change: string): string {
  return change.trim().replace(/^[+＋\-−－↑↓]\s*/, "");
}

function StateMetric({
  value,
  change,
}: {
  value: string | number;
  change?: string;
}) {
  if (!change) {
    return <>{value}</>;
  }

  const direction = getChangeDirection(change);
  const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "→";
  const amount = formatChangeAmount(change);
  const directionLabel =
    direction === "up" ? "上升" : direction === "down" ? "下降" : "无变化";

  return (
    <>
      {value}
      <span
        className={`dimension-change dimension-change--${direction}`}
        aria-label={`${directionLabel} ${amount}`}
      >
        {arrow}{amount}
      </span>
    </>
  );
}

export default function Home() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<CivState | null>(null);
  const [command, setCommand] = useState("");
  const [narrative, setNarrative] = useState("");
  const [dimensionChanges, setDimensionChanges] =
    useState<DimensionChanges>({});
  const [clarification, setClarification] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [gameOverReason, setGameOverReason] = useState<string | null>(null);
  const [websocketStatus, setWebsocketStatus] =
    useState<WebSocketStatus>("idle");

  const websocketRef = useRef<WebSocket | null>(null);
  const pendingActionRef = useRef<PendingAction | null>(null);
  const completedStreamRef = useRef<CompletedStream | null>(null);
  const stateTurnRef = useRef<number | null>(null);
  const actionTokenRef = useRef(0);
  const websocketInterruptedRef = useRef(false);

  useEffect(() => {
    if (!gameId) {
      setWebsocketStatus("idle");
      return;
    }

    let disposed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (disposed) {
        return;
      }

      setWebsocketStatus("connecting");
      const websocket = new WebSocket(
        `${WS_BASE_URL}/api/game/${encodeURIComponent(gameId)}/ws`,
      );
      websocketRef.current = websocket;

      websocket.onopen = () => {
        if (!disposed && websocketRef.current === websocket) {
          setWebsocketStatus("open");
        }
      };

      websocket.onmessage = (event) => {
        if (
          disposed ||
          websocketRef.current !== websocket ||
          typeof event.data !== "string"
        ) {
          return;
        }

        let frame: NarrativeFrame;
        try {
          frame = JSON.parse(event.data) as NarrativeFrame;
        } catch {
          setError("收到了无法解析的叙事消息。");
          return;
        }

        if (frame.type === "ping") {
          return;
        }

        if (frame.type === "game_over") {
          const completed = completedStreamRef.current;

          if (
            !completed ||
            frame.turn !== completed.turn ||
            frame.stream_id !== completed.streamId
          ) {
            return;
          }

          pendingActionRef.current = null;
          setSubmitting(false);
          setGameOver(true);
          setGameOverReason(
            frame.payload?.reason ??
              frame.payload?.game_over_reason ??
              "文明进程已结束。",
          );
          return;
        }

        const pending = pendingActionRef.current;

        // 回合号可能在失败重试时相同，因此 turn 与 stream_id 必须同时匹配。
        if (
          !pending ||
          frame.turn !== pending.turn ||
          frame.stream_id !== pending.streamId
        ) {
          return;
        }

        switch (frame.type) {
          case "narrative_start":
            setNarrative("");
            setClarification([]);
            break;
          case "narrative_delta": {
            const text = frame.payload?.text;
            if (typeof text === "string") {
              setNarrative((current) => current + text);
            }
            break;
          }
          case "narrative_end":
            if (typeof frame.payload?.full_text === "string") {
              setNarrative(frame.payload.full_text);
            }
            // 叙事结束不代表状态已提交；继续等 state_update。
            break;
          case "state_update": {
            const nextState = frame.payload?.state;
            if (!nextState || nextState.turn !== pending.turn) {
              setError("收到的回合状态与当前政令不匹配。");
              return;
            }

            stateTurnRef.current = nextState.turn;
            completedStreamRef.current = {
              turn: pending.turn,
              streamId: pending.streamId,
            };
            pendingActionRef.current = null;
            setState(nextState);
            setDimensionChanges(frame.payload?.dimension_changes ?? {});
            setSubmitting(false);
            if (websocketInterruptedRef.current) {
              setError("叙事连接曾中断；数值已恢复，但本回合叙事可能不完整。");
            }
            websocketInterruptedRef.current = false;
            break;
          }
          case "narrative_error":
            pendingActionRef.current = null;
            websocketInterruptedRef.current = false;
            setError(frame.payload?.message ?? "叙事生成失败。");
            setSubmitting(false);
            break;
        }
      };

      websocket.onerror = () => {
        if (!disposed && websocketRef.current === websocket) {
          setWebsocketStatus("error");
        }
      };

      websocket.onclose = () => {
        if (disposed || websocketRef.current !== websocket) {
          return;
        }

        websocketRef.current = null;
        if (pendingActionRef.current) {
          websocketInterruptedRef.current = true;
          // 不丢弃仍在途的政令。POST /action 的响应包含权威 state 与
          // dimension_changes，可在 WebSocket 丢帧时完成本回合并避免重试重算。
          setError("叙事连接中断，正在等待本回合的数值结果。");
        }
        setWebsocketStatus("error");
        reconnectTimer = setTimeout(connect, 1000);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      const websocket = websocketRef.current;
      websocketRef.current = null;
      websocket?.close();
    };
  }, [gameId]);

  async function createGame() {
    setCreating(true);
    setError(null);
    setDimensionChanges({});

    try {
      const response = await fetch(`${API_BASE_URL}/api/game/new`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: "zhou", seed: null }),
      });
      const result = await readResponse<NewGameResponse>(response);

      const previousWebsocket = websocketRef.current;
      websocketRef.current = null;
      previousWebsocket?.close();

      pendingActionRef.current = null;
      completedStreamRef.current = null;
      websocketInterruptedRef.current = false;
      stateTurnRef.current = result.state.turn;
      actionTokenRef.current += 1;

      setGameId(result.game_id);
      setState(result.state);
      setCommand("");
      setNarrative(result.opening_narrative);
      setClarification([]);
      setSubmitting(false);
      setGameOver(false);
      setGameOverReason(null);
      setWebsocketStatus("connecting");
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "新建游戏失败。",
      );
    } finally {
      setCreating(false);
    }
  }

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const playerInput = command.trim();
    const currentTurn = stateTurnRef.current;
    if (
      !gameId ||
      currentTurn === null ||
      !playerInput ||
      creating ||
      submitting ||
      pendingActionRef.current !== null ||
      gameOver ||
      websocketStatus !== "open"
    ) {
      return;
    }

    const token = ++actionTokenRef.current;
    const streamId = crypto.randomUUID();
    pendingActionRef.current = {
      token,
      turn: currentTurn + 1,
      streamId,
    };
    websocketInterruptedRef.current = false;
    setSubmitting(true);
    setCommand("");
    setError(null);
    setClarification([]);
    setDimensionChanges({});

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/game/${encodeURIComponent(gameId)}/action`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            input: playerInput,
            rng_seed: null,
            stream_id: streamId,
          }),
        },
      );
      const result = await readResponse<SubmitActionResponse>(response);
      const pending = pendingActionRef.current;

      // state_update 可能比 HTTP 响应更早到达；若已完成就忽略迟到的响应。
      if (!pending || pending.token !== token) {
        return;
      }

      if (result.settlement_skipped) {
        pendingActionRef.current = null;
        websocketInterruptedRef.current = false;
        setError(null);
        setNarrative("");
        setClarification(
          result.vague_prompts?.length
            ? result.vague_prompts
            : ["请把政令说得更具体一些。"],
        );
        setSubmitting(false);
        return;
      }

      if (result.turn !== pending.turn || result.state.turn !== pending.turn) {
        pendingActionRef.current = null;
        setError("服务端返回了意外的回合号。");
        setSubmitting(false);
        return;
      }

      if (result.ws_stream_id !== pending.streamId) {
        pendingActionRef.current = null;
        setError("服务端返回了意外的叙事流 ID。");
        setSubmitting(false);
        return;
      }

      // 正常情况下 state_update 会先完成回合；若 WebSocket 中断而该帧
      // 丢失，则以同一 stream_id 的 HTTP 权威快照恢复，避免前后端错回合。
      stateTurnRef.current = result.state.turn;
      completedStreamRef.current = {
        turn: pending.turn,
        streamId: pending.streamId,
      };
      pendingActionRef.current = null;
      setState(result.state);
      setDimensionChanges(result.dimension_changes);
      setSubmitting(false);
      if (websocketInterruptedRef.current) {
        setError("叙事连接曾中断；数值已恢复，但本回合叙事可能不完整。");
      }
      websocketInterruptedRef.current = false;
    } catch (requestError) {
      const pending = pendingActionRef.current;
      if (!pending || pending.token !== token) {
        return;
      }

      pendingActionRef.current = null;
      websocketInterruptedRef.current = false;
      setCommand(playerInput);
      setError(
        requestError instanceof Error ? requestError.message : "政令提交失败。",
      );
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>文明灵 CivSim v2</h1>

      <button type="button" onClick={createGame} disabled={creating || submitting}>
        {creating ? "新建中……" : "新建游戏（西周）"}
      </button>

      {error && <p role="alert">错误：{error}</p>}
      {gameOver && (
        <p role="status">游戏结束：{gameOverReason ?? "文明进程已结束。"}</p>
      )}

      {state && gameId && (
        <>
          <section>
            <h2>当前状态</h2>
            <dl>
              <dt>文明</dt>
              <dd>{state.civ_name}</dd>
              <dt>年份</dt>
              <dd>{formatYear(state.year)}</dd>
              <dt>回合</dt>
              <dd>{state.turn}</dd>
              <dt>人口</dt>
              <dd>
                <StateMetric
                  value={state.population.toLocaleString("zh-CN")}
                  change={getDimensionChange(dimensionChanges, "population")}
                />
              </dd>
              <dt>稳定</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.stability)}
                  change={getDimensionChange(dimensionChanges, "stability")}
                />
              </dd>
              <dt>统治力</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.authority)}
                  change={getDimensionChange(dimensionChanges, "authority")}
                />
              </dd>
              <dt>阶级张力</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.class_tension)}
                  change={getDimensionChange(dimensionChanges, "class_tension")}
                />
              </dd>
              <dt>精英凝聚力</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.elite_cohesion)}
                  change={getDimensionChange(dimensionChanges, "elite_cohesion")}
                />
              </dd>
              <dt>官僚化</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.bureaucratization)}
                  change={getDimensionChange(
                    dimensionChanges,
                    "bureaucratization",
                  )}
                />
              </dd>
              <dt>农业技术</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.tech_agriculture)}
                  change={getDimensionChange(
                    dimensionChanges,
                    "tech_agriculture",
                  )}
                />
              </dd>
              <dt>工程技术</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.tech_engineering)}
                  change={getDimensionChange(
                    dimensionChanges,
                    "tech_engineering",
                  )}
                />
              </dd>
              <dt>知识技术</dt>
              <dd>
                <StateMetric
                  value={formatMetric(state.tech_knowledge)}
                  change={getDimensionChange(
                    dimensionChanges,
                    "tech_knowledge",
                  )}
                />
              </dd>
            </dl>
            <p>叙事连接：{websocketStatusLabel[websocketStatus]}</p>
          </section>

          <section>
            <h2>下达政令</h2>
            <form onSubmit={submitAction}>
              <label htmlFor="command">政令：</label>
              <input
                id="command"
                name="command"
                type="text"
                value={command}
                onChange={(event) => setCommand(event.target.value)}
                placeholder="兴修水利"
                disabled={creating || submitting || gameOver}
              />
              <button
                type="submit"
                disabled={
                  creating ||
                  submitting ||
                  gameOver ||
                  websocketStatus !== "open" ||
                  command.trim().length === 0
                }
              >
                {submitting ? "执行中……" : "执行"}
              </button>
            </form>
          </section>

          {clarification.length > 0 && (
            <section aria-live="polite">
              <h2>需要说明</h2>
              <ul>
                {clarification.map((prompt, index) => (
                  <li key={`${index}-${prompt}`}>{prompt}</li>
                ))}
              </ul>
            </section>
          )}

          <section aria-live="polite">
            <h2>史官叙事</h2>
            <p>{narrative || "尚无叙事。"}</p>
          </section>
        </>
      )}
    </main>
  );
}

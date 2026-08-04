"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { ActionMenu, type ActionMenuItem } from "@/components/ActionMenu";
import { emblemSrc } from "@/components/CivEmblem";
import {
  GameOverOverlay,
  type GameOverReport,
} from "@/components/GameOverOverlay";
import {
  SaveLoadModal,
  type SaveListItem,
} from "@/components/SaveLoadModal";
import { StartScreen } from "@/components/StartScreen";
import {
  StatusPanel,
  type CivStateView,
  type DimensionChanges,
} from "@/components/StatusPanel";
import { TemplateSelect } from "@/components/TemplateSelect";
import type { CivTemplateMeta } from "@/lib/civTemplates";

type CivState = CivStateView & {
  [key: string]: unknown;
};

type NewGameResponse = {
  game_id: string;
  state: CivState;
  seed: number;
  opening_narrative: string;
  history?: Array<{ turn: number; year: number; text: string }> | null;
  status?: string | null;
  game_over_reason?: string | null;
  autosave_id?: string | null;
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
  reason_label?: string;
  civ_name?: string;
  total_turns?: number;
  year_start?: number;
  year_end?: number;
  peak_population?: number;
  peak_territory?: number;
  achievements?: GameOverReport["achievements"];
  historical_lesson?: string;
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

/** 开始界面 → 模板选择 → 游戏主界面 */
type AppScreen = "start" | "templates" | "playing";

type NarrativeEntry = {
  turn: number;
  year: number;
  text: string;
  streaming?: boolean;
};

function pickLatestContinueSave(list: SaveListItem[]): SaveListItem | null {
  if (list.length === 0) {
    return null;
  }
  const autosave = list.find((item) => item.is_autosave);
  return autosave ?? list[0] ?? null;
}

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const WS_BASE_URL = API_BASE_URL.replace(/^http:/, "ws:").replace(
  /^https:/,
  "wss:",
);

/** 提交后等待首帧 / HTTP 结果的最长秒数；超时解除加载态并允许重试。 */
const ACTION_WAIT_TIMEOUT_MS = 120_000;

const websocketStatusLabel: Record<WebSocketStatus, string> = {
  idle: "未连接",
  connecting: "连接中",
  open: "已连接",
  error: "连接失败，正在重试",
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
  const rounded = Math.round(year);
  return rounded < 0
    ? `公元前${Math.abs(rounded)}年`
    : `公元${rounded}年`;
}

function sealGlyph(civName: string): string {
  const trimmed = civName.trim();
  return trimmed ? trimmed[0]! : "史";
}

function updateNarrativeEntry(
  entries: NarrativeEntry[],
  turn: number,
  year: number,
  updater: (text: string) => string,
  streaming = true,
): NarrativeEntry[] {
  const index = entries.findIndex((entry) => entry.turn === turn);
  if (index === -1) {
    return [...entries, { turn, year, text: updater(""), streaming }];
  }

  return entries.map((entry, i) =>
    i === index
      ? {
          ...entry,
          year,
          text: updater(entry.text),
          streaming,
        }
      : entry,
  );
}

export default function Home() {
  const [screen, setScreen] = useState<AppScreen>("start");
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<CivState | null>(null);
  const [command, setCommand] = useState("");
  const [narrativeEntries, setNarrativeEntries] = useState<NarrativeEntry[]>(
    [],
  );
  const [dimensionChanges, setDimensionChanges] =
    useState<DimensionChanges>({});
  const [clarification, setClarification] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  /** 整回合锁：提交后到 state_update / 模糊短路 / 失败，防止重复提交。 */
  const [submitting, setSubmitting] = useState(false);
  /** 提交→narrative_start（或 HTTP 短路/失败）的可见加载态。 */
  const [awaitingNarrative, setAwaitingNarrative] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [gameOverReason, setGameOverReason] = useState<string | null>(null);
  const [gameOverReport, setGameOverReport] = useState<GameOverReport | null>(
    null,
  );
  const [websocketStatus, setWebsocketStatus] =
    useState<WebSocketStatus>("idle");
  const [menuItems, setMenuItems] = useState<ActionMenuItem[]>([]);
  const [menuLoading, setMenuLoading] = useState(false);
  /** 递增以清空行动菜单勾选态（提交成功开始后 / 新局） */
  const [menuSelectionResetKey, setMenuSelectionResetKey] = useState(0);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveModalMode, setSaveModalMode] = useState<"save" | "load">("save");
  const [saves, setSaves] = useState<SaveListItem[]>([]);
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    "zhou",
  );
  /** 从游戏内进入模板选择时，取消可回到主界面 */
  const [templatesReturnTo, setTemplatesReturnTo] = useState<
    "start" | "playing"
  >("start");

  const websocketRef = useRef<WebSocket | null>(null);
  const pendingActionRef = useRef<PendingAction | null>(null);
  const completedStreamRef = useRef<CompletedStream | null>(null);
  const stateTurnRef = useRef<number | null>(null);
  const actionTokenRef = useRef(0);
  const websocketInterruptedRef = useRef(false);
  const actionAbortRef = useRef<AbortController | null>(null);
  const actionWaitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const narrativeEndRef = useRef<HTMLDivElement | null>(null);
  const pendingYearRef = useRef<number | null>(null);
  const commandInputRef = useRef<HTMLTextAreaElement | null>(null);

  function clearActionWaitTimer() {
    if (actionWaitTimerRef.current !== null) {
      clearTimeout(actionWaitTimerRef.current);
      actionWaitTimerRef.current = null;
    }
  }

  function endAwaitingNarrative() {
    clearActionWaitTimer();
    setAwaitingNarrative(false);
  }

  /** 政令框随内容增高，上限约 6 行后内部滚动 */
  function resizeCommandInput() {
    const el = commandInputRef.current;
    if (!el) {
      return;
    }
    el.style.height = "auto";
    const maxHeight = Number.parseFloat(getComputedStyle(el).maxHeight);
    const next = Number.isFinite(maxHeight)
      ? Math.min(el.scrollHeight, maxHeight)
      : el.scrollHeight;
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > next + 1 ? "auto" : "hidden";
  }

  useEffect(() => {
    resizeCommandInput();
  }, [command]);

  useEffect(() => {
    narrativeEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [narrativeEntries, awaitingNarrative, clarification]);

  /** 开始界面预取存档，用于「继续上一局」 */
  useEffect(() => {
    if (screen !== "start") {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/game/saves`);
        const result = await readResponse<{ saves: SaveListItem[] }>(response);
        if (!cancelled) {
          setSaves(result.saves ?? []);
        }
      } catch {
        // 开始页不必因列档失败打断；读档时再提示
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [screen]);

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
          const isDebug = frame.stream_id === "debug-end";
          const matched =
            completed &&
            frame.turn === completed.turn &&
            frame.stream_id === completed.streamId;

          if (!isDebug && !matched) {
            return;
          }

          pendingActionRef.current = null;
          endAwaitingNarrative();
          setSubmitting(false);
          setGameOver(true);
          const payload = frame.payload;
          const reason =
            payload?.reason_label ??
            payload?.reason ??
            payload?.game_over_reason ??
            "文明进程已结束。";
          setGameOverReason(reason);
          if (
            payload &&
            typeof payload.civ_name === "string" &&
            typeof payload.historical_lesson === "string"
          ) {
            setGameOverReport({
              reason: payload.reason ?? "civilization_collapse",
              reason_label: payload.reason_label,
              civ_name: payload.civ_name,
              total_turns: payload.total_turns ?? frame.turn,
              year_start: payload.year_start ?? 0,
              year_end: payload.year_end ?? 0,
              peak_population: payload.peak_population ?? 0,
              peak_territory: payload.peak_territory ?? 0,
              achievements: payload.achievements ?? [],
              historical_lesson: payload.historical_lesson,
            });
          }
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

        const yearForTurn =
          pendingYearRef.current ??
          (typeof frame.payload?.state?.year === "number"
            ? frame.payload.state.year
            : 0);

        switch (frame.type) {
          case "narrative_start":
            // 首帧到达：处理中加载态结束，叙事开始流出；整回合锁仍保持到 state_update。
            endAwaitingNarrative();
            setClarification([]);
            setNarrativeEntries((entries) =>
              updateNarrativeEntry(
                entries,
                pending.turn,
                yearForTurn,
                () => "",
                true,
              ),
            );
            break;
          case "narrative_delta": {
            const text = frame.payload?.text;
            if (typeof text === "string") {
              setNarrativeEntries((entries) =>
                updateNarrativeEntry(
                  entries,
                  pending.turn,
                  yearForTurn,
                  (current) => current + text,
                  true,
                ),
              );
            }
            break;
          }
          case "narrative_end":
            if (typeof frame.payload?.full_text === "string") {
              const fullText = frame.payload.full_text;
              setNarrativeEntries((entries) =>
                updateNarrativeEntry(
                  entries,
                  pending.turn,
                  yearForTurn,
                  () => fullText,
                  false,
                ),
              );
            } else {
              setNarrativeEntries((entries) =>
                entries.map((entry) =>
                  entry.turn === pending.turn
                    ? { ...entry, streaming: false }
                    : entry,
                ),
              );
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
            pendingYearRef.current = nextState.year;
            completedStreamRef.current = {
              turn: pending.turn,
              streamId: pending.streamId,
            };
            pendingActionRef.current = null;
            endAwaitingNarrative();
            setState(nextState);
            setDimensionChanges(frame.payload?.dimension_changes ?? {});
            setNarrativeEntries((entries) =>
              entries.map((entry) =>
                entry.turn === pending.turn
                  ? { ...entry, year: nextState.year, streaming: false }
                  : entry,
              ),
            );
            setSubmitting(false);
            void fetchActionMenu(gameId);
            if (websocketInterruptedRef.current) {
              setError("叙事连接曾中断；数值已恢复，但本回合叙事可能不完整。");
            }
            websocketInterruptedRef.current = false;
            break;
          }
          case "narrative_error":
            pendingActionRef.current = null;
            websocketInterruptedRef.current = false;
            endAwaitingNarrative();
            setError(
              `${frame.payload?.message ?? "叙事生成失败。"}请修改或重试政令。`,
            );
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

  useEffect(() => {
    return () => {
      clearActionWaitTimer();
      actionAbortRef.current?.abort();
    };
  }, []);

  async function fetchActionMenu(nextGameId: string) {
    setMenuLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/game/${encodeURIComponent(nextGameId)}/menu`,
      );
      const result = await readResponse<{ items: ActionMenuItem[] }>(response);
      setMenuItems(result.items ?? []);
    } catch {
      setMenuItems([]);
    } finally {
      setMenuLoading(false);
    }
  }

  async function refreshSaves() {
    const response = await fetch(`${API_BASE_URL}/api/game/saves`);
    const result = await readResponse<{ saves: SaveListItem[] }>(response);
    setSaves(result.saves ?? []);
  }

  function applyLoadedGame(result: NewGameResponse) {
    const previousWebsocket = websocketRef.current;
    websocketRef.current = null;
    previousWebsocket?.close();

    pendingActionRef.current = null;
    completedStreamRef.current = null;
    websocketInterruptedRef.current = false;
    actionAbortRef.current?.abort();
    actionAbortRef.current = null;
    clearActionWaitTimer();
    stateTurnRef.current = result.state.turn;
    pendingYearRef.current = result.state.year;
    actionTokenRef.current += 1;

    setGameId(result.game_id);
    setState(result.state);
    setCommand("");
    setMenuSelectionResetKey((key) => key + 1);
    setGameOver(result.status === "game_over");
    setGameOverReason(result.game_over_reason ?? null);
    setGameOverReport(null);
    setClarification([]);
    setDimensionChanges({});
    setAwaitingNarrative(false);
    setSubmitting(false);

    if (result.history && result.history.length > 0) {
      setNarrativeEntries(
        result.history.map((item) => ({
          turn: item.turn,
          year: item.year,
          text: item.text,
          streaming: false,
        })),
      );
    } else {
      setNarrativeEntries([
        {
          turn: result.state.turn === 0 ? 0 : result.state.turn,
          year: result.state.year,
          text: result.opening_narrative,
          streaming: false,
        },
      ]);
    }

    void fetchActionMenu(result.game_id);
    setScreen("playing");
  }

  function openTemplateSelect(from: "start" | "playing") {
    setTemplatesReturnTo(from);
    setSelectedTemplateId("zhou");
    setError(null);
    setScreen("templates");
  }

  function returnToStartMenu() {
    const previousWebsocket = websocketRef.current;
    websocketRef.current = null;
    previousWebsocket?.close();

    pendingActionRef.current = null;
    completedStreamRef.current = null;
    websocketInterruptedRef.current = false;
    actionAbortRef.current?.abort();
    actionAbortRef.current = null;
    clearActionWaitTimer();
    stateTurnRef.current = null;
    pendingYearRef.current = null;
    actionTokenRef.current += 1;

    setGameId(null);
    setState(null);
    setCommand("");
    setNarrativeEntries([]);
    setDimensionChanges({});
    setClarification([]);
    setMenuItems([]);
    setGameOver(false);
    setGameOverReason(null);
    setGameOverReport(null);
    setAwaitingNarrative(false);
    setSubmitting(false);
    setCreating(false);
    setSaveModalOpen(false);
    setSaveMessage(null);
    setError(null);
    setSelectedTemplateId("zhou");
    setScreen("start");
  }

  async function createGame(templateId = "zhou") {
    setCreating(true);
    setError(null);
    setDimensionChanges({});
    setGameOverReport(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/game/new`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: templateId, seed: null }),
      });
      const result = await readResponse<NewGameResponse>(response);
      applyLoadedGame(result);
      setError(null);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "开局失败";
      setError(message);
    } finally {
      setCreating(false);
    }
  }

  async function openSaveModal() {
    setSaveModalMode("save");
    setSaveMessage(null);
    setSaveModalOpen(true);
  }

  async function openLoadModal() {
    setSaveModalMode("load");
    setSaveMessage(null);
    setSaveBusy(true);
    setSaveModalOpen(true);
    try {
      await refreshSaves();
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "无法列出存档";
      setSaveMessage(message);
    } finally {
      setSaveBusy(false);
    }
  }

  async function confirmSave() {
    if (!gameId) {
      return;
    }
    setSaveBusy(true);
    setSaveMessage(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/game/${encodeURIComponent(gameId)}/save`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slot_name: null, autosave: false }),
        },
      );
      const result = await readResponse<{
        save_id: string;
        saved_at: string;
        slot_name: string | null;
      }>(response);
      setSaveMessage(`已保存：${result.slot_name ?? result.save_id}`);
      await refreshSaves();
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "存档失败";
      setSaveMessage(message);
    } finally {
      setSaveBusy(false);
    }
  }

  async function loadSave(saveId: string) {
    setSaveBusy(true);
    setSaveMessage(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/game/load/${encodeURIComponent(saveId)}`,
        { method: "POST" },
      );
      const result = await readResponse<NewGameResponse>(response);
      applyLoadedGame(result);
      setSaveModalOpen(false);
      setError(null);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "读档失败";
      setSaveMessage(message);
    } finally {
      setSaveBusy(false);
    }
  }

  async function deleteSave(saveId: string) {
    setSaveBusy(true);
    setSaveMessage(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/game/saves/${encodeURIComponent(saveId)}`,
        { method: "DELETE" },
      );
      await readResponse<{ ok: boolean; save_id: string }>(response);
      setSaves((prev) => prev.filter((item) => item.save_id !== saveId));
      setSaveMessage("存档已删除。");
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "删除存档失败";
      setSaveMessage(message);
    } finally {
      setSaveBusy(false);
    }
  }

  async function continueLatestSave() {
    const latest = pickLatestContinueSave(saves);
    if (!latest) {
      setError("没有可继续的存档。");
      return;
    }
    await loadSave(latest.save_id);
  }

  async function loadLatestAutosave() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/game/saves`);
      const result = await readResponse<{ saves: SaveListItem[] }>(response);
      const list = result.saves ?? [];
      setSaves(list);
      const latest = pickLatestContinueSave(list);
      if (!latest) {
        setError("没有可读取的存档。");
        return;
      }
      await loadSave(latest.save_id);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "读档失败";
      setError(message);
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
      awaitingNarrative ||
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
    actionAbortRef.current?.abort();
    const abortController = new AbortController();
    actionAbortRef.current = abortController;
    clearActionWaitTimer();
    actionWaitTimerRef.current = setTimeout(() => {
      actionWaitTimerRef.current = null;
      const pending = pendingActionRef.current;
      if (!pending || pending.token !== token) {
        return;
      }

      abortController.abort();
      pendingActionRef.current = null;
      websocketInterruptedRef.current = false;
      setAwaitingNarrative(false);
      setSubmitting(false);
      setCommand(playerInput);
      setError("处理超时，请重试政令。");
    }, ACTION_WAIT_TIMEOUT_MS);

    setSubmitting(true);
    setAwaitingNarrative(true);
    setCommand("");
    setMenuSelectionResetKey((key) => key + 1);
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
          signal: abortController.signal,
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
        endAwaitingNarrative();
        setError(null);
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
        endAwaitingNarrative();
        setError("服务端返回了意外的回合号。请重试政令。");
        setSubmitting(false);
        return;
      }

      if (result.ws_stream_id !== pending.streamId) {
        pendingActionRef.current = null;
        endAwaitingNarrative();
        setError("服务端返回了意外的叙事流 ID。请重试政令。");
        setSubmitting(false);
        return;
      }

      // 正常情况下 state_update 会先完成回合；若 WebSocket 中断而该帧
      // 丢失，则以同一 stream_id 的 HTTP 权威快照恢复，避免前后端错回合。
      stateTurnRef.current = result.state.turn;
      pendingYearRef.current = result.state.year;
      completedStreamRef.current = {
        turn: pending.turn,
        streamId: pending.streamId,
      };
      pendingActionRef.current = null;
      endAwaitingNarrative();
      setState(result.state);
      setDimensionChanges(result.dimension_changes);
      setNarrativeEntries((entries) =>
        entries.map((entry) =>
          entry.turn === pending.turn
            ? { ...entry, year: result.state.year, streaming: false }
            : entry,
        ),
      );
      setSubmitting(false);
      void fetchActionMenu(gameId);
      if (websocketInterruptedRef.current) {
        setError("叙事连接曾中断；数值已恢复，但本回合叙事可能不完整。");
      }
      websocketInterruptedRef.current = false;
    } catch (requestError) {
      const pending = pendingActionRef.current;
      if (!pending || pending.token !== token) {
        return;
      }

      // 超时路径已在 timer 里恢复 UI；此处避免覆盖超时文案。
      if (abortController.signal.aborted) {
        return;
      }

      pendingActionRef.current = null;
      websocketInterruptedRef.current = false;
      endAwaitingNarrative();
      setCommand(playerInput);
      const message =
        requestError instanceof Error
          ? requestError.message
          : "政令提交失败";
      setError(
        message.endsWith("。")
          ? `${message}请重试政令。`
          : `${message}。请重试政令。`,
      );
      setSubmitting(false);
    } finally {
      if (actionAbortRef.current === abortController) {
        actionAbortRef.current = null;
      }
    }
  }

  if (screen === "start" || !state || !gameId) {
    if (screen === "templates") {
      return (
        <>
          <TemplateSelect
            creating={creating}
            error={error}
            selectedId={selectedTemplateId}
            onSelect={(template: CivTemplateMeta) => {
              setSelectedTemplateId(template.id);
              setError(null);
            }}
            onConfirm={() => {
              if (selectedTemplateId) {
                void createGame(selectedTemplateId);
              }
            }}
            onBack={() => {
              setError(null);
              if (templatesReturnTo === "playing" && state && gameId) {
                setScreen("playing");
              } else {
                setScreen("start");
              }
            }}
          />
          <SaveLoadModal
            open={saveModalOpen}
            mode={saveModalMode}
            saves={saves}
            loading={saveBusy}
            message={saveMessage}
            onClose={() => setSaveModalOpen(false)}
            onConfirmSave={() => void confirmSave()}
            onLoad={(saveId) => void loadSave(saveId)}
            onDelete={(saveId) => deleteSave(saveId)}
          />
        </>
      );
    }

    const latestSave = pickLatestContinueSave(saves);
    return (
      <>
        <StartScreen
          creating={creating}
          error={error}
          latestSave={latestSave}
          onNewGame={() => openTemplateSelect("start")}
          onLoadSaves={() => void openLoadModal()}
          onContinue={
            latestSave ? () => void continueLatestSave() : undefined
          }
        />
        <SaveLoadModal
          open={saveModalOpen}
          mode={saveModalMode}
          saves={saves}
          loading={saveBusy}
          message={saveMessage}
          onClose={() => setSaveModalOpen(false)}
          onConfirmSave={() => void confirmSave()}
          onLoad={(saveId) => void loadSave(saveId)}
          onDelete={(saveId) => deleteSave(saveId)}
        />
      </>
    );
  }

  if (screen === "templates") {
    return (
      <>
        <TemplateSelect
          creating={creating}
          error={error}
          selectedId={selectedTemplateId}
          onSelect={(template: CivTemplateMeta) => {
            setSelectedTemplateId(template.id);
            setError(null);
          }}
          onConfirm={() => {
            if (selectedTemplateId) {
              void createGame(selectedTemplateId);
            }
          }}
          onBack={() => {
            setError(null);
            setScreen(templatesReturnTo === "playing" ? "playing" : "start");
          }}
        />
        <SaveLoadModal
          open={saveModalOpen}
          mode={saveModalMode}
          saves={saves}
          loading={saveBusy}
          message={saveMessage}
          onClose={() => setSaveModalOpen(false)}
          onConfirmSave={() => void confirmSave()}
          onLoad={(saveId) => void loadSave(saveId)}
          onDelete={(saveId) => deleteSave(saveId)}
        />
      </>
    );
  }

  const inputDisabled = creating || submitting || gameOver;
  const submitDisabled =
    inputDisabled ||
    websocketStatus !== "open" ||
    command.trim().length === 0;

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div className="seal" aria-hidden="true">
          {sealGlyph(state.civ_name)}
        </div>
        <div className="top-bar-meta">
          <h1 className="civ-name">{state.civ_name}</h1>
          <span className="top-meta-item">{formatYear(state.year)}</span>
          <span className="top-meta-item">第{state.turn}回合</span>
        </div>
        <div className="top-bar-actions">
          <span className="ws-status" title="叙事连接状态">
            {websocketStatusLabel[websocketStatus]}
          </span>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => void openSaveModal()}
            disabled={creating || submitting}
          >
            存档
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => void openLoadModal()}
            disabled={creating || submitting}
          >
            读档
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => openTemplateSelect("playing")}
            disabled={creating || submitting}
          >
            新局
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={returnToStartMenu}
            disabled={creating || submitting}
          >
            主菜单
          </button>
        </div>
      </header>

      {error && (
        <p className="banner banner--error" role="alert">
          {error}
        </p>
      )}
      {gameOver && !gameOverReport && (
        <p className="banner banner--status" role="status">
          游戏结束：{gameOverReason ?? "文明进程已结束。"}
        </p>
      )}

      <div className="main-grid">
        <StatusPanel state={state} dimensionChanges={dimensionChanges} />

        <section className="narrative-scroll parchment" aria-label="史官叙事">
          <div className="narrative-watermark" aria-hidden="true">
            <img
              src={emblemSrc(state.template_id)}
              alt=""
              width={320}
              height={320}
              draggable={false}
            />
          </div>

          <div className="narrative-scroll-inner">
            {narrativeEntries.length === 0 ? (
              <p className="narrative-empty">尚无叙事。</p>
            ) : (
              narrativeEntries.map((entry, index) => (
                <article
                  key={`${entry.turn}-${index}`}
                  className="narrative-entry"
                >
                  {index > 0 && (
                    <div className="gold-divider" aria-hidden="true">
                      <span className="gold-divider-mark" />
                      <span className="gold-divider-mark" />
                    </div>
                  )}
                  <div className="narrative-year">
                    <span className="narrative-year-end" aria-hidden="true" />
                    <span>
                      {formatYear(entry.year)}
                      {entry.turn === 0
                        ? " · 开局"
                        : ` · 第${entry.turn}回合`}
                    </span>
                    <span className="narrative-year-end" aria-hidden="true" />
                  </div>
                  <p
                    className={`narrative-text${
                      entry.streaming ? " narrative-text--streaming" : ""
                    }`}
                  >
                    {entry.text || (entry.streaming ? "" : "……")}
                  </p>
                </article>
              ))
            )}

            {clarification.length > 0 && (
              <aside className="scribe-ask" aria-live="polite">
                <p className="scribe-ask-label">史官问曰</p>
                {clarification.map((prompt, index) => (
                  <blockquote
                    key={`${index}-${prompt}`}
                    className="scribe-ask-quote"
                  >
                    「{prompt}」
                  </blockquote>
                ))}
                <p className="scribe-ask-hint">请把政令说得更具体一些，再行下达。</p>
              </aside>
            )}

            <div ref={narrativeEndRef} />
          </div>

          {awaitingNarrative && (
            <p className="scribe-status" role="status" aria-live="polite">
              史官执笔中……
            </p>
          )}
        </section>
      </div>

      <div className="command-stack">
        <ActionMenu
          items={menuItems}
          loading={menuLoading}
          disabled={inputDisabled}
          command={command}
          selectionResetKey={menuSelectionResetKey}
          onCompose={(text) => setCommand(text)}
        />
        <form className="command-bar" onSubmit={submitAction}>
          <label className="sr-only" htmlFor="command">
            政令
          </label>
          <textarea
            id="command"
            name="command"
            ref={commandInputRef}
            className="command-input"
            rows={1}
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (!submitDisabled) {
                  event.currentTarget.form?.requestSubmit();
                }
              }
            }}
            placeholder="可勾选多项政令，或直接输入……（Enter 提交，Shift+Enter 换行）"
            disabled={inputDisabled}
            autoComplete="off"
            wrap="soft"
          />
          <button
            type="submit"
            className="btn-primary command-submit"
            disabled={submitDisabled}
          >
            {submitting ? "执行中" : "执行"}
          </button>
        </form>
      </div>

      <SaveLoadModal
        open={saveModalOpen}
        mode={saveModalMode}
        saves={saves}
        loading={saveBusy}
        message={saveMessage}
        onClose={() => setSaveModalOpen(false)}
        onConfirmSave={() => void confirmSave()}
        onLoad={(saveId) => void loadSave(saveId)}
        onDelete={(saveId) => deleteSave(saveId)}
      />

      {gameOver && gameOverReport && (
        <GameOverOverlay
          report={gameOverReport}
          onLoadLatest={() => void loadLatestAutosave()}
          onNewGame={() => openTemplateSelect("playing")}
        />
      )}
    </main>
  );
}

-- CivSim v2 初始 Schema（设计文档 §10.3）
-- 六张表：games / game_states / turns / summaries / landmarks / accumulations

-- 游戏实例
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    civ_name TEXT,
    template_id TEXT,
    status TEXT DEFAULT 'active'  -- active / game_over
);

-- 当前状态（每局一行，频繁更新）
CREATE TABLE IF NOT EXISTS game_states (
    game_id UUID PRIMARY KEY REFERENCES games(id),
    turn INTEGER,
    year DOUBLE PRECISION,
    state JSONB  -- 完整的 CivState 结构
);

-- 每轮记录（追加）
CREATE TABLE IF NOT EXISTS turns (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    year_start DOUBLE PRECISION,
    year_end DOUBLE PRECISION,
    player_input TEXT,
    llm_intent JSONB,           -- LLM①输出
    action_result JSONB,        -- 数学引擎输出
    narrative TEXT,             -- LLM②输出
    summary TEXT,               -- 一句话摘要
    state_before JSONB,         -- 行动前状态快照
    state_after JSONB,          -- 行动后状态快照
    domain_tags TEXT[],         -- 行动领域标签
    created_at TIMESTAMP
);

-- 中期摘要
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn_start INTEGER,
    turn_end INTEGER,
    year_start DOUBLE PRECISION,
    year_end DOUBLE PRECISION,
    content TEXT,               -- 摘要文本
    domain_frequencies JSONB,   -- 各领域行动频次
    created_at TIMESTAMP
);

-- 长期关键事件索引
CREATE TABLE IF NOT EXISTS landmarks (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    year DOUBLE PRECISION,
    tags TEXT[],                -- 主题标签（可用 GIN 索引）
    title TEXT,
    summary TEXT,
    state_snapshot JSONB,
    created_at TIMESTAMP
);

-- 积累值时间序列
CREATE TABLE IF NOT EXISTS accumulations (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    values JSONB,              -- {academic, military, commercial, administrative, cultural}
    created_at TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_turns_game_turn ON turns(game_id, turn DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_game ON summaries(game_id, turn_end DESC);
-- 文档写 USING GIN(game_id, tags)；UUID 非 GIN 原生类型，拆为 B-tree + GIN(tags)
CREATE INDEX IF NOT EXISTS idx_landmarks_game ON landmarks(game_id);
CREATE INDEX IF NOT EXISTS idx_landmarks_tags ON landmarks USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_accumulations_game ON accumulations(game_id, turn DESC);

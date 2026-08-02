-- Phase 3：landmarks 预留向量字段（当前不生成 embedding）
ALTER TABLE landmarks
    ADD COLUMN IF NOT EXISTS embedding REAL[],
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS importance_score INTEGER DEFAULT 1;

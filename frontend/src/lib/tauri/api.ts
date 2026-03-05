// Tauri API 调用封装 (带错误处理和重试)

import { invoke } from '@tauri-apps/api/core';

export interface TurnResult {
  narrative: string;
  summary: string;
  new_state: CivState;
  turn: number;
}

export interface CivState {
  year: number;
  civ_name: string;
  population: number;
  stability: number;
  authority: number;
  centralization: number;
  territory_size: number;
  tech_level: number;
  biome_fertility: number;
}

export interface SaveMetadata {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Era {
  id: string;
  year: number;
  display_name_zh: string;
  display_name_en: string;
  description_zh: string;
  description_en: string;
}

export interface Location {
  id: string;
  display_name_zh: string;
  display_name_en: string;
  biome_fertility: number;
}

export interface CivTemplate {
  era_id: string;
  location_id: string;
  civ_name_zh: string;
  civ_name_en: string;
  initial_state: any;
}

export interface GeneratedCivData {
  civ_name: string;
  historical_context: string;
  initial_state: any;
  plausibility_score: number;
}

export class APIError extends Error {
  constructor(
    message: string,
    public code: string = 'UNKNOWN',
    public retryable: boolean = false
  ) {
    super(message);
    this.name = 'APIError';
  }
}

const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

async function invokeWithRetry<T>(
  command: string,
  args: Record<string, unknown> = {},
  retries = 0
): Promise<T> {
  try {
    return await invoke<T>(command, args);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    const isRetryable = errorMsg.includes('network') || errorMsg.includes('timeout') || errorMsg.includes('connection');
    
    if (isRetryable && retries < MAX_RETRIES) {
      console.warn(`API call failed, retrying (${retries + 1}/${MAX_RETRIES})...`);
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (retries + 1)));
      return invokeWithRetry<T>(command, args, retries + 1);
    }
    
    throw new APIError(`命令 "${command}" 执行失败：${errorMsg}`, 'API_ERROR', isRetryable);
  }
}

export async function processPlayerInput(input: string): Promise<TurnResult> {
  if (!input || input.trim().length === 0) {
    throw new APIError('指令不能为空', 'VALIDATION_ERROR', false);
  }
  if (input.trim().length > 1000) {
    throw new APIError('指令过长 (最大 1000 字符)', 'VALIDATION_ERROR', false);
  }
  return invokeWithRetry<TurnResult>('process_player_input', { input });
}

export async function getCurrentState(): Promise<CivState> {
  return invokeWithRetry<CivState>('get_current_state');
}

export async function saveGame(name: string): Promise<number> {
  if (!name || name.trim().length === 0) {
    throw new APIError('存档名称不能为空', 'VALIDATION_ERROR', false);
  }
  if (name.trim().length > 100) {
    throw new APIError('存档名称过长 (最大 100 字符)', 'VALIDATION_ERROR', false);
  }
  return invokeWithRetry<number>('save_game', { name });
}

export async function overwriteSave(name: string, id: number): Promise<void> {
  if (!name || name.trim().length === 0) {
    throw new APIError('存档名称不能为空', 'VALIDATION_ERROR', false);
  }
  return invokeWithRetry<void>('overwrite_save', { name, id });
}

export async function loadGame(id: number): Promise<CivState> {
  return invokeWithRetry<CivState>('load_game', { id });
}

export async function listSaves(): Promise<SaveMetadata[]> {
  return invokeWithRetry<SaveMetadata[]>('list_saves');
}

export async function deleteSave(id: number): Promise<void> {
  return invokeWithRetry<void>('delete_save', { id });
}

// Civilization Selection API
export async function listEras(): Promise<Era[]> {
  return invokeWithRetry<Era[]>('list_eras');
}

export async function listLocations(): Promise<Location[]> {
  return invokeWithRetry<Location[]>('list_locations');
}

export async function hasCivTemplate(eraId: string, locationId: string): Promise<boolean> {
  return invokeWithRetry<boolean>('has_civ_template', { eraId, locationId });
}

export async function getCivTemplate(
  eraId: string, 
  locationId: string,
  lang: string
): Promise<CivTemplate | null> {
  return invokeWithRetry<CivTemplate | null>('get_civ_template', { eraId, locationId, lang });
}

export async function generateCivData(
  eraId: string,
  locationId: string
): Promise<GeneratedCivData> {
  return invokeWithRetry<GeneratedCivData>('generate_civilization', { eraId, locationId });
}

export async function startNewGameFromTemplate(
  eraId: string,
  locationId: string,
  lang: string
): Promise<CivState> {
  return invokeWithRetry<CivState>('start_new_game_from_template', { eraId, locationId, lang });
}

export async function startNewGameFromGenerated(
  generated: GeneratedCivData,
  year: number,
  lang: string
): Promise<CivState> {
  return invokeWithRetry<CivState>('start_new_game_from_generated', { generated, year, lang });
}

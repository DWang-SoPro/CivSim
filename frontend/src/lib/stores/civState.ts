import { writable, derived } from 'svelte/store';
import { resetGameLog } from './gameLog.js';

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
  political_system?: string;
  economic_system?: string;
}

export interface StateChange {
  population: number;
  stability: number;
  authority: number;
  centralization: number;
  territory_size: number;
  tech_level: number;
}

const initialState: CivState = {
  year: -2000,
  civ_name: 'Harappan League',
  population: 50000,
  stability: 82,
  authority: 3,
  centralization: 35,
  territory_size: 1200,
  tech_level: 1.0,
  biome_fertility: 0.6,
  political_system: '封建制',
  economic_system: '自然经济',
};

// 主状态存储
export const civState = writable<CivState>(initialState);

// 前一回合状态存储（用于计算变化量）
export const previousCivState = writable<CivState | null>(null);

// 状态变化量存储
export const stateChanges = derived(
  [civState, previousCivState],
  ([$civState, $previousCivState]): StateChange | null => {
    if (!$previousCivState) return null;
    return {
      population: $civState.population - $previousCivState.population,
      stability: $civState.stability - $previousCivState.stability,
      authority: $civState.authority - $previousCivState.authority,
      centralization: $civState.centralization - $previousCivState.centralization,
      territory_size: $civState.territory_size - $previousCivState.territory_size,
      tech_level: $civState.tech_level - $previousCivState.tech_level,
    };
  }
);

export function setCivState(state: CivState) {
  // Reset game log when setting new state (new game)
  resetGameLog();
  previousCivState.set(null);
  civState.set(state);
}

export function updateCivState(newState: CivState) {
  // 保存当前状态为前一回合状态
  civState.update(current => {
    previousCivState.set(current);
    return newState;
  });
}

import { writable } from 'svelte/store';
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
};

export const civState = writable<CivState>(initialState);

export function setCivState(state: CivState) {
  // Reset game log when setting new state (new game)
  resetGameLog();
  civState.set(state);
}

export function updateCivState(newState: CivState) {
  // Replace entire state with new state from server
  civState.set(newState);
}

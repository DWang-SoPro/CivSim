import { writable } from 'svelte/store';

export type GamePhase = 
  | 'select'
  | 'era'
  | 'location'
  | 'confirm'
  | 'load'
  | 'playing';

export interface NewGameSelection {
  eraId: string | null;
  locationId: string | null;
  template: any | null;
  generated: any | null;
}

export const gamePhase = writable<GamePhase>('select');

export const selection = writable<NewGameSelection>({
  eraId: null,
  locationId: null,
  template: null,
  generated: null,
});

// Subscribe to changes for debugging
gamePhase.subscribe(phase => {
  console.log('>>> gamePhase SUBSCRIBED:', phase);
});

selection.subscribe(sel => {
  console.log('>>> selection SUBSCRIBED:', sel);
});

export function setPhase(phase: GamePhase) {
  console.log('>>> setPhase CALLED with:', phase);
  gamePhase.set(phase);
}

export function resetSelection() {
  selection.set({
    eraId: null,
    locationId: null,
    template: null,
    generated: null,
  });
}

export function selectEra(eraId: string) {
  console.log('>>> selectEra CALLED with:', eraId);
  selection.update(s => { 
    const newVal = { ...s, eraId };
    console.log('>>> selection updated to:', newVal);
    return newVal;
  });
}

export function selectLocation(locationId: string) {
  console.log('>>> selectLocation CALLED with:', locationId);
  selection.update(s => ({ ...s, locationId }));
}

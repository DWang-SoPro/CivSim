import { writable } from 'svelte/store';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

function createToastStore() {
  const { subscribe, update } = writable<ToastMessage[]>([]);
  
  function addToast(
    message: string,
    type: 'success' | 'error' | 'warning' | 'info' = 'info',
    duration: number = 3000
  ) {
    const id = Date.now().toString();
    update(toasts => [...toasts, { id, message, type, duration }]);
    return id;
  }
  
  function removeToast(id: string) {
    update(toasts => toasts.filter(t => t.id !== id));
  }
  
  function success(message: string, duration?: number) {
    return addToast(message, 'success', duration);
  }
  
  function error(message: string, duration?: number) {
    return addToast(message, 'error', duration);
  }
  
  function warning(message: string, duration?: number) {
    return addToast(message, 'warning', duration);
  }
  
  function info(message: string, duration?: number) {
    return addToast(message, 'info', duration);
  }
  
  return {
    subscribe,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };
}

export const toast = createToastStore();

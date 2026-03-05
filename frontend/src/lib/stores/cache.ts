// 前端数据缓存

interface CacheEntry<T> {
  value: T;
  timestamp: number;
  ttl: number;
}

class DataCache {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private defaultTTL: number;

  constructor(ttlSeconds: number = 300) {
    this.defaultTTL = ttlSeconds * 1000;
  }

  set<T>(key: string, value: T, ttl?: number): void {
    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      ttl: ttl || this.defaultTTL,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }
    
    const now = Date.now();
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.value as T;
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  // 获取缓存统计
  getStats(): { size: number; keys: string[] } {
    const now = Date.now();
    const validKeys: string[] = [];
    
    this.cache.forEach((entry, key) => {
      if (now - entry.timestamp <= entry.ttl) {
        validKeys.push(key);
      } else {
        this.cache.delete(key);
      }
    });
    
    return {
      size: validKeys.length,
      keys: validKeys,
    };
  }
}

// 全局缓存实例
export const cache = new DataCache(300); // 5 分钟 TTL

// Agent 缓存系统 - 减少重复 API 调用

use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

use crate::schemas::{DeconstructorOutput, AuditorOutput, SimulatorOutput, ChroniclerOutput};

/// 缓存条目
#[derive(Clone)]
struct CacheEntry<T> {
    value: T,
    expires_at: Instant,
}

/// 结果缓存
pub struct ResultCache {
    deconstructor: RwLock<HashMap<String, CacheEntry<DeconstructorOutput>>>,
    auditor: RwLock<HashMap<String, CacheEntry<AuditorOutput>>>,
    simulator: RwLock<HashMap<String, CacheEntry<SimulatorOutput>>>,
    chronicler: RwLock<HashMap<String, CacheEntry<ChroniclerOutput>>>,
    ttl: Duration,
}

impl ResultCache {
    pub fn new(ttl_secs: u64) -> Self {
        Self {
            deconstructor: RwLock::new(HashMap::new()),
            auditor: RwLock::new(HashMap::new()),
            simulator: RwLock::new(HashMap::new()),
            chronicler: RwLock::new(HashMap::new()),
            ttl: Duration::from_secs(ttl_secs),
        }
    }
    
    /// 获取或设置 Deconstructor 缓存
    pub async fn get_or_set_deconstructor<F, Fut>(
        &self,
        key: &str,
        fetch: F,
    ) -> Result<DeconstructorOutput, Box<dyn std::error::Error + Send + Sync>>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<DeconstructorOutput, Box<dyn std::error::Error + Send + Sync>>>,
    {
        self.get_or_set(&self.deconstructor, key, fetch).await
    }
    
    /// 通用获取或设置方法
    async fn get_or_set<T: Clone, F, Fut>(
        &self,
        cache: &RwLock<HashMap<String, CacheEntry<T>>>,
        key: &str,
        fetch: F,
    ) -> Result<T, Box<dyn std::error::Error + Send + Sync>>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, Box<dyn std::error::Error + Send + Sync>>>,
    {
        // 尝试从缓存获取
        {
            let read_cache = cache.read().await;
            if let Some(entry) = read_cache.get(key) {
                if Instant::now() < entry.expires_at {
                    return Ok(entry.value.clone());
                }
            }
        }
        
        // 缓存未命中或过期，执行实际调用
        let value = fetch().await?;
        
        // 设置缓存
        {
            let mut write_cache = cache.write().await;
            write_cache.insert(
                key.to_string(),
                CacheEntry {
                    value: value.clone(),
                    expires_at: Instant::now() + self.ttl,
                },
            );
        }
        
        Ok(value)
    }
    
    /// 清理过期缓存
    pub async fn cleanup(&self) {
        let now = Instant::now();
        
        let mut decon = self.deconstructor.write().await;
        decon.retain(|_, entry| now < entry.expires_at);
        
        let mut aud = self.auditor.write().await;
        aud.retain(|_, entry| now < entry.expires_at);
        
        let mut sim = self.simulator.write().await;
        sim.retain(|_, entry| now < entry.expires_at);
        
        let mut chron = self.chronicler.write().await;
        chron.retain(|_, entry| now < entry.expires_at);
    }
}

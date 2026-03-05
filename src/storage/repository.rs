use chrono::NaiveDateTime;
use rusqlite::Connection;
use rusqlite::Result;

pub struct Storage {
    conn: Connection,
}

#[derive(Debug, Clone)]
pub struct SaveMetadata {
    pub id: i64,
    pub name: String,
    pub created_at: NaiveDateTime,
    pub updated_at: NaiveDateTime,
}

impl Storage {
    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        Ok(Storage { conn })
    }

    pub fn init_schema(&self) -> Result<()> {
        self.conn
            .execute_batch(crate::storage::schema::SCHEMA_SQL)?;
        self.migrate()?;
        Ok(())
    }

    fn migrate(&self) -> Result<()> {
        let mut stmt = self.conn.prepare("PRAGMA table_info(saves)")?;
        let columns: Vec<String> = stmt
            .query_map([], |row| row.get::<_, String>(1))?
            .filter_map(|r| r.ok())
            .collect();

        if !columns.contains(&"updated_at".to_string()) {
            self.conn.execute(
                "ALTER TABLE saves ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
                [],
            )?;
            eprintln!("[MIGRATION] Added updated_at column to saves table");
        }

        if !columns.contains(&"conversation_history".to_string()) {
            self.conn.execute(
                "ALTER TABLE saves ADD COLUMN conversation_history TEXT DEFAULT '[]'",
                [],
            )?;
            eprintln!("[MIGRATION] Added conversation_history column to saves table");
        }

        Ok(())
    }

    pub fn save_game(
        &self,
        name: &str,
        state_json: &str,
        conversation_history: &str,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT INTO saves (name, state_json, conversation_history) VALUES (?1, ?2, ?3)",
            rusqlite::params![name, state_json, conversation_history],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn update_save(
        &self,
        id: i64,
        name: &str,
        state_json: &str,
        conversation_history: &str,
    ) -> Result<usize> {
        self.conn.execute(
            "UPDATE saves SET name = ?1, state_json = ?2, conversation_history = ?3, updated_at = CURRENT_TIMESTAMP WHERE id = ?4",
            rusqlite::params![name, state_json, conversation_history, id],
        )
    }

    pub fn load_game(&self, id: i64) -> Result<Option<(String, String)>> {
        let mut stmt = self
            .conn
            .prepare("SELECT state_json, conversation_history FROM saves WHERE id = ?1")?;
        let mut rows = stmt.query([id])?;
        if let Some(row) = rows.next()? {
            let state: String = row.get(0)?;
            let history: String = row.get(1)?;
            Ok(Some((state, history)))
        } else {
            Ok(None)
        }
    }

    pub fn list_saves(&self) -> Result<Vec<SaveMetadata>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, name, created_at, updated_at FROM saves ORDER BY updated_at DESC",
        )?;
        let mut rows = stmt.query([])?;
        let mut saves: Vec<SaveMetadata> = Vec::new();
        while let Some(row) = rows.next()? {
            let id: i64 = row.get(0)?;
            let name: String = row.get(1)?;
            let created_at_str: String = row.get(2)?;
            let updated_at_str: String = row.get(3)?;
            let created_at = parse_naive_datetime(&created_at_str);
            let updated_at = parse_naive_datetime(&updated_at_str);
            saves.push(SaveMetadata {
                id,
                name,
                created_at,
                updated_at,
            });
        }
        Ok(saves)
    }

    pub fn delete_save(&self, id: i64) -> Result<usize> {
        self.conn
            .execute("DELETE FROM saves WHERE id = ?1", rusqlite::params![id])
    }

    pub fn save_template(
        &self,
        era_id: &str,
        location_id: &str,
        template_json: &str,
    ) -> Result<i64> {
        self.conn.execute(
            "INSERT OR REPLACE INTO generated_templates (era_id, location_id, template_json) VALUES (?1, ?2, ?3)",
            rusqlite::params![era_id, location_id, template_json],
        )?;
        let mut stmt = self
            .conn
            .prepare("SELECT id FROM generated_templates WHERE era_id = ?1 AND location_id = ?2")?;
        let mut rows = stmt.query([era_id, location_id])?;
        if let Some(row) = rows.next()? {
            Ok(row.get(0)?)
        } else {
            Ok(0)
        }
    }

    pub fn load_template(&self, era_id: &str, location_id: &str) -> Result<Option<String>> {
        let mut stmt = self.conn.prepare(
            "SELECT template_json FROM generated_templates WHERE era_id = ?1 AND location_id = ?2",
        )?;
        let mut rows = stmt.query([era_id, location_id])?;
        if let Some(row) = rows.next()? {
            let s: String = row.get(0)?;
            Ok(Some(s))
        } else {
            Ok(None)
        }
    }
}

fn parse_naive_datetime(s: &str) -> NaiveDateTime {
    let mut date_part = "1970-01-01";
    let mut time_part = "00:00:00";
    if let Some(space_pos) = s.find(' ') {
        date_part = &s[..space_pos];
        time_part = &s[space_pos + 1..];
    } else if !s.is_empty() {
        date_part = s;
    }

    let date_vals: Vec<i32> = date_part
        .split('-')
        .filter_map(|p| p.parse::<i32>().ok())
        .collect();
    let time_vals: Vec<u32> = time_part
        .split(':')
        .filter_map(|p| p.parse::<u32>().ok())
        .collect();

    let year = *date_vals.get(0).unwrap_or(&1970) as i32;
    let month = *date_vals.get(1).unwrap_or(&1) as u32;
    let day = *date_vals.get(2).unwrap_or(&1) as u32;
    let hour = *time_vals.get(0).unwrap_or(&0);
    let minute = *time_vals.get(1).unwrap_or(&0);
    let second = *time_vals.get(2).unwrap_or(&0);

    chrono::NaiveDate::from_ymd_opt(year, month, day)
        .and_then(|d| d.and_hms_opt(hour, minute, second))
        .unwrap_or_else(|| {
            chrono::NaiveDate::from_ymd_opt(1970, 1, 1)
                .unwrap()
                .and_hms_opt(0, 0, 0)
                .unwrap()
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn storage_save_load_roundtrip() {
        let storage = Storage::new(":memory:").expect("new in-memory db");
        storage.init_schema().expect("init schema");
        let id = storage.save_game("test", "{\"a\":1}", "[]").expect("save");
        let loaded = storage.load_game(id).expect("load");
        assert_eq!(loaded.unwrap().0, "{\"a\":1}");
    }
}

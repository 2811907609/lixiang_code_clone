import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import duckdb


class RepoStatusManager:
    def __init__(self, db_path: str = "repo_status.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database and table structure"""
        # 创建序列
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS repo_status_id_seq START 1
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS repo_status (
                id INTEGER PRIMARY KEY DEFAULT nextval('repo_status_id_seq'),
                repo_name VARCHAR(255) NOT NULL,
                repo_url VARCHAR(500) NOT NULL,
                last_activity_at TIMESTAMP,
                next_collect_at TIMESTAMP DEFAULT NOW(),
                last_collected_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                branches_info JSON,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create unique index on repo_name to prevent duplicates
        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_repo_name_unique
            ON repo_status(repo_name)
        """)

    def add_repo(self, repo_name: str, repo_url: str, last_activity_at: Optional[str] = None) -> int:
        """Add new repository to status table"""
        result = self.conn.execute("""
            INSERT INTO repo_status (repo_name, repo_url, last_activity_at, last_collected_at)
            VALUES (?, ?, ?, '2000-01-01 00:00:00')
            RETURNING id
        """, (repo_name, repo_url, last_activity_at)).fetchone()
        return result[0] if result else None

    def get_pending_repos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of repositories pending collection, prioritizing by last collected time"""
        results = self.conn.execute("""
            SELECT * FROM repo_status
            WHERE status IN ('pending', 'failed')
            AND next_collect_at <= NOW()
            AND (last_activity_at IS NULL OR last_activity_at > last_collected_at)
            ORDER BY last_collected_at ASC, next_collect_at ASC
            LIMIT ?
        """, (limit,)).fetchall()

        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in results]

    def start_processing(self, repo_id: int) -> bool:
        """Mark repository as processing"""
        self.conn.execute("""
            UPDATE repo_status
            SET status = 'processing', updated_at = NOW()
            WHERE id = ?
        """, (repo_id,))
        return True

    def complete_processing(self, repo_id: int, branches_info: Dict[str, str] = None,
                          next_collect_hours: int = 72) -> bool:
        """Mark repository processing as completed"""
        branches_json = json.dumps(branches_info) if branches_info else None
        next_collect_at = datetime.now() + timedelta(hours=next_collect_hours)

        self.conn.execute("""
            UPDATE repo_status
            SET status = 'completed',
                last_collected_at = NOW(),
                next_collect_at = ?,
                branches_info = ?,
                retry_count = 0,
                error_message = NULL,
                updated_at = NOW()
            WHERE id = ?
        """, (next_collect_at, branches_json, repo_id))
        return True

    def fail_processing(self, repo_id: int, error_message: str,
                       retry_delay_hours: int = 1) -> bool:
        """Mark repository processing as failed"""
        next_collect_at = datetime.now() + timedelta(hours=retry_delay_hours)

        self.conn.execute("""
            UPDATE repo_status
            SET status = 'failed',
                error_message = ?,
                retry_count = retry_count + 1,
                next_collect_at = ?,
                updated_at = NOW()
            WHERE id = ?
        """, (error_message, next_collect_at, repo_id))
        return True

    def get_repo_status(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository status"""
        result = self.conn.execute("""
            SELECT * FROM repo_status WHERE repo_name = ?
        """, (repo_name,)).fetchone()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None

    def reset_stuck_repos(self, hours_threshold: int = 2) -> int:
        """Reset repositories stuck in processing status"""
        result = self.conn.execute("""
            UPDATE repo_status
            SET status = 'pending',
                next_collect_at = NOW(),
                updated_at = NOW()
            WHERE status = 'processing'
            AND updated_at < NOW() - INTERVAL (? || ' HOUR')::INTERVAL
            RETURNING id
        """, (hours_threshold,)).fetchall()
        return len(result)

    def reset_all_repos(self) -> int:
        """Reset all repositories to pending status for re-scraping"""
        result = self.conn.execute("""
            UPDATE repo_status
            SET status = 'pending',
                next_collect_at = NOW(),
                last_collected_at = '2000-01-01 00:00:00',
                retry_count = 0,
                error_message = NULL,
                updated_at = NOW()
            RETURNING id
        """).fetchall()
        return len(result)

    def get_stats(self) -> Dict[str, int]:
        """Get statistics"""
        result = self.conn.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM repo_status
            GROUP BY status
        """).fetchall()

        stats = dict(result)
        return {
            'total': sum(stats.values()),
            'pending': stats.get('pending', 0),
            'processing': stats.get('processing', 0),
            'completed': stats.get('completed', 0),
            'failed': stats.get('failed', 0)
        }

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute_sql(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute arbitrary SQL query and return results as list of dictionaries.

        Args:
            sql: SQL query to execute
            params: Optional parameters for the query

        Returns:
            List of dictionaries with column names as keys
        """
        if params:
            result = self.conn.execute(sql, params).fetchall()
        else:
            result = self.conn.execute(sql).fetchall()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return [dict(zip(columns, row)) for row in result]
        return []


def get_db_helper(db_path: str = None):
    """Get a database helper for interactive use in Jupyter/IPython.

    Usage:
        db = get_db_helper()
        results = db.execute_sql("SELECT * FROM repo_status LIMIT 5")

    Args:
        db_path: Database path (uses default if not provided)

    Returns:
        RepoStatusManager instance for interactive SQL execution
    """
    from data_scrap.config import config
    db_path = db_path or config.REPO_DB_PATH or "repo_status.duckdb"
    return RepoStatusManager(db_path)

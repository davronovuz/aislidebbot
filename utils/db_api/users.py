from .database import Database
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pytz

TASHKENT_TZ = pytz.timezone('Asia/Tashkent')

class UserDatabase(Database):
    def create_table_users(self):
        """Foydalanuvchilar jadvali"""
        sql_users = """
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(255) NULL,
            ALTER TABLE Users ADD COLUMN free_presentations INTEGER DEFAULT 0;
            balance DECIMAL(10, 2) DEFAULT 0.00,
            total_spent DECIMAL(10, 2) DEFAULT 0.00,
            total_deposited DECIMAL(10, 2) DEFAULT 0.00,
            last_active DATETIME NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_blocked BOOLEAN DEFAULT FALSE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql_users, commit=True)

        sql_admins = """
        CREATE TABLE IF NOT EXISTS Admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            is_super_admin BOOLEAN DEFAULT FALSE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        );
        """
        self.execute(sql_admins, commit=True)

    def create_table_transactions(self):
        """Tranzaksiyalar jadvali"""
        sql = """
        CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            balance_before DECIMAL(10, 2) NOT NULL,
            balance_after DECIMAL(10, 2) NOT NULL,
            description TEXT NULL,
            receipt_file_id TEXT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            admin_id INTEGER NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NULL,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES Users(id) ON DELETE SET NULL
        );
        """
        self.execute(sql, commit=True)
        self.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON Transactions(user_id);", commit=True)
        self.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON Transactions(status);", commit=True)



    def create_table_pricing(self):
        """Narxlar jadvali"""
        sql = """
        CREATE TABLE IF NOT EXISTS Pricing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type VARCHAR(100) NOT NULL UNIQUE,
            price DECIMAL(10, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT "so'm",
            description TEXT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            updated_by INTEGER NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NULL,
            FOREIGN KEY (updated_by) REFERENCES Users(id) ON DELETE SET NULL
        );
        """
        self.execute(sql, commit=True)

        default_prices = [
            ('slide_basic', 1000.00, "so'm", 'Oddiy slayd', True),
            ('slide_pro', 2000.00, "so'm", 'Professional slayd', True),
            ('presentation_basic', 10000.00, "so'm", 'Oddiy prezentatsiya (10 slayd)', True),
            ('presentation_pro', 20000.00, "so'm", 'Professional prezentatsiya (10 slayd)', True),
        ]

        for service, price, currency, desc, active in default_prices:
            self.execute("""
                INSERT OR IGNORE INTO Pricing (service_type, price, currency, description, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, parameters=(service, price, currency, desc, active), commit=True)

    def create_table_presentation_tasks(self):
        """Prezentatsiya task'lari"""
        sql = """
        CREATE TABLE IF NOT EXISTS PresentationTasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_uuid VARCHAR(100) NOT NULL UNIQUE,
            presentation_type VARCHAR(50) NOT NULL,
            slide_count INTEGER DEFAULT 10,
            answers TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            file_path TEXT NULL,
            error_message TEXT NULL,
            amount_charged DECIMAL(10, 2) NULL,
            started_at DATETIME NULL,
            completed_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        );
        """
        self.execute(sql, commit=True)
        self.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON PresentationTasks(user_id);", commit=True)
        self.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON PresentationTasks(status);", commit=True)
        self.execute("CREATE INDEX IF NOT EXISTS idx_tasks_uuid ON PresentationTasks(task_uuid);", commit=True)

    # ==================== USER METHODLAR ====================

    # users_db.py ga qo'shish

    def create_business_plans_table(self):
        """Biznes planlar jadvali"""
        sql = """
        CREATE TABLE IF NOT EXISTS BusinessPlans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            file_id TEXT NOT NULL,  -- Telegram file_id
            preview_image_id TEXT,  -- Preview rasm
            category TEXT,
            sold_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql, commit=True)

        # Sotib olish tarixi
        sql_purchases = """
        CREATE TABLE IF NOT EXISTS PlanPurchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id),
            FOREIGN KEY (plan_id) REFERENCES BusinessPlans(id)
        );
        """
        self.execute(sql_purchases, commit=True)




    def user_exists(self, telegram_id: int) -> bool:
        sql = "SELECT 1 FROM Users WHERE telegram_id = ?"
        result = self.execute(sql, parameters=(telegram_id,), fetchone=True)
        return result is not None

    def add_user(self, telegram_id: int, username: str, created_at=None):
        if not self.user_exists(telegram_id):
            sql = "INSERT INTO Users (telegram_id, username,free_presentations, created_at) VALUES (?, ?, 0, ?)"
            if created_at is None:
                created_at = datetime.now().isoformat()
            self.execute(sql, parameters=(telegram_id, username, created_at), commit=True)

    def get_user_id(self, telegram_id: int) -> Optional[int]:
        sql = "SELECT id FROM Users WHERE telegram_id = ?"
        result = self.execute(sql, parameters=(telegram_id,), fetchone=True)
        return result[0] if result else None

    def get_user_balance(self, telegram_id: int) -> float:
        sql = "SELECT balance FROM Users WHERE telegram_id = ?"
        result = self.execute(sql, parameters=(telegram_id,), fetchone=True)
        return float(result[0]) if result else 0.0

    def add_to_balance(self, telegram_id: int, amount: float) -> bool:
        try:
            sql = """
            UPDATE Users SET balance = balance + ?, total_deposited = total_deposited + ?
            WHERE telegram_id = ?
            """
            self.execute(sql, parameters=(amount, amount, telegram_id), commit=True)
            return True
        except Exception as e:
            print(f"❌ Balansga qo'shishda xato: {e}")
            return False

    def deduct_from_balance(self, telegram_id: int, amount: float) -> bool:
        try:
            current_balance = self.get_user_balance(telegram_id)
            if current_balance < amount:
                return False
            sql = """
            UPDATE Users SET balance = balance - ?, total_spent = total_spent + ?
            WHERE telegram_id = ? AND balance >= ?
            """
            self.execute(sql, parameters=(amount, amount, telegram_id, amount), commit=True)
            return True
        except Exception as e:
            print(f"❌ Balansdan yechishda xato: {e}")
            return False

    def get_user_stats(self, telegram_id: int) -> Optional[Dict]:
        sql = "SELECT balance, total_spent, total_deposited, created_at FROM Users WHERE telegram_id = ?"
        result = self.execute(sql, parameters=(telegram_id,), fetchone=True)
        if result:
            return {
                'balance': float(result[0]),
                'total_spent': float(result[1]),
                'total_deposited': float(result[2]),
                'member_since': result[3]
            }
        return None

    # ==================== TRANSACTION METHODLAR ====================

    def create_transaction(
            self,
            telegram_id: int,
            transaction_type: str,
            amount: float,
            description: str = None,
            receipt_file_id: str = None,
            status: str = 'pending'
    ) -> Optional[int]:
        """
        Yangi tranzaksiya yaratish

        ✅ TO'G'IRLANGAN - TO'G'RI ID QAYTARADI
        """
        try:
            user_id = self.get_user_id(telegram_id)
            if not user_id:
                print(f"❌ User topilmadi: telegram_id={telegram_id}")
                return None

            balance_before = self.get_user_balance(telegram_id)

            sql = """
            INSERT INTO Transactions (
                user_id, transaction_type, amount, 
                balance_before, balance_after, 
                description, receipt_file_id, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            self.execute(
                sql,
                parameters=(
                    user_id, transaction_type, amount,
                    balance_before, balance_before,
                    description, receipt_file_id, status
                ),
                commit=True
            )

            # ✅ TO'G'IRLANGAN: Oxirgi kiritilgan ID ni olish
            result = self.execute(
                "SELECT id FROM Transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                parameters=(user_id,),
                fetchone=True
            )

            if result:
                trans_id = result[0]
                print(f"✅ Tranzaksiya yaratildi: ID={trans_id}")
                return trans_id

            return None

        except Exception as e:
            print(f"❌ Tranzaksiya yaratishda xato: {e}")
            return None

    def get_transaction_by_id(self, trans_id: int) -> Optional[Dict]:
        """Tranzaksiyani ID bo'yicha olish"""
        try:
            sql = """
            SELECT 
                t.id, t.user_id, t.transaction_type, t.amount,
                t.description, t.receipt_file_id, t.status,
                t.admin_id, t.created_at, t.updated_at, u.telegram_id
            FROM Transactions t
            JOIN Users u ON t.user_id = u.id
            WHERE t.id = ?
            """
            result = self.execute(sql, parameters=(trans_id,), fetchone=True)

            if result:
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'type': result[2],
                    'amount': float(result[3]),
                    'description': result[4],
                    'receipt_file_id': result[5],
                    'status': result[6],
                    'admin_id': result[7],
                    'created_at': result[8],
                    'updated_at': result[9],
                    'telegram_id': result[10]
                }
            return None

        except Exception as e:
            print(f"❌ get_transaction_by_id xato: {e}")
            return None

    def update_transaction_status(self, trans_id: int, status: str, admin_id: int = None) -> bool:
        try:
            sql = "UPDATE Transactions SET status = ?, admin_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.execute(sql, parameters=(status, admin_id, trans_id), commit=True)
            return True
        except Exception as e:
            print(f"❌ update_transaction_status xato: {e}")
            return False

    def approve_transaction(self, transaction_id: int, admin_telegram_id: int) -> bool:
        """Tranzaksiyani tasdiqlash va balansni yangilash"""
        try:
            trans = self.get_transaction_by_id(transaction_id)
            if not trans:
                return False

            if trans['status'] != 'pending':
                return False

            # Balansni yangilash
            if trans['type'] == 'deposit':
                self.add_to_balance(trans['telegram_id'], trans['amount'])

            # Status yangilash
            balance_after = self.get_user_balance(trans['telegram_id'])
            admin_id = self.get_user_id(admin_telegram_id)

            sql = """
            UPDATE Transactions SET status = 'approved', balance_after = ?, admin_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            self.execute(sql, parameters=(balance_after, admin_id, transaction_id), commit=True)
            return True

        except Exception as e:
            print(f"❌ Tranzaksiyani tasdiqlashda xato: {e}")
            return False

    def reject_transaction(self, transaction_id: int, admin_telegram_id: int = None) -> bool:
        try:
            admin_id = self.get_user_id(admin_telegram_id) if admin_telegram_id else None
            sql = "UPDATE Transactions SET status = 'rejected', admin_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pending'"
            self.execute(sql, parameters=(admin_id, transaction_id), commit=True)
            return True
        except Exception as e:
            print(f"❌ Tranzaksiyani rad etishda xato: {e}")
            return False

    def get_pending_transactions(self) -> List[Dict]:
        sql = """
        SELECT t.id, u.telegram_id, u.username, t.transaction_type, 
               t.amount, t.description, t.receipt_file_id, t.created_at
        FROM Transactions t
        JOIN Users u ON t.user_id = u.id
        WHERE t.status = 'pending'
        ORDER BY t.created_at DESC
        """
        results = self.execute(sql, fetchall=True)
        transactions = []
        for row in results:
            transactions.append({
                'id': row[0],
                'telegram_id': row[1],
                'username': row[2],
                'type': row[3],
                'amount': float(row[4]),
                'description': row[5],
                'receipt_file_id': row[6],
                'created_at': row[7]
            })
        return transactions

    def get_user_transactions(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        sql = """
        SELECT id, transaction_type, amount, balance_before, balance_after, description, status, created_at
        FROM Transactions
        WHERE user_id = (SELECT id FROM Users WHERE telegram_id = ?)
        ORDER BY created_at DESC LIMIT ?
        """
        results = self.execute(sql, parameters=(telegram_id, limit), fetchall=True)
        transactions = []
        for row in results:
            transactions.append({
                'id': row[0],
                'type': row[1],
                'amount': float(row[2]),
                'balance_before': float(row[3]),
                'balance_after': float(row[4]),
                'description': row[5],
                'status': row[6],
                'created_at': row[7]
            })
        return transactions

    # ==================== PRICING METHODLAR ====================

    def get_price(self, service_type: str) -> Optional[float]:
        sql = "SELECT price FROM Pricing WHERE service_type = ? AND is_active = TRUE"
        result = self.execute(sql, parameters=(service_type,), fetchone=True)
        return float(result[0]) if result else None

    def update_price(self, service_type: str, new_price: float, admin_telegram_id: int) -> bool:
        try:
            admin_id = self.get_user_id(admin_telegram_id)
            sql = "UPDATE Pricing SET price = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE service_type = ?"
            self.execute(sql, parameters=(new_price, admin_id, service_type), commit=True)
            return True
        except Exception as e:
            print(f"❌ Narxni yangilashda xato: {e}")
            return False

    def get_all_prices(self) -> List[Dict]:
        sql = "SELECT service_type, price, currency, description, is_active FROM Pricing ORDER BY service_type"
        results = self.execute(sql, fetchall=True)
        prices = []
        for row in results:
            prices.append({
                'service_type': row[0],
                'price': float(row[1]),
                'currency': row[2],
                'description': row[3],
                'is_active': bool(row[4])
            })
        return prices

    # ==================== PRESENTATION TASK METHODLAR ====================

    def create_presentation_task(
            self, telegram_id: int, task_uuid: str, presentation_type: str,
            slide_count: int, answers: str, amount_charged: float
    ) -> Optional[int]:
        try:
            user_id = self.get_user_id(telegram_id)
            if not user_id:
                return None

            sql = """
            INSERT INTO PresentationTasks (user_id, task_uuid, presentation_type, slide_count, answers, amount_charged)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            self.execute(sql, parameters=(user_id, task_uuid, presentation_type, slide_count, answers, amount_charged),
                         commit=True)

            result = self.execute("SELECT id FROM PresentationTasks WHERE task_uuid = ?", parameters=(task_uuid,),
                                  fetchone=True)
            return result[0] if result else None

        except Exception as e:
            print(f"❌ Task yaratishda xato: {e}")
            return None

    def update_task_status(self, task_uuid: str, status: str, progress: int = None, file_path: str = None,
                           error_message: str = None) -> bool:
        try:
            updates = ["status = ?"]
            parameters = [status]

            if progress is not None:
                updates.append("progress = ?")
                parameters.append(progress)
            if file_path:
                updates.append("file_path = ?")
                parameters.append(file_path)
            if error_message:
                updates.append("error_message = ?")
                parameters.append(error_message)
            if status == 'processing':
                updates.append("started_at = CURRENT_TIMESTAMP")
            if status in ['completed', 'failed']:
                updates.append("completed_at = CURRENT_TIMESTAMP")

            parameters.append(task_uuid)
            sql = f"UPDATE PresentationTasks SET {', '.join(updates)} WHERE task_uuid = ?"
            self.execute(sql, parameters=tuple(parameters), commit=True)
            return True

        except Exception as e:
            print(f"❌ Task statusini yangilashda xato: {e}")
            return False

    def get_task_by_uuid(self, task_uuid: str) -> Optional[Dict]:
        sql = """
        SELECT id, user_id, task_uuid, presentation_type, slide_count, answers, status, progress, 
               file_path, error_message, amount_charged, started_at, completed_at, created_at
        FROM PresentationTasks WHERE task_uuid = ?
        """
        result = self.execute(sql, parameters=(task_uuid,), fetchone=True)
        if result:
            return {
                'id': result[0], 'user_id': result[1], 'task_uuid': result[2],
                'presentation_type': result[3], 'slide_count': result[4], 'answers': result[5],
                'status': result[6], 'progress': result[7], 'file_path': result[8],
                'error_message': result[9], 'amount_charged': float(result[10]) if result[10] else 0.0,
                'started_at': result[11], 'completed_at': result[12], 'created_at': result[13]
            }
        return None

    def get_user_tasks(self, telegram_id: int, limit: int = 5) -> List[Dict]:
        sql = """
        SELECT task_uuid, presentation_type, slide_count, status, progress, file_path, amount_charged, created_at
        FROM PresentationTasks
        WHERE user_id = (SELECT id FROM Users WHERE telegram_id = ?)
        ORDER BY created_at DESC LIMIT ?
        """
        results = self.execute(sql, parameters=(telegram_id, limit), fetchall=True)
        tasks = []
        for row in results:
            tasks.append({
                'task_uuid': row[0], 'type': row[1], 'slide_count': row[2],
                'status': row[3], 'progress': row[4], 'file_path': row[5],
                'amount_charged': float(row[6]) if row[6] else 0.0, 'created_at': row[7]
            })
        return tasks

    def get_pending_tasks(self) -> List[Dict]:
        sql = "SELECT task_uuid, user_id, presentation_type, slide_count, answers, created_at FROM PresentationTasks WHERE status = 'pending' ORDER BY created_at ASC"
        results = self.execute(sql, fetchall=True)
        tasks = []
        for row in results:
            tasks.append(
                {'task_uuid': row[0], 'user_id': row[1], 'type': row[2], 'slide_count': row[3], 'answers': row[4],
                 'created_at': row[5]})
        return tasks

    # ==================== STATISTIKA ====================

    def get_financial_stats(self) -> Dict:
        total_balance = self.execute("SELECT SUM(balance) FROM Users", fetchone=True)[0] or 0
        total_deposited = self.execute("SELECT SUM(total_deposited) FROM Users", fetchone=True)[0] or 0
        total_spent = self.execute("SELECT SUM(total_spent) FROM Users", fetchone=True)[0] or 0
        pending_deposits = \
        self.execute("SELECT SUM(amount) FROM Transactions WHERE transaction_type = 'deposit' AND status = 'pending'",
                     fetchone=True)[0] or 0

        return {
            'total_balance': float(total_balance),
            'total_deposited': float(total_deposited),
            'total_spent': float(total_spent),
            'pending_deposits': float(pending_deposits),
            'total_revenue': float(total_deposited)
        }

    # ==================== ESKI METHODLAR ====================

    def select_all_users(self):
        return self.execute("SELECT * FROM Users", fetchall=True)

    def select_user(self, **kwargs):
        sql = "SELECT * FROM Users WHERE "
        sql, parameters = self.format_args(sql, kwargs)
        return self.execute(sql, parameters=parameters, fetchone=True)

    def count_users(self):
        return self.execute("SELECT COUNT(*) FROM Users;", fetchone=True)[0]

    def delete_users(self):
        self.execute("DELETE FROM Users WHERE TRUE", commit=True)

    def update_user_last_active(self, telegram_id: int):
        self.execute("UPDATE Users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                     parameters=(telegram_id,), commit=True)

    def deactivate_user(self, telegram_id: int):
        self.execute("UPDATE Users SET is_active = FALSE WHERE telegram_id = ?", parameters=(telegram_id,), commit=True)

    def activate_user(self, telegram_id: int):
        self.execute("UPDATE Users SET is_active = TRUE WHERE telegram_id = ?", parameters=(telegram_id,), commit=True)

    def mark_user_as_blocked(self, telegram_id: int):
        self.execute("UPDATE Users SET is_blocked = TRUE, is_active = FALSE WHERE telegram_id = ?",
                     parameters=(telegram_id,), commit=True)

    def get_active_users(self):
        return self.execute("SELECT * FROM Users WHERE is_active = TRUE", fetchall=True)

    def get_inactive_users(self):
        return self.execute("SELECT * FROM Users WHERE is_active = FALSE", fetchall=True)

    def get_blocked_users(self):
        return self.execute("SELECT * FROM Users WHERE is_blocked = TRUE", fetchall=True)

    def count_active_users(self):
        return self.execute("SELECT COUNT(*) FROM Users WHERE is_active = TRUE;", fetchone=True)[0]

    def count_blocked_users(self):
        return self.execute("SELECT COUNT(*) FROM Users WHERE is_blocked = TRUE;", fetchone=True)[0]

    def count_users_last_12_hours(self):
        time_threshold = (datetime.now() - timedelta(hours=12)).isoformat()
        return \
        self.execute("SELECT COUNT(*) FROM Users WHERE created_at >= ?;", parameters=(time_threshold,), fetchone=True)[
            0]

    def count_users_today(self):
        today = datetime.now().date().isoformat()
        return \
        self.execute("SELECT COUNT(*) FROM Users WHERE DATE(created_at) = ?;", parameters=(today,), fetchone=True)[0]

    def count_users_this_week(self):
        start_of_week = (datetime.now() - timedelta(days=datetime.now().weekday())).date().isoformat()
        return self.execute("SELECT COUNT(*) FROM Users WHERE DATE(created_at) >= ?;", parameters=(start_of_week,),
                            fetchone=True)[0]

    def count_users_this_month(self):
        start_of_month = datetime.now().replace(day=1).date().isoformat()
        return self.execute("SELECT COUNT(*) FROM Users WHERE DATE(created_at) >= ?;", parameters=(start_of_month,),
                            fetchone=True)[0]

    def add_admin(self, user_id: int, name: str, is_super_admin: bool = False):
        if not self.check_if_admin(user_id):
            self.execute("INSERT INTO Admins (user_id, name, is_super_admin) VALUES (?, ?, ?)",
                         parameters=(user_id, name, is_super_admin), commit=True)

    def remove_admin(self, user_id: int):
        self.execute("DELETE FROM Admins WHERE user_id = ?", parameters=(user_id,), commit=True)

    def get_all_admins(self):
        sql = "SELECT Admins.user_id, Users.telegram_id, Admins.name, Admins.is_super_admin FROM Admins JOIN Users ON Admins.user_id = Users.id"
        result = self.execute(sql, fetchall=True)
        if not result:
            return []
        admins = []
        for row in result:
            admins.append({"user_id": row[0], "telegram_id": row[1], "name": row[2], "is_super_admin": row[3]})
        return admins

    def check_if_admin(self, user_id: int) -> bool:
        result = self.execute("SELECT 1 FROM Admins WHERE user_id = ?", parameters=(user_id,), fetchone=True)
        return result is not None

    def update_admin_status(self, user_id: int, is_super_admin: bool):
        self.execute("UPDATE Admins SET is_super_admin = ? WHERE user_id = ?", parameters=(is_super_admin, user_id),
                     commit=True)

    # ==================== USERS_DB.PY GA QO'SHILADIGAN METODLAR ====================
    # Bu metodlarni utils/db/users_db.py fayliga qo'shing

    def get_total_balance(self) -> float:
        """Barcha userlarning jami balansini olish"""
        result = self.execute(
            "SELECT COALESCE(SUM(balance), 0) FROM Users",
            fetchone=True
        )
        return float(result[0]) if result else 0.0

    def count_users_with_balance(self) -> int:
        """Balansi 0 dan katta userlar soni"""
        result = self.execute(
            "SELECT COUNT(*) FROM Users WHERE balance > 0",
            fetchone=True
        )
        return result[0] if result else 0

    def reset_all_balances(self, admin_telegram_id: int) -> bool:
        """
        Barcha foydalanuvchilar balansini 0 ga tushirish

        Args:
            admin_telegram_id: Reset qilgan admin ID si

        Returns:
            bool: Muvaffaqiyatli bo'lsa True
        """
        try:
            # 1. Avval balansi bor userlarni olish (log uchun)
            users_with_balance = self.execute(
                "SELECT id, telegram_id, balance FROM Users WHERE balance > 0",
                fetchall=True
            )

            if not users_with_balance:
                print("ℹ️ Balansi bor user yo'q")
                return True

            # 2. Har bir user uchun reset tranzaksiya yozish
            for user in users_with_balance:
                user_id = user[0]
                telegram_id = user[1]
                old_balance = user[2]

                # Tranzaksiya yozish
                self.execute(
                    """INSERT INTO Transactions 
                       (user_id, transaction_type, amount, balance_before, balance_after, 
                        description, status, admin_id, created_at, updated_at)
                       VALUES (?, 'reset', ?, ?, 0, 'Admin tomonidan barcha balanslar reset qilindi', 
                               'approved', ?, datetime('now'), datetime('now'))""",
                    parameters=(user_id, old_balance, old_balance, admin_telegram_id),
                    commit=True
                )

            # 3. BARCHA balanslarni 0 ga tushirish
            self.execute(
                "UPDATE Users SET balance = 0",
                commit=True
            )

            print(f"✅ {len(users_with_balance)} ta user balansi reset qilindi")
            return True

        except Exception as e:
            print(f"❌ Reset balances xato: {e}")
            return False


# ==================== KENGAYTIRILGAN STATISTIKA METODLARI ====================
# Bu metodlarni utils/db/users_db.py fayliga qo'shing



    TASHKENT_TZ = pytz.timezone('Asia/Tashkent')


    def get_tashkent_now(self):
        return datetime.now(TASHKENT_TZ)


    def get_tashkent_today_range(self):
        """Bugungi kun boshlanishi va tugashi (Toshkent vaqti)"""
        now = datetime.now(TASHKENT_TZ)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        # UTC ga o'tkazish (database UTC da saqlaydi)
        today_start_utc = today_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')
        today_end_utc = today_end.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

        return today_start_utc, today_end_utc


    def get_extended_statistics(self) -> dict:
        """
        Kengaytirilgan statistikalar - Toshkent vaqti bo'yicha
        """
        try:
            now = datetime.now(TASHKENT_TZ)
            today_start, today_end = self.get_tashkent_today_range()

            # Hafta boshlanishi (Dushanba)
            week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
            week_start_utc = week_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

            # Oy boshlanishi
            month_start = now.replace(day=1, hour=0, minute=0, second=0)
            month_start_utc = month_start.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')

            stats = {}

            # ==================== FOYDALANUVCHILAR ====================

            # Jami userlar
            result = self.execute("SELECT COUNT(*) FROM Users", fetchone=True)
            stats['total_users'] = result[0] if result else 0

            # Balansi bor userlar
            result = self.execute("SELECT COUNT(*) FROM Users WHERE balance > 0", fetchone=True)
            stats['users_with_balance'] = result[0] if result else 0

            # Balansi yo'q userlar
            stats['users_without_balance'] = stats['total_users'] - stats['users_with_balance']

            # Bugun ro'yxatdan o'tganlar
            result = self.execute(
                "SELECT COUNT(*) FROM Users WHERE created_at >= ? AND created_at <= ?",
                parameters=(today_start, today_end),
                fetchone=True
            )
            stats['new_users_today'] = result[0] if result else 0

            # Bu hafta ro'yxatdan o'tganlar
            result = self.execute(
                "SELECT COUNT(*) FROM Users WHERE created_at >= ?",
                parameters=(week_start_utc,),
                fetchone=True
            )
            stats['new_users_week'] = result[0] if result else 0

            # Bu oy ro'yxatdan o'tganlar
            result = self.execute(
                "SELECT COUNT(*) FROM Users WHERE created_at >= ?",
                parameters=(month_start_utc,),
                fetchone=True
            )
            stats['new_users_month'] = result[0] if result else 0

            # ==================== BALANSLAR ====================

            # Jami balans
            result = self.execute("SELECT COALESCE(SUM(balance), 0) FROM Users", fetchone=True)
            stats['total_balance'] = float(result[0]) if result else 0.0

            # O'rtacha balans (balansi bor userlar orasida)
            result = self.execute(
                "SELECT COALESCE(AVG(balance), 0) FROM Users WHERE balance > 0",
                fetchone=True
            )
            stats['avg_balance'] = float(result[0]) if result else 0.0

            # Eng katta balans
            result = self.execute("SELECT COALESCE(MAX(balance), 0) FROM Users", fetchone=True)
            stats['max_balance'] = float(result[0]) if result else 0.0

            # ==================== BUGUNGI TRANZAKSIYALAR ====================

            # Bugun to'ldirilgan (approved deposits)
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'deposit' 
                   AND status = 'approved'
                   AND created_at >= ? AND created_at <= ?""",
                parameters=(today_start, today_end),
                fetchone=True
            )
            stats['today_deposited'] = float(result[0]) if result else 0.0
            stats['today_deposit_count'] = result[1] if result else 0

            # Bugun sarflangan (withdrawals)
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'withdrawal' 
                   AND status = 'approved'
                   AND created_at >= ? AND created_at <= ?""",
                parameters=(today_start, today_end),
                fetchone=True
            )
            stats['today_spent'] = float(result[0]) if result else 0.0
            stats['today_spent_count'] = result[1] if result else 0

            # Bugun kutilayotgan to'lovlar
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'deposit' 
                   AND status = 'pending'
                   AND created_at >= ? AND created_at <= ?""",
                parameters=(today_start, today_end),
                fetchone=True
            )
            stats['today_pending'] = float(result[0]) if result else 0.0
            stats['today_pending_count'] = result[1] if result else 0

            # ==================== HAFTALIK TRANZAKSIYALAR ====================

            # Bu hafta to'ldirilgan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'deposit' 
                   AND status = 'approved'
                   AND created_at >= ?""",
                parameters=(week_start_utc,),
                fetchone=True
            )
            stats['week_deposited'] = float(result[0]) if result else 0.0
            stats['week_deposit_count'] = result[1] if result else 0

            # Bu hafta sarflangan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'withdrawal' 
                   AND status = 'approved'
                   AND created_at >= ?""",
                parameters=(week_start_utc,),
                fetchone=True
            )
            stats['week_spent'] = float(result[0]) if result else 0.0
            stats['week_spent_count'] = result[1] if result else 0

            # ==================== OYLIK TRANZAKSIYALAR ====================

            # Bu oy to'ldirilgan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'deposit' 
                   AND status = 'approved'
                   AND created_at >= ?""",
                parameters=(month_start_utc,),
                fetchone=True
            )
            stats['month_deposited'] = float(result[0]) if result else 0.0
            stats['month_deposit_count'] = result[1] if result else 0

            # Bu oy sarflangan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'withdrawal' 
                   AND status = 'approved'
                   AND created_at >= ?""",
                parameters=(month_start_utc,),
                fetchone=True
            )
            stats['month_spent'] = float(result[0]) if result else 0.0
            stats['month_spent_count'] = result[1] if result else 0

            # ==================== JAMI (ALL TIME) ====================

            # Jami to'ldirilgan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'deposit' AND status = 'approved'""",
                fetchone=True
            )
            stats['total_deposited'] = float(result[0]) if result else 0.0
            stats['total_deposit_count'] = result[1] if result else 0

            # Jami sarflangan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE transaction_type = 'withdrawal' AND status = 'approved'""",
                fetchone=True
            )
            stats['total_spent'] = float(result[0]) if result else 0.0
            stats['total_spent_count'] = result[1] if result else 0

            # Jami kutilayotgan
            result = self.execute(
                """SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Transactions 
                   WHERE status = 'pending'""",
                fetchone=True
            )
            stats['total_pending'] = float(result[0]) if result else 0.0
            stats['total_pending_count'] = result[1] if result else 0

            # ==================== TASK STATISTIKA ====================

            # Bugungi tasklar
            result = self.execute(
                """SELECT status, COUNT(*) FROM PresentationTasks 
                   WHERE created_at >= ? AND created_at <= ?
                   GROUP BY status""",
                parameters=(today_start, today_end),
                fetchall=True
            )
            stats['today_tasks'] = {row[0]: row[1] for row in result} if result else {}
            stats['today_tasks_total'] = sum(stats['today_tasks'].values())

            # Jami tasklar
            result = self.execute(
                "SELECT status, COUNT(*) FROM PresentationTasks GROUP BY status",
                fetchall=True
            )
            stats['all_tasks'] = {row[0]: row[1] for row in result} if result else {}

            # ==================== TOP USERLAR ====================

            # Eng ko'p balansli 5 user
            result = self.execute(
                """SELECT u.telegram_id, u.username, u.balance 
                   FROM Users u 
                   WHERE u.balance > 0 
                   ORDER BY u.balance DESC LIMIT 5""",
                fetchall=True
            )
            stats['top_balance_users'] = [
                {'telegram_id': r[0], 'username': r[1] or 'N/A', 'balance': r[2]}
                for r in result
            ] if result else []

            # Bugun eng ko'p to'ldirgan userlar
            result = self.execute(
                """SELECT u.telegram_id, u.username, SUM(t.amount) as total
                   FROM Transactions t
                   JOIN Users u ON t.user_id = u.id
                   WHERE t.transaction_type = 'deposit' 
                   AND t.status = 'approved'
                   AND t.created_at >= ? AND t.created_at <= ?
                   GROUP BY u.telegram_id
                   ORDER BY total DESC LIMIT 5""",
                parameters=(today_start, today_end),
                fetchall=True
            )
            stats['top_depositors_today'] = [
                {'telegram_id': r[0], 'username': r[1] or 'N/A', 'amount': r[2]}
                for r in result
            ] if result else []

            # Toshkent vaqti
            stats['current_time'] = now.strftime('%Y-%m-%d %H:%M:%S')
            stats['timezone'] = 'Asia/Tashkent (UTC+5)'

            return stats

        except Exception as e:
            print(f"❌ Extended statistics xato: {e}")
            import traceback
            traceback.print_exc()
            return {}


    def get_total_balance(self) -> float:
        """Barcha userlarning jami balansini olish"""
        result = self.execute(
            "SELECT COALESCE(SUM(balance), 0) FROM Users",
            fetchone=True
        )
        return float(result[0]) if result else 0.0


    def count_users_with_balance(self) -> int:
        """Balansi 0 dan katta userlar soni"""
        result = self.execute(
            "SELECT COUNT(*) FROM Users WHERE balance > 0",
            fetchone=True
        )
        return result[0] if result else 0



    def get_free_presentations(self, telegram_id: int) -> int:
        """
        Foydalanuvchining bepul prezentatsiya qoldig'ini olish

        Returns:
            int: Qolgan bepul prezentatsiyalar soni (default: 2)
        """
        try:
            result = self.execute(
                "SELECT free_presentations FROM Users WHERE telegram_id = ?",
                parameters=(telegram_id,),
                fetchone=True
            )

            if result and result[0] is not None:
                return int(result[0])

            # Agar ustun yo'q yoki NULL bo'lsa, 2 qaytarish
            return 2

        except Exception as e:
            print(f"❌ get_free_presentations xato: {e}")
            return 0

    def use_free_presentation(self, telegram_id: int) -> bool:
        """
        Bepul prezentatsiyani ishlatish (1 ta kamaytirish)

        Returns:
            bool: Muvaffaqiyatli bo'lsa True
        """
        try:
            current_free = self.get_free_presentations(telegram_id)

            if current_free <= 0:
                return False

            self.execute(
                "UPDATE Users SET free_presentations = free_presentations - 1 WHERE telegram_id = ?",
                parameters=(telegram_id,),
                commit=True
            )

            new_free = self.get_free_presentations(telegram_id)
            print(f"✅ Bepul prezentatsiya ishlatildi: User {telegram_id}, Qoldi: {new_free}")

            return True

        except Exception as e:
            print(f"❌ use_free_presentation xato: {e}")
            return False

    def set_free_presentations(self, telegram_id: int, count: int) -> bool:
        """
        Bepul prezentatsiya sonini o'rnatish (Admin uchun)

        Args:
            telegram_id: Foydalanuvchi ID
            count: Yangi son

        Returns:
            bool: Muvaffaqiyatli bo'lsa True
        """
        try:
            self.execute(
                "UPDATE Users SET free_presentations = ? WHERE telegram_id = ?",
                parameters=(count, telegram_id),
                commit=True
            )

            print(f"✅ Bepul prezentatsiya o'rnatildi: User {telegram_id}, Son: {count}")
            return True

        except Exception as e:
            print(f"❌ set_free_presentations xato: {e}")
            return False

    def add_free_presentations(self, telegram_id: int, count: int = 1) -> bool:
        """
        Bepul prezentatsiya qo'shish (Admin/Bonus uchun)

        Args:
            telegram_id: Foydalanuvchi ID
            count: Qo'shiladigan son (default: 1)

        Returns:
            bool: Muvaffaqiyatli bo'lsa True
        """
        try:
            self.execute(
                "UPDATE Users SET free_presentations = free_presentations + ? WHERE telegram_id = ?",
                parameters=(count, telegram_id),
                commit=True
            )

            new_count = self.get_free_presentations(telegram_id)
            print(f"✅ Bepul prezentatsiya qo'shildi: User {telegram_id}, Yangi son: {new_count}")
            return True

        except Exception as e:
            print(f"❌ add_free_presentations xato: {e}")
            return False
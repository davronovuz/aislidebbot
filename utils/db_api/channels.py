# utils/db/channel_db.py
# Kanallar database

from .database import Database
import logging

logger = logging.getLogger(__name__)


class ChannelDatabase(Database):

    def create_table_channels(self):
        """Kanallar jadvalini yaratish"""
        sql_channels = """
        CREATE TABLE IF NOT EXISTS Channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id BIGINT UNIQUE,
            title VARCHAR(255),
            invite_link VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql_channels, commit=True)

    def add_channel(self, channel_id: int, title: str, invite_link: str) -> bool:
        """
        Kanal qo'shish

        Returns:
            bool: True - muvaffaqiyatli, False - allaqachon mavjud yoki xato
        """
        try:
            # Avval mavjudligini tekshirish
            if self.channel_exists(channel_id):
                logger.warning(f"⚠️ Kanal allaqachon mavjud: {channel_id}")
                # Mavjud kanalni yangilash
                self.update_channel(channel_id, title, invite_link)
                return True

            sql = """
            INSERT INTO Channels (channel_id, title, invite_link)
            VALUES (?, ?, ?)
            """
            self.execute(sql, parameters=(channel_id, title, invite_link), commit=True)
            logger.info(f"✅ Kanal qo'shildi: {title} ({channel_id})")
            return True

        except Exception as e:
            logger.error(f"❌ Kanal qo'shishda xato: {e}")
            return False

    def update_channel(self, channel_id: int, title: str = None, invite_link: str = None) -> bool:
        """Kanal ma'lumotlarini yangilash"""
        try:
            updates = []
            params = []

            if title:
                updates.append("title = ?")
                params.append(title)

            if invite_link:
                updates.append("invite_link = ?")
                params.append(invite_link)

            if not updates:
                return False

            params.append(channel_id)
            sql = f"UPDATE Channels SET {', '.join(updates)} WHERE channel_id = ?"
            self.execute(sql, parameters=tuple(params), commit=True)
            logger.info(f"✅ Kanal yangilandi: {channel_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Kanal yangilashda xato: {e}")
            return False

    def remove_channel(self, channel_id: int) -> bool:
        """Kanalni o'chirish"""
        try:
            sql = "DELETE FROM Channels WHERE channel_id = ?"
            self.execute(sql, parameters=(channel_id,), commit=True)
            logger.info(f"✅ Kanal o'chirildi: {channel_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Kanal o'chirishda xato: {e}")
            return False

    def get_all_channels(self) -> list:
        """Barcha faol kanallar"""
        try:
            sql = "SELECT * FROM Channels WHERE is_active = TRUE OR is_active = 1"
            result = self.execute(sql, fetchall=True)
            return result if result else []
        except Exception as e:
            logger.error(f"❌ Kanallarni olishda xato: {e}")
            return []

    def get_channel_by_id(self, channel_id: int):
        """Kanal ID bo'yicha olish"""
        try:
            sql = "SELECT * FROM Channels WHERE channel_id = ?"
            return self.execute(sql, parameters=(channel_id,), fetchone=True)
        except Exception as e:
            logger.error(f"❌ Kanalni olishda xato: {e}")
            return None

    def get_channel_by_invite_link(self, invite_link: str):
        """Invite link bo'yicha kanal olish"""
        try:
            sql = "SELECT * FROM Channels WHERE invite_link = ?"
            return self.execute(sql, parameters=(invite_link,), fetchone=True)
        except Exception as e:
            logger.error(f"❌ Kanalni olishda xato: {e}")
            return None

    def update_channel_invite_link(self, channel_id: int, new_invite_link: str) -> bool:
        """Kanal invite linkini yangilash"""
        return self.update_channel(channel_id, invite_link=new_invite_link)

    def channel_exists(self, channel_id: int) -> bool:
        """Kanal mavjudligini tekshirish"""
        try:
            sql = "SELECT 1 FROM Channels WHERE channel_id = ?"
            result = self.execute(sql, parameters=(channel_id,), fetchone=True)
            return result is not None
        except Exception as e:
            logger.error(f"❌ Tekshirishda xato: {e}")
            return False

    def count_channels(self) -> int:
        """Kanallar sonini olish"""
        try:
            sql = "SELECT COUNT(*) FROM Channels WHERE is_active = TRUE OR is_active = 1"
            result = self.execute(sql, fetchone=True)
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Sanashda xato: {e}")
            return 0

    def deactivate_channel(self, channel_id: int) -> bool:
        """Kanalni o'chirmasdan deaktiv qilish"""
        try:
            sql = "UPDATE Channels SET is_active = FALSE WHERE channel_id = ?"
            self.execute(sql, parameters=(channel_id,), commit=True)
            return True
        except Exception as e:
            logger.error(f"❌ Deaktiv qilishda xato: {e}")
            return False

    def activate_channel(self, channel_id: int) -> bool:
        """Kanalni aktiv qilish"""
        try:
            sql = "UPDATE Channels SET is_active = TRUE WHERE channel_id = ?"
            self.execute(sql, parameters=(channel_id,), commit=True)
            return True
        except Exception as e:
            logger.error(f"❌ Aktiv qilishda xato: {e}")
            return False
import unittest
import discord
from views.shift_view import ShiftView
from views.admin_view import AdminView
from utils.formatters import (
    create_shift_panel_embed,
    create_admin_panel_embed,
    create_admin_report_embed,
    create_active_shifts_embed,
    create_warning_embed,
    create_error_embed,
)

class TestViewsAndEmbeds(unittest.TestCase):
    """View bileşenleri ve embed doğrulama testleri."""

    def test_shift_view_properties(self):
        """ShiftView'in timeout ve custom_id'lerini doğrula."""
        view = ShiftView()
        self.assertIsNone(view.timeout, "ShiftView kalıcı olması için timeout=None olmalıdır.")

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_start_shift", custom_ids)
        self.assertIn("btn_end_shift", custom_ids)

    def test_admin_view_properties(self):
        """AdminView'in timeout ve custom_id'lerini doğrula."""
        view = AdminView()
        self.assertIsNone(view.timeout, "AdminView kalıcı olması için timeout=None olmalıdır.")

        custom_ids = [item.custom_id for item in view.children if isinstance(item, discord.ui.Button)]
        self.assertIn("btn_get_report", custom_ids)
        self.assertIn("btn_active_shifts", custom_ids)

    def test_embed_creation(self):
        """Embed oluşturucuların hatasız çalıştığını doğrula."""
        panel_embed = create_shift_panel_embed()
        self.assertIn("MESAİ", panel_embed.title)

        admin_embed = create_admin_panel_embed()
        self.assertIn("YÖNETİCİ", admin_embed.title)

        warn_embed = create_warning_embed("Test Uyarı", "Açıklama")
        self.assertIn("⚠️", warn_embed.title)

        err_embed = create_error_embed("Test Hata", "Hata detayı")
        self.assertIn("❌", err_embed.title)

        # Rapor embed testi
        mock_report = [
            {"user_id": 111, "user_name": "Ahmet", "shift_count": 5, "total_duration": 36000, "last_active": "2026-08-27T10:00:00+00:00"}
        ]
        rep_embed = create_admin_report_embed(mock_report)
        self.assertIn("RAPORU", rep_embed.title)

if __name__ == "__main__":
    unittest.main()

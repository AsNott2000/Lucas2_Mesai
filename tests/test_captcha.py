import unittest
from datetime import datetime, timezone
import discord
from services.captcha_service import (
    generate_captcha_challenge,
    CaptchaChallenge,
    CaptchaOption,
    CAPTCHA_ITEMS_POOL,
)
from views.captcha_view import CaptchaVerificationView
from utils.formatters import (
    create_captcha_prompt_embed,
    create_captcha_success_embed,
    create_captcha_failed_embed,
)
from database import db
import os
import shutil
from pathlib import Path

class MockUser:
    def __init__(self, user_id=12345, display_name="TestPersonel"):
        self.id = user_id
        self.display_name = display_name
        self.name = display_name.lower()
        self.mention = f"<@{user_id}>"

class MockInteractionResponse:
    def __init__(self):
        self.edited = False
        self.sent_message = False
        self.last_embed = None
        self.last_view = None
        self.is_ephemeral = False

    async def edit_message(self, embed=None, view=None):
        self.edited = True
        self.last_embed = embed
        self.last_view = view

    async def send_message(self, content=None, embed=None, ephemeral=False):
        self.sent_message = True
        self.last_embed = embed
        self.is_ephemeral = ephemeral

class MockInteraction:
    def __init__(self, user, guild_id=9999, guild=None):
        self.user = user
        self.guild_id = guild_id
        self.guild = guild
        self.response = MockInteractionResponse()
        self.message = discord.Object(id=1111)

class TestCaptchaServiceAndViews(unittest.IsolatedAsyncioTestCase):
    """CAPTCHA doğrulama servisi ve View etkileşim testleri."""

    async def asyncSetUp(self):
        self.test_dir = Path("tests/temp_captcha_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.test_db = str(self.test_dir / "test_captcha.db")
        db.db_path = self.test_db
        await db.init_db()

    async def asyncTearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_challenge_generation_structure(self):
        """Dinamik CAPTCHA challenge üretiminin yapısını ve benzersizliğini test et."""
        challenge = generate_captcha_challenge(user_id=101, guild_id=9999, option_count=4, timeout_seconds=60)
        
        self.assertIsInstance(challenge, CaptchaChallenge)
        self.assertEqual(challenge.user_id, 101)
        self.assertEqual(challenge.guild_id, 9999)
        self.assertEqual(challenge.timeout_seconds, 60)
        self.assertEqual(len(challenge.options), 4)

        # Doğru seçenek kontrolü (Tam 1 adet olmalı)
        correct_opts = [opt for opt in challenge.options if opt.is_correct]
        self.assertEqual(len(correct_opts), 1)
        self.assertEqual(correct_opts[0].name, challenge.target_name)
        self.assertEqual(correct_opts[0].emoji, challenge.target_emoji)

        # Yanıltıcı seçenekler kontrolü (3 adet olmalı)
        wrong_opts = [opt for opt in challenge.options if not opt.is_correct]
        self.assertEqual(len(wrong_opts), 3)

        # Şıkların isimlerinin benzersiz olduğunu doğrula
        option_names = [opt.name for opt in challenge.options]
        self.assertEqual(len(set(option_names)), 4)

        # Custom ID'lerin benzersizliğini doğrula
        custom_ids = [opt.custom_id for opt in challenge.options]
        self.assertEqual(len(set(custom_ids)), 4)

    def test_captcha_embeds_creation(self):
        """CAPTCHA embed fonksiyonlarının doğru içerikle oluştuğunu test et."""
        user = MockUser(101, "LucasDev")
        challenge = generate_captcha_challenge(user_id=101, guild_id=9999)

        # 1. Prompt Embed
        prompt_embed = create_captcha_prompt_embed(
            user=user,
            target_name=challenge.target_name,
            target_emoji=challenge.target_emoji,
            minutes_active=45,
            timeout_seconds=60,
            penalty_minutes=45
        )
        self.assertIn("GÜVENLİK", prompt_embed.title)
        self.assertIn(challenge.target_name, prompt_embed.description)
        self.assertIn("60 saniye", prompt_embed.description)
        self.assertIn("45 dakika", prompt_embed.description)

        # 2. Success Embed
        success_embed = create_captcha_success_embed(user=user, challenge=challenge)
        self.assertIn("Başarıyla Doğrulandı", success_embed.title)
        self.assertIn(challenge.target_name, success_embed.description)

        # 3. Failed Embed
        failed_embed = create_captcha_failed_embed(
            user=user,
            target_name=challenge.target_name,
            target_emoji=challenge.target_emoji,
            chosen_name="Yanlış Şık",
            chosen_emoji="❌",
            duration_seconds=1800,
            raw_duration_seconds=4500,
            deducted_seconds=2700,
            penalty_minutes=45
        )
        self.assertIn("Başarısız", failed_embed.title)
        self.assertIn("Yanlış Şık", failed_embed.description)
        self.assertIn("Uygulanan Ceza", failed_embed.description)

    def test_captcha_view_buttons(self):
        """CaptchaVerificationView'in butonlarını challenge seçeneklerine göre oluşturduğunu doğrula."""
        challenge = generate_captcha_challenge(user_id=202, guild_id=8888, option_count=4)
        view = CaptchaVerificationView(challenge=challenge)

        self.assertEqual(len(view.children), 4)
        button_labels = [btn.label for btn in view.children if isinstance(btn, discord.ui.Button)]
        for opt in challenge.options:
            self.assertIn(opt.name, button_labels)

    async def test_captcha_correct_interaction(self):
        """Kullanıcının doğru seçeneğe tıklaması durumunu doğrula."""
        user = MockUser(301, "DogruSecen")
        guild_id = 7777
        t0 = datetime.now(timezone.utc)

        # Mesai başlat
        await db.start_shift(guild_id, user.id, user.display_name, t0)

        challenge = generate_captcha_challenge(user_id=user.id, guild_id=guild_id)
        view = CaptchaVerificationView(challenge=challenge)

        # Doğru butonu bul
        correct_opt = next(opt for opt in challenge.options if opt.is_correct)
        interaction = MockInteraction(user=user, guild_id=guild_id)

        await view._handle_selection(interaction, correct_opt)

        self.assertTrue(challenge.solved)
        self.assertFalse(challenge.failed)
        self.assertTrue(interaction.response.edited)
        self.assertIn("Başarıyla Doğrulandı", interaction.response.last_embed.title)

        # Veritabanında last_verified_at güncellenmiş olmalı
        active = await db.get_active_shift(guild_id, user.id)
        self.assertIsNotNone(active["last_verified_at"])

    async def test_captcha_wrong_interaction(self):
        """Kullanıcının yanlış seçeneğe tıklaması durumunda mesainin sonlandırıldığını ve ceza uygulandığını doğrula."""
        user = MockUser(302, "YanlisSecen")
        guild_id = 7777
        t0 = datetime.now(timezone.utc)

        # Mesai başlat
        await db.start_shift(guild_id, user.id, user.display_name, t0)

        challenge = generate_captcha_challenge(user_id=user.id, guild_id=guild_id)
        view = CaptchaVerificationView(challenge=challenge)

        # Yanlış butonu bul
        wrong_opt = next(opt for opt in challenge.options if not opt.is_correct)
        interaction = MockInteraction(user=user, guild_id=guild_id)

        await view._handle_selection(interaction, wrong_opt)

        self.assertFalse(challenge.solved)
        self.assertTrue(challenge.failed)
        self.assertTrue(interaction.response.edited)
        self.assertIn("Başarısız", interaction.response.last_embed.title)

        # Veritabanında aktif mesai sonlandırılmış olmalı
        active = await db.get_active_shift(guild_id, user.id)
        self.assertIsNone(active)

    async def test_captcha_unauthorized_user(self):
        """Başka bir kullanıcının başkasının CAPTCHA butonuna tıklamasının engellendiğini doğrula."""
        owner_user = MockUser(401, "AsilPersonel")
        other_user = MockUser(402, "Baskasi")
        guild_id = 7777

        challenge = generate_captcha_challenge(user_id=owner_user.id, guild_id=guild_id)
        view = CaptchaVerificationView(challenge=challenge)

        interaction = MockInteraction(user=other_user, guild_id=guild_id)
        any_opt = challenge.options[0]

        await view._handle_selection(interaction, any_opt)

        self.assertFalse(challenge.solved)
        self.assertFalse(challenge.failed)
        self.assertTrue(interaction.response.sent_message)
        self.assertTrue(interaction.response.is_ephemeral)
        self.assertIn("Yetkisiz", interaction.response.last_embed.title)

if __name__ == "__main__":
    unittest.main()

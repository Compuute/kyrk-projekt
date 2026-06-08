"""Re-export FakeTezkarAdapter from fake_payment for guard test discovery."""
from app.adapters.fake_payment import FakeTezkarAdapter

__all__ = ["FakeTezkarAdapter"]

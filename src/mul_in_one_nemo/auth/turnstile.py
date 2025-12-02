"""Cloudflare Turnstile verification service."""

import os
import httpx
from typing import Optional


class TurnstileService:
    """Cloudflare Turnstile 人机验证服务."""
    
    VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    
    def __init__(self):
        self.secret_key = os.environ.get("TURNSTILE_SECRET_KEY", "")
        self.enabled = bool(self.secret_key)
    
    async def verify_token(self, token: str, remote_ip: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        验证 Turnstile token.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not self.enabled:
            # 如果未配置，直接通过
            return True, None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.VERIFY_URL,
                    data={
                        "secret": self.secret_key,
                        "response": token,
                        "remoteip": remote_ip,
                    },
                    timeout=10.0
                )
                
                result = response.json()
                
                if result.get("success"):
                    return True, None
                else:
                    error_codes = result.get("error-codes", [])
                    error_msg = f"Turnstile verification failed: {', '.join(error_codes)}"
                    print(f"[Turnstile] {error_msg}")
                    return False, error_msg
        
        except Exception as e:
            error_msg = f"Turnstile verification error: {str(e)}"
            print(f"[Turnstile] {error_msg}")
            # 验证服务出错时，可以选择通过或拒绝
            # 这里选择拒绝以保证安全
            return False, error_msg


# 全局 Turnstile 服务实例
turnstile_service = TurnstileService()

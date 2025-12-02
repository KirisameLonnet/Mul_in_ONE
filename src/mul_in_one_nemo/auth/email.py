"""Email service for sending verification emails."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailService:
    """邮件发送服务."""
    
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("SMTP_FROM_EMAIL", self.smtp_user)
        self.from_name = os.environ.get("SMTP_FROM_NAME", "Mul-in-ONE")
        self.frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """发送邮件."""
        if not self.enabled:
            print(f"[Email] SMTP not configured. Would send to {to_email}: {subject}")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # 添加纯文本版本（如果提供）
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # 添加 HTML 版本
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"[Email] Sent to {to_email}: {subject}")
        except Exception as e:
            print(f"[Email] Failed to send to {to_email}: {e}")
            raise
    
    def send_verification_email(self, email: str, token: str, username: str):
        """发送邮箱验证邮件."""
        verify_url = f"{self.frontend_url}/verify-email?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #d97757;">欢迎加入 Mul-in-ONE！</h2>
                <p>你好 {username}，</p>
                <p>感谢你注册 Mul-in-ONE 多智能体对话系统。请点击下方按钮验证你的邮箱地址：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verify_url}" 
                       style="background-color: #d97757; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        验证邮箱
                    </a>
                </div>
                <p>或者复制以下链接到浏览器：</p>
                <p style="word-break: break-all; color: #666;">{verify_url}</p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    如果你没有注册 Mul-in-ONE 账户，请忽略此邮件。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        欢迎加入 Mul-in-ONE！
        
        你好 {username}，
        
        感谢你注册 Mul-in-ONE 多智能体对话系统。请访问以下链接验证你的邮箱地址：
        
        {verify_url}
        
        如果你没有注册 Mul-in-ONE 账户，请忽略此邮件。
        """
        
        self.send_email(email, "验证你的 Mul-in-ONE 账户", html_content, text_content)
    
    def send_password_reset_email(self, email: str, token: str, username: str):
        """发送密码重置邮件."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #d97757;">重置密码</h2>
                <p>你好 {username}，</p>
                <p>我们收到了你的密码重置请求。请点击下方按钮重置密码：</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #d97757; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        重置密码
                    </a>
                </div>
                <p>或者复制以下链接到浏览器：</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <p style="color: #d15648; margin-top: 30px;">
                    此链接将在 1 小时后过期。
                </p>
                <p style="color: #999; font-size: 12px;">
                    如果你没有请求重置密码，请忽略此邮件，你的密码不会被更改。
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        重置密码
        
        你好 {username}，
        
        我们收到了你的密码重置请求。请访问以下链接重置密码：
        
        {reset_url}
        
        此链接将在 1 小时后过期。
        
        如果你没有请求重置密码，请忽略此邮件，你的密码不会被更改。
        """
        
        self.send_email(email, "重置你的 Mul-in-ONE 密码", html_content, text_content)


# 全局邮件服务实例
email_service = EmailService()

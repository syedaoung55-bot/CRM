from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from ..config import settings

conf = ConnectionConfig(
    MAIL_USERNAME = settings.mail_username,
    MAIL_PASSWORD = settings.mail_password,
    MAIL_FROM = settings.mail_from,
    MAIL_PORT = settings.mail_port,
    MAIL_SERVER = settings.mail_server,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS=True
)

async def send_lead_assigned_email(assigned_to_email: str, assigned_to_name: str,
                             lead_name: str, assigned_by_name: str):
    message = MessageSchema(
        subject = f"New Lead Assigned: {lead_name}",
        recipients = [assigned_to_email], # type: ignore
        body = f"""
        Hi {assigned_to_name},

        A new lead has been assigned to you.

        Lead Name: {lead_name}
        Assigned By: {assigned_by_name}

        Please log into the system to check futher details.

        Regards,
        Your Supervisor
        """,
        subtype = MessageType.plain
    )
    fm = FastMail(conf)

    await fm.send_message(message)

async def send_welcome_email(email: str, full_name: str):
    message = MessageSchema(
        subject = f"Welcome to the System",
        recipients = [email], # type: ignore
        body = f"""
        Hi {full_name},

        Your account has been created succesfully.

        You can now log into the system.

        Regards,
        System
        """,
        subtype = MessageType.plain
    )
    fm = FastMail(conf)

    await fm.send_message(message)


async def send_invite_email(email: str, full_name: str, temp_password: str, company_name: str, invited_by: str):
    message = MessageSchema(
        subject=f"You've been invited to join {company_name}",
        recipients=[email], # type: ignore
        body=f"""
        Hi {full_name},

        {invited_by} has invited you to join {company_name} on the CRM.

        Your temporary login credentials:
        Email: {email}
        Temporary Password: {temp_password}

        Please log in and change your password as soon as possible.

        Regards,
        {company_name}
        """,
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_password_reset_email(email: str, full_name: str, reset_token: str):
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email], # type: ignore
        body=f"""
        Hi {full_name},

        A password reset was requested for your account.

        Use this token to reset your password: {reset_token}

        If you did not request this, you can safely ignore this email.

        Regards,
        Your CRM
        """,
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def weekly_summary_email(email: str, full_name: str, company_name: str, open_leads: int):
    message = MessageSchema(
        subject=f"Weekly summary for {company_name}",
        recipients=[email], # type: ignore
        body=f"""
        Hi {full_name},

        Here's your weekly summary for {company_name}.

        open_leads: {open_leads}

        Login to your CRM to get the complete breakdown.

        Regards,
        Your CRM
        """,
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_verification_email(email: str, full_name: str, verify_token: str):
    message = MessageSchema(
        subject=f"Verify your email",
        recipients=[email], # type: ignore
        body=f"""
        Hi {full_name},

        Verify your email  by using this token: {verify_token}.

        this link will expire in 24 hours.

        Regards,
        Your CRM
        """,
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)
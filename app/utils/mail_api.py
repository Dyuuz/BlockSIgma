from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models import SendSmtpEmail, SendSmtpEmailTo
from datetime import datetime, timezone, timedelta
from app.utils.mail_date_format import convert_datetime, format_utc_time_label, convert_utc_to_country_time
from app.schema.model_schema import EmailSchema
from dotenv import load_dotenv
from app.database import get_db
from app.models.models import Prediction, Prediction4hr
from sqlalchemy.future import select
import os
import logging
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mail_router = APIRouter(prefix="/smtp", tags=["Email"])


async def send_email_via_brevo(email_to: str, country: str, timeframe: str, name: str | None = None):
    """
    Send email using Brevo API (async wrapper with to_thread)
    """
    brevo_key = os.getenv("BREVO_KEY")
    if not brevo_key:
        logger.error("BREVO_KEY environment variable not set")
        raise ValueError("Brevo API key not configured")

    configuration = Configuration()
    configuration.api_key['api-key'] = brevo_key

    api_client = ApiClient(configuration)
    api_instance = TransactionalEmailsApi(api_client)

    if timeframe == '12hr':
        async for db in get_db():
            result = (select(Prediction).order_by(Prediction.expiry_time.asc()).limit(1))
            result = await db.execute(result)
            valid_until = result.scalars().first().expiry_time.isoformat()
            valid_until = await convert_utc_to_country_time(valid_until, country)
            converted_time = valid_until["converted_time"]
            current_time = await convert_datetime(valid_until["current_time"])
            ft_valid_until = await convert_datetime(converted_time)
            prediction_type = "12-hour"
    
    elif timeframe == '4hr':
        async for db in get_db():
            result = (select(Prediction4hr).order_by(Prediction4hr.expiry_time.asc()).limit(1))
            result = await db.execute(result)
            valid_until = result.scalars().first().expiry_time.isoformat()
            valid_until = await convert_utc_to_country_time(valid_until, country)
            converted_time = valid_until["converted_time"]
            current_time = await convert_datetime(valid_until["current_time"])
            ft_valid_until = await convert_datetime(converted_time)
            prediction_type = "4-hour"
    else:
        ft_valid_until = ''

    greeting = f"Hi {name}," if name else "Hi,"
    mail_time = await format_utc_time_label(ft_valid_until)

    html_content = f"""
    <html>
        <body>
            <p>{greeting}</p>
            <p>A new {prediction_type} prediction for <a href="Binance.com">Binance.com</a> is now live on <a href="https://MyTradeGenius.com">MyTradeGenius.com</a></p>
            <p>📍 Country: {country}</p>
            <p>🕒 Current Time: {current_time}</p>
            <p>📊 Prediction Valid Until: {ft_valid_until}</p>
            <p>🔄 Next Update At: {ft_valid_until}</p>
            <br/>
            <p>You can view the latest prediction and trading signals at:</p>
            <p><a href="https://MyTradeGenius.com">MyTradeGenius.com</a></p>
            <br/>
            <p>Stay ahead with smart trading insights.</p>
            <p>For best results, execute trades within 1 hour of this update.</p>
            <br/>
            <p>Best regards,</p>
            <p>The <a href="https://MyTradeGenius.com">MyTradeGenius.com</a> Team</p>
        </body>
    </html>
    """

    email_data = SendSmtpEmail(
        to=[SendSmtpEmailTo(email=email_to, name=name)],
        subject=f"📈New Binance.com Prediction Available - Valid Until {mail_time}",
        html_content=html_content,
        sender={
            "name": "MyTradeGenius.com",
            "email": os.getenv("SENDER_EMAIL", "noreply@mytradegenius.com")
        }
    )

    def send_email_blocking():
        return api_instance.send_transac_email(email_data)

    try:
        api_response = await asyncio.to_thread(send_email_blocking)
        logger.info(f"Email sent to {email_to}, message ID: {api_response.message_id}")
        return api_response
    
    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {str(e)}")
        raise


@mail_router.post("/send-email")
async def send_email(
    email_data: EmailSchema,
    background_tasks: BackgroundTasks
):
    """
    Send email asynchronously using Brevo SMTP API.
    
    Parameters:
    - email: Valid email address (required)
    - name: Subscriber name (optional)
    """
    try:
        await send_email_via_brevo(
            email_to=email_data.email,
            country=email_data.country,
            timeframe=email_data.timeframe,
            name=email_data.name)
        return {
            "message": "Email is being processed",
            "email": email_data.email
        }
    except Exception as e:
        logger.error(f"Email processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to queue email for sending"
        )

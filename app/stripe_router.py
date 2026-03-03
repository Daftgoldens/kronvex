import hashlib
import hmac
import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import create_api_key
from app.models import Agent

router = APIRouter(tags=["Billing"])

# Price IDs Stripe (mode test)
PRICE_TO_PLAN = {
    "price_1T6f7DGz94jECunBR5zOLfpm": "starter",
    "price_1T6f87Gz94jECunBdUITMLV3": "growth",
    "price_1T6f8RGz94jECunBN5ZBkRA7": "scale",
}


class CheckoutRequest(BaseModel):
    price_id: str
    customer_email: str
    customer_name: str


@router.post("/checkout", summary="Create a Stripe Checkout session")
async def create_checkout(data: CheckoutRequest):
    """
    Crée une session Stripe Checkout.
    Le client est redirigé vers la page de paiement Stripe hébergée.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    if data.price_id not in PRICE_TO_PLAN:
        raise HTTPException(status_code=400, detail="Invalid price_id")

    plan = PRICE_TO_PLAN[data.price_id]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": data.price_id, "quantity": 1}],
            customer_email=data.customer_email,
            metadata={
                "customer_name": data.customer_name,
                "plan": plan,
            },
            success_url="https://kronvex.io?checkout=success&session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://kronvex.io?checkout=cancelled",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook", summary="Stripe webhook — DO NOT CALL MANUALLY")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Reçoit les événements Stripe.
    Quand un paiement réussit → crée la clé API + agent + envoie l'email.
    """
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Vérifier la signature du webhook
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Événement : paiement confirmé
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_completed(db, session)

    # Événement : abonnement annulé
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _handle_subscription_cancelled(db, subscription)

    return {"received": True}


async def _handle_checkout_completed(db: AsyncSession, session: dict):
    """Crée la clé API + agent quand le paiement est confirmé."""
    import smtplib
    from email.mime.text import MIMEText

    metadata = session.get("metadata", {})
    customer_email = session.get("customer_email", "")
    customer_name = metadata.get("customer_name", "Customer")
    plan = metadata.get("plan", "starter")
    stripe_customer_id = session.get("customer", "")

    # Créer la clé API avec le bon plan
    api_key_obj, full_key = await create_api_key(
        db,
        name=f"{customer_name} ({plan})",
        plan=plan,
    )

    # Sauvegarder le customer_id Stripe pour les futures opérations
    api_key_obj.contact_email = customer_email
    api_key_obj.contact_usecase = f"stripe:{stripe_customer_id}"
    await db.commit()

    # Créer un premier agent automatiquement
    from app.plans import get_plan
    p = get_plan(plan)
    agent = Agent(
        name=f"{customer_name}'s agent",
        description=f"Auto-created on {plan} plan",
        api_key_id=api_key_obj.id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Envoyer l'email avec la clé (si SMTP configuré)
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if smtp_user and smtp_pass and customer_email:
        _send_welcome_email(
            smtp_user, smtp_pass,
            to=customer_email,
            name=customer_name,
            plan=plan,
            api_key=full_key,
            agent_id=str(agent.id),
        )


async def _handle_subscription_cancelled(db: AsyncSession, subscription: dict):
    """Désactive la clé API quand l'abonnement est annulé."""
    from sqlalchemy import select, update
    from app.models import ApiKey

    stripe_customer_id = subscription.get("customer", "")
    if not stripe_customer_id:
        return

    # Trouver la clé via le customer_id stocké dans contact_usecase
    await db.execute(
        update(ApiKey)
        .where(ApiKey.contact_usecase == f"stripe:{stripe_customer_id}")
        .values(is_active=False)
    )
    await db.commit()


def _send_welcome_email(smtp_user, smtp_pass, to, name, plan, api_key, agent_id):
    """Envoie l'email de bienvenue avec la clé API."""
    plan_labels = {
        "starter": "Starter — €99/mo",
        "growth":  "Growth — €499/mo",
        "scale":   "Scale — €1,499/mo",
    }
    subject = f"Your Kronvex {plan.capitalize()} API key is ready"
    body = f"""Hi {name},

Welcome to Kronvex! Your {plan_labels.get(plan, plan)} subscription is active.

YOUR API KEY (save it — shown only once):
{api_key}

YOUR FIRST AGENT ID:
{agent_id}

Quick start:
  curl -X POST https://kronvex.up.railway.app/api/v1/agents/{agent_id}/remember \
    -H "X-API-Key: {api_key}" \
    -H "Content-Type: application/json" \
    -d '{{"content": "Hello world", "memory_type": "episodic"}}'

Documentation: https://kronvex.up.railway.app/docs
Support: hello@kronvex.io

— The Kronvex team
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to, msg.as_string())
    except Exception as e:
        # Ne pas planter si l'email échoue — la clé est déjà créée
        print(f"[EMAIL ERROR] {e}")

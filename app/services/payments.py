"""Razorpay integration: local ownership, signature, amount and capture checks."""

import hashlib
import hmac
import secrets
from decimal import Decimal
import requests
from cryptography.fernet import Fernet
from flask import current_app
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Donation, DonationReceipt, now
from app.services.email import queue_email
from app.utils.security import audit


class PaymentError(ValueError):
    pass


class PaymentService:
    @staticmethod
    def enabled():
        c = current_app.config
        return c["DONATIONS_ENABLED"] and bool(
            c["RAZORPAY_KEY_ID"] and c["RAZORPAY_KEY_SECRET"]
        )

    @staticmethod
    def gateway(method, path, **kwargs):
        try:
            response = requests.request(
                method,
                f"https://api.razorpay.com/v1/{path}",
                auth=(
                    current_app.config["RAZORPAY_KEY_ID"],
                    current_app.config["RAZORPAY_KEY_SECRET"],
                ),
                timeout=(5, 20),
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PaymentError(
                "Payment provider is temporarily unavailable. Please try again."
            ) from exc

    def create_order(self, data):
        if not self.enabled():
            raise PaymentError(
                "Online donations are not enabled. Please contact the organization."
            )
        pan = data.get("pan") or ""
        if pan and not current_app.config["FIELD_ENCRYPTION_KEY"]:
            raise PaymentError(
                "PAN collection is unavailable. Leave PAN blank to continue."
            )
        amount = int(Decimal(str(data["amount"])) * 100)
        if amount < 100 or amount > 100000000:
            raise PaymentError("Donation amount is outside the permitted range.")
        donation = Donation(
            name=data["name"],
            email=data["email"].lower().strip(),
            phone=data.get("phone", ""),
            amount=amount,
            address=data.get("address", ""),
            anonymous=data.get("anonymous", False),
            message=data.get("message", ""),
        )
        if pan:
            donation.pan_encrypted = (
                Fernet(current_app.config["FIELD_ENCRYPTION_KEY"].encode())
                .encrypt(pan.encode())
                .decode()
            )
        db.session.add(donation)
        db.session.flush()
        result = self.gateway(
            "POST",
            "orders",
            json={
                "amount": amount,
                "currency": "INR",
                "receipt": f"gyanpath-{donation.token}",
            },
        )
        if (
            result.get("amount") != amount
            or result.get("currency") != "INR"
            or not result.get("id", "").startswith("order_")
        ):
            db.session.rollback()
            raise PaymentError("Payment order could not be verified.")
        donation.order_id = result["id"]
        donation.status = "Pending"
        db.session.commit()
        return donation

    def verify(self, token, order_id, payment_id, signature):
        if not self.enabled():
            raise PaymentError("Online donations are not enabled.")
        donation = db.session.scalar(
            db.select(Donation).where(Donation.token == token).with_for_update()
        )
        if not donation or donation.order_id != order_id:
            raise PaymentError("Payment does not match this donation.")
        if (
            not isinstance(payment_id, str)
            or not payment_id.startswith("pay_")
            or not payment_id.replace("_", "").isalnum()
        ):
            raise PaymentError("Invalid payment identifier.")
        expected = hmac.new(
            current_app.config["RAZORPAY_KEY_SECRET"].encode(),
            f"{donation.order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(
            expected, signature
        ):
            raise PaymentError("Invalid payment signature.")
        if donation.status == "Refunded":
            raise PaymentError("This donation was refunded.")
        if donation.status == "Paid":
            if donation.payment_id != payment_id:
                raise PaymentError("Payment mismatch.")
            return donation
        payment = self.gateway("GET", f"payments/{payment_id}")
        if (
            payment.get("order_id") != donation.order_id
            or payment.get("amount") != donation.amount
            or payment.get("currency") != donation.currency
            or payment.get("status") != "captured"
        ):
            raise PaymentError(
                "Payment is not yet captured or its details do not match. Retry verification shortly."
            )
        donation.payment_id = payment_id
        donation.signature = signature
        donation.payment_method = payment.get("method", "gateway")
        donation.status = "Paid"
        audit("payment captured", "Donation", donation.id)
        db.session.add(
            DonationReceipt(
                donation_id=donation.id,
                receipt_number=f"GP-{now():%Y}-{donation.id:08d}",
            )
        )
        queue_email(
            donation.email,
            "Gyanpath donation receipt",
            "donation",
            donation=donation,
            receipt_url=current_app.config["SITE_URL"]
            + "/donations/"
            + donation.token
            + "/receipt",
        )
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            refreshed = db.session.get(Donation, donation.id)
            if refreshed.status == "Paid" and refreshed.payment_id == payment_id:
                return refreshed
            raise PaymentError("Payment is already associated with another donation.")
        return donation

    def reconcile(self, order_id, payment_id):
        donation = db.session.scalar(
            db.select(Donation).where(Donation.order_id == order_id)
        )
        if not donation:
            return None
        signature = hmac.new(
            current_app.config["RAZORPAY_KEY_SECRET"].encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return self.verify(donation.token, order_id, payment_id, signature)

    def refund(self, donation):
        if donation.status != "Paid":
            raise PaymentError("Only captured donations can be refunded.")
        # Receipt is deterministic so duplicate requests use the same gateway idempotency key.
        result = self.gateway(
            "POST",
            f"payments/{donation.payment_id}/refund",
            headers={"X-Refund-Idempotency": f"gp-refund-{donation.token}"},
            json={"amount": donation.amount, "receipt": f"gp-refund-{donation.id}"},
        )
        if result.get("status") == "processed":
            donation.status = "Refunded"
        db.session.commit()
        return result

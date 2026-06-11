from django.core.mail import send_mail
from django.conf import settings
import requests

def send_email_notification(subject, message, recipient_list=None):
    """Send email notification"""
    if not recipient_list:
        recipient_list = [settings.ADMIN_EMAIL]
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def send_whatsapp_notification(message, phone_number=None):
    """Send WhatsApp notification (via WhatsApp API or Twilio)"""
    # For now, just print. Integrate with WhatsApp Business API later
    print(f"WhatsApp notification to {phone_number}: {message}")
    return True

def notify_new_property(property_obj):
    """Notify admin when a new property is submitted"""
    subject = f"New Property Submitted: {property_obj.title}"
    message = f"""
    A new property has been submitted for approval.
    
    Title: {property_obj.title}
    Type: {property_obj.get_property_type_display()}
    Landlord: {property_obj.landlord.name} ({property_obj.landlord.phone})
    Location: {property_obj.location_neighbourhood}
    
    Approve here: https://enyumba-ebxk.onrender.com/admin/enyumba/property/{property_obj.id}/change/
    """
    send_email_notification(subject, message)

def notify_new_report(report_obj):
    """Notify admin when a property is reported"""
    subject = f"Property Report: {report_obj.property.title}"
    message = f"""
    A property has been reported by a user.
    
    Property: {report_obj.property.title}
    Reason: {report_obj.reason}
    Reporter IP: {report_obj.reporter_ip}
    
    View here: https://enyumba-ebxk.onrender.com/admin/enyumba/report/{report_obj.id}/change/
    """
    send_email_notification(subject, message)

def notify_upgrade_request(property_obj, tier):
    """Notify admin when landlord requests priority upgrade"""
    subject = f"Upgrade Request: {property_obj.title}"
    message = f"""
    A landlord has requested to upgrade their listing.
    
    Property: {property_obj.title}
    Landlord: {property_obj.landlord.name} ({property_obj.landlord.phone})
    Requested Tier: {tier}
    
    Process payment and update listing tier in admin.
    """
    send_email_notification(subject, message)

def notify_payment_confirmed(payment_obj):
    """Notify landlord when payment is confirmed"""
    landlord = payment_obj.landlord
    message = f"""
    Dear {landlord.name},
    
    Your payment of KES {payment_obj.amount} for upgrading "{payment_obj.property.title}" to {payment_obj.tier.upper()} has been confirmed.
    
    Your listing will now appear at the top of search results for 30 days.
    
    Thank you for using eNyumba!
    """
    # For now, send email. Later integrate SMS via Africa's Talking
    send_email_notification(
        subject="Payment Confirmed - eNyumba",
        message=message,
        recipient_list=[landlord.user.email if landlord.user else None]
    )
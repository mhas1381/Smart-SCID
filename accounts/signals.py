from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create a UserProfile when a new User is created.
    """
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            print(f"✅ Profile created for user: {instance.phone_number}")
        except Exception as e:
            print(f"❌ Error creating profile for {instance.phone_number}: {e}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save profile when user is saved.
    """
    if hasattr(instance, "profile"):
        try:
            instance.profile.save()
        except Exception:
            pass
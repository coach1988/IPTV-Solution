from django.apps import AppConfig

class ManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'manager'
    streaming_thread = None
    verbose_name = 'IPTV Manager'    
    
    def ready(self):
        from .models import iptvSession
        try:
            iptvSession.objects.all().delete()
        except Exception as err:
            print(f'ERROR: Couldn\'t flush sessions table, check your DB! Error:\n{err}')

from settings.models import NotificationEmails, Modules
from loguru import logger

def modules_list(module_name):
    """ method for returning filtered email list for a given module"""
    try:
        module = Modules.objects.get(name=module_name)
        modules = NotificationEmails.objects.filter(module=module) 
        m_list = [m.email for m in modules]

        return m_list
    
    except Exception as e:
        logger.info(f'Module: {module_name} doesnt exists')
        
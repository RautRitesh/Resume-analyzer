from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template



def send_email(subject:str,to_email:list,html_template,context):
    msg=EmailMultiAlternatives(subject=subject,to=to_email,from_email="noreply@gmail.com")
    html_template=get_template(html_template)
    html_alternative = html_template.render(context=context)
    msg.attach(html_alternative,"text/html")
    msg.send(fail_silently=False)
    
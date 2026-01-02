from django.shortcuts import redirect

def redirect_authenticated_user(views_func):
    def wrapper(request,*args,**kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        else:
            return views_func(request,*args,**kwargs)
    return wrapper
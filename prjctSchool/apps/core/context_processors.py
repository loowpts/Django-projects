from apps.courses.models import Category


def site_context(request):
    return {
        'categories': Category.objects.all(),
        'current_user': {
            'is_authenticated': request.user.is_authenticated,
            'email': request.user.email if request.user.is_authenticated else None,
            'full_name': request.user.full_name if request.user.is_authenticated else None,
            'role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
        }
    }
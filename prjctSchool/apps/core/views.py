from django.views.generic import TemplateView
from apps.courses.models import Course


class IndexView(TemplateView):
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['courses'] = Course.objects.all()[:6]
        return ctx
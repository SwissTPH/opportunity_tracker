from django.utils import timezone
from weasyprint import HTML
from django.template.loader import get_template
from django.http import HttpResponse


class PDFProcessor:
    @staticmethod
    def process(request, template_path, data, subtitle="", context=None, footnote="", filename="report.pdf"):
        context = context or {}
        printed_date = timezone.now().strftime("%Y-%m-%d %H:%M")
        template = get_template(template_path)
        html = template.render(
            {'data': data, 'printed_date': printed_date, 'subtitle': subtitle, 'context': context, 'footnote': footnote})

        base_url = request.build_absolute_uri('/')

        pdf_file = HTML(
            string=html, base_url=base_url).write_pdf()

        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'

        return response

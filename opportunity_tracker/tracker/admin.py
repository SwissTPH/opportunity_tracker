from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from notification.models import (NotificationChannel, NotificationSubscription,
                                 OpportunitySubscription)
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import (ExportForm, ImportForm,
                                                SelectableFieldsExportForm)

from .models import (Client, Country, Currency, FundingAgency, Institute,
                     Opportunity, Unit, GoReason, NoGoReason)

from .resources import ClientResource, FundingAgencyResource, InstituteResource, UnitResource


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'channel',
                    'preferred_method', 'is_active')
    list_filter = ('user', 'channel', 'is_active')


@admin.register(OpportunitySubscription)
class OpportunitySubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'opportunity', 'is_active')
    list_filter = ('user', 'is_active')


@admin.register(FundingAgency)
class FundingAgencyAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    resource_class = FundingAgencyResource
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(Client)
class ClientAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'name', 'client_type']
    search_fields = ['code', 'name', 'client_type']
    resource_class = ClientResource
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(Institute)
class InstituteAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    resource_class = InstituteResource
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(Country)
class CountryAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(Unit)
class UnitAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']
    resource_class = UnitResource
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(Currency)
class CurrencyAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['code', 'currency', 'symbol']
    search_fields = ['code', 'currency']
    import_form_class = ImportForm
    export_form_class = ExportForm


@admin.register(NotificationChannel)
class NotificationChannelAdmin(ModelAdmin):
    pass


@admin.register(Opportunity)
class OpportunityAdmin(ModelAdmin, ImportExportModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ['ref_no', 'title']
    search_fields = ['ref_no', 'title']


@admin.register(GoReason)
class GoReasonAdmin(ModelAdmin, ImportExportModelAdmin):
    import_from_class = ImportForm
    export_form_class = ExportForm
    list_display = ['reason']
    search_fields = ['reason']


@admin.register(NoGoReason)
class NoGoReasonAdmin(ModelAdmin, ImportExportModelAdmin):
    import_from_class = ImportForm
    export_form_class = ExportForm
    list_display = ['reason']
    search_fields = ['reason']

from django import forms
from django.utils.translation import ugettext as _

from localflavor.br.forms import BRCPFField
from invitations.models import Invitation

from attendee.models import Attendee


class AttendeeForm(forms.ModelForm):
    cpf = BRCPFField()

    class Meta:
        model = Attendee
        fields = (
            'name', 'email', 'educational_institution',
            'cpf', 'phone'
        )


class CustomAttendeeForm(forms.ModelForm):
    cpf = BRCPFField()

    class Meta:
        model = Attendee
        exclude = (
            'code', 'attended_at', 'created_at', 'profile',
            'last_updated_at', 'status', 'moip_status',
            'moip_payment_type', 'moip_code', 'activity'
        )


class AttendeePaymentNotificationForm(forms.Form):
    id_transacao = forms.CharField()
    valor = forms.IntegerField()
    status_pagamento = forms.ChoiceField(choices=Attendee.MOIP_STATUS_CHOICES)
    cod_moip = forms.CharField()
    tipo_pagamento = forms.ChoiceField(
        choices=Attendee.MOIP_PAYMENT_TYPE_CHOICES)
    email_consumidor = forms.CharField()

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(AttendeePaymentNotificationForm, self).__init__(*args, **kwargs)

    def clean_valor(self):
        price = self.cleaned_data.get('valor')
        if self.instance and \
           self.instance.activity.get_price_as_cents > price:
            raise forms.ValidationError(
                'Activity with a wrong price at this payment.'
            )
        return price

    def clean_email_consumidor(self):
        email = self.cleaned_data.get('email_consumidor')
        if self.instance and self.instance.email != email:
            raise forms.ValidationError(
                'Attendee matching query does not exist.'
            )
        return email

    def clean_status_pagamento(self):
        status = self.cleaned_data.get('status_pagamento')
        return int(status)


class AttendeeInviteForm(forms.Form):
    email = forms.EmailField()

    class Meta:
        fields = (
            'email',
        )

    def __init__(self, *args, **kwargs):
        self.activity = kwargs.pop('activity', None)
        super(AttendeeInviteForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        already_attendee = self.activity.attendees.filter(
            user__email=email).exists()
        already_invited = Invitation.objects.filter(email=email).exists()

        if already_attendee:
            raise forms.ValidationError(
                _('Attendee already invited.')
            )
        elif already_invited:
            raise forms.ValidationError(
                _('Attendee already invited.')
            )

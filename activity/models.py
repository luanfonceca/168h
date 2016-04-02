from django.db import models
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.utils.timezone import datetime
from django.template.loader import render_to_string
from django.core.mail import send_mail

from PIL import Image

from django_extensions.db.fields import CreationDateTimeField
from django_extensions.db.models import TitleSlugDescriptionModel

from web168h import settings


class ActivityManager(models.QuerySet):
    def is_public(self):
        return self.filter(is_public=True)

    def get_next(self):
        return self.filter(
            models.Q(scheduled_date__isnull=True) |
            models.Q(scheduled_date__gte=datetime.today())
        ).extra(
            select=dict(date_is_null='scheduled_date IS NULL'),
            order_by=['date_is_null', 'scheduled_date'],
        )


class Activity(TitleSlugDescriptionModel):
    link = models.URLField(_(u'Link'), max_length=300, null=True, blank=True)
    scheduled_date = models.DateField(_(u'Date'), null=True, blank=True)
    hours = models.IntegerField(
        null=True, blank=True,
        help_text=_('Total of hours to be used in the Certificate.'))
    created_at = CreationDateTimeField(_(u'Created At'))
    is_published = models.BooleanField(_(u'Is Published'), default=True)
    is_public = models.BooleanField(_(u'Is Public'), default=True)
    is_organizer = models.BooleanField(_(u'Is Organizer'), default=False)
    is_online = models.BooleanField(default=False)
    photo = models.ImageField(
        _(u'Event photo'),
        upload_to='photos/', null=True, blank=True,
        help_text=_('Images in the resolution: 400x400.'))
    location = models.CharField(
        _(u'Location'), max_length=500, null=True, blank=True)
    capacity = models.IntegerField(
        _(u'Capacity'), default=50, null=True, blank=True)
    price = models.DecimalField(
        _(u'Price'), max_digits=10, decimal_places=2, null=True, blank=True)

    # relations
    created_by = models.ForeignKey(
        verbose_name=_(u'Created by'),
        to='core.Profile',
        null=True, blank=True,
        related_name='activities')
    categories = models.ManyToManyField(
        verbose_name=_(u'Categories'),
        to='category.Category',
        related_name='activities')
    attendees = models.ManyToManyField(
        verbose_name=_(u'Attendees'),
        to='core.Profile',
        through='attendee.Attendee',
        related_name='activities+')

    # managers
    objects = ActivityManager.as_manager()

    class Meta:
        verbose_name = _(u'Activity')
        verbose_name_plural = _(u'Activities')

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('activity:detail', kwargs={'slug': self.slug})

    def get_update_url(self):
        return reverse('activity:update', kwargs={'slug': self.slug})

    def get_delete_url(self):
        return reverse('activity:delete', kwargs={'slug': self.slug})

    def get_attendee_join_url(self):
        return reverse('attendee:join', kwargs={'activity_slug': self.slug})

    def get_attendee_list_url(self):
        return reverse('attendee:list', kwargs={'activity_slug': self.slug})

    @property
    def get_photo_url(self):
        return '{0}/{1}'.format(settings.MEDIA_URL, self.photo)

    def get_attended_ones(self):
        return self.attendee_set.filter(attended_at__isnull=False)

    def check_all(self):
        return self.attendee_set.update(attended_at=datetime.now())

    def send_certificates(self):
        attendees = self.get_attended_ones().values('name', 'code', 'email')
        subject = _(u'Certificate from "{}"!').format(self.title)

        def get_full_certificate_url(slug, code):
            return 'http://{domain}{url}'.format(
                domain=Site.objects.get_current().domain,
                url=reverse('attendee:certificate', kwargs={
                    'activity_slug': slug,
                    'code': code
                })
            )

        for attendee in attendees:
            context = {
                'object': self,
                'name': attendee.get('name'),
                'certificate_url': get_full_certificate_url(
                    self.slug, attendee.get('code'))
            }
            message = render_to_string(
                'mailing/certificate_attendee.txt', context)
            html_message = render_to_string(
                'mailing/certificate_attendee.html', context)
            recipients = [attendee.get('email')]

            send_mail(
                subject=subject, message=message, html_message=html_message,
                from_email=settings.NO_REPLY_EMAIL, recipient_list=recipients
            )


def resize_activity_photo(sender, instance, **kwargs):
    try:
        image = Image.open(instance.photo.path)
    except ValueError:
        return

    if (image.width, image.height) == (400, 400):
        return

    image = image.resize((400, 400), Image.ANTIALIAS)
    image.save(instance.photo.path, quality=90)


post_save.connect(resize_activity_photo, sender=Activity)
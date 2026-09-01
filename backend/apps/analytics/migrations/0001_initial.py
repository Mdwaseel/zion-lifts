"""The analytics tables and the indexes the dashboard reads them through.

Every index here backs a named query in ``selectors.py`` rather than a column
that looked important. They are composite and lead with ``is_demo`` because that
filter is applied to every read (see ``selectors.base_filters``), so leading
with it lets one index serve both the filter and the range scan behind it
instead of the planner intersecting two.

``PageView`` is the table that grows per action; the other two grow per visit
and per browser. That is why the dimension panels — devices, browsers, sources,
geography — are answered from ``Session`` and never touch ``PageView`` at all.
"""

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Visitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.UUIDField(editable=False, unique=True)),
                ('first_seen', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('last_seen', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('session_count', models.PositiveIntegerField(default=0)),
                ('page_view_count', models.PositiveIntegerField(default=0)),
                ('is_demo', models.BooleanField(db_index=True, default=False)),
            ],
            options={
                'indexes': [models.Index(fields=['is_demo', 'first_seen'], name='an_visitor_demo_first')],
            },
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_activity_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('page_view_count', models.PositiveIntegerField(default=0)),
                ('is_first', models.BooleanField(default=False)),
                ('device', models.CharField(choices=[('desktop', 'Desktop'), ('mobile', 'Mobile'), ('tablet', 'Tablet'), ('bot', 'Bot'), ('unknown', 'Unknown')], default='unknown', max_length=12)),
                ('browser', models.CharField(default='Other', max_length=32)),
                ('os', models.CharField(default='Other', max_length=32)),
                ('channel', models.CharField(choices=[('direct', 'Direct'), ('search', 'Google / Search'), ('social', 'Social media'), ('referral', 'Referral'), ('other', 'Other')], default='direct', max_length=12)),
                ('referrer_host', models.CharField(blank=True, max_length=160)),
                ('country', models.CharField(blank=True, max_length=64)),
                ('region', models.CharField(blank=True, max_length=64)),
                ('city', models.CharField(blank=True, max_length=64)),
                ('entry_path', models.CharField(blank=True, max_length=300)),
                ('exit_path', models.CharField(blank=True, max_length=300)),
                ('is_demo', models.BooleanField(db_index=True, default=False)),
                ('visitor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='analytics.visitor')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='PageView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_key', models.UUIDField(editable=False, unique=True)),
                ('path', models.CharField(max_length=300)),
                ('referrer_host', models.CharField(blank=True, max_length=160)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('duration_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('is_demo', models.BooleanField(db_index=True, default=False)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_views', to='analytics.session')),
                ('visitor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_views', to='analytics.visitor')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='session',
            index=models.Index(fields=['is_demo', 'started_at'], name='an_sess_demo_started'),
        ),
        migrations.AddIndex(
            model_name='session',
            index=models.Index(fields=['visitor', '-last_activity_at'], name='an_sess_visitor_recent'),
        ),
        migrations.AddIndex(
            model_name='session',
            index=models.Index(fields=['is_demo', '-last_activity_at'], name='an_sess_demo_recent'),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['is_demo', 'created_at'], name='an_pv_demo_created'),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['is_demo', 'path', 'created_at'], name='an_pv_demo_path_created'),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['visitor', 'created_at'], name='an_pv_visitor_created'),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['session', '-created_at'], name='an_pv_session_recent'),
        ),
    ]

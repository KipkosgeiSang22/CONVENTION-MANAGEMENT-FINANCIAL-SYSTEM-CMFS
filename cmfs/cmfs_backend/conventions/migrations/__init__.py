from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={'db_table': 'regions', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='County',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('county_code', models.CharField(max_length=3, unique=True)),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='counties', to='conventions.region')),
            ],
            options={'db_table': 'counties', 'ordering': ['name'], 'verbose_name_plural': 'counties'},
        ),
        migrations.CreateModel(
            name='Convention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('scope', models.CharField(choices=[('county', 'County'), ('regional', 'Regional'), ('national', 'National')], max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('description', models.TextField(blank=True, default='')),
                ('fee_student', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fee_kessat', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fee_associate', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_registration_open', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open'), ('active', 'Active'), ('ended', 'Ended'), ('financially_closed', 'Financially Closed'), ('archived', 'Archived')], default='draft', max_length=25)),
                ('scope_locked', models.BooleanField(default=False)),
                ('created_by_id', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'conventions', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ConventionUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope_type', models.CharField(choices=[('county', 'County'), ('regional', 'Regional'), ('national', 'National')], max_length=20)),
                ('scope_id', models.IntegerField(blank=True, null=True)),
                ('head_user_id', models.IntegerField(blank=True, null=True)),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='units', to='conventions.convention')),
            ],
            options={'db_table': 'convention_units'},
        ),
    ]